# import json
# import os
# import re
# from typing import Any, Dict, List, Optional, Tuple

# import requests
# from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
# from google.cloud import vision
# from google.oauth2 import service_account
# from pydantic import BaseModel

# try:
#     import phonenumbers
#     from phonenumbers import NumberParseException, PhoneNumberMatcher
# except Exception:  # phonenumbers is optional but recommended
#     phonenumbers = None
#     NumberParseException = Exception
#     PhoneNumberMatcher = None

# from components.tenant_resolver import get_tenant_by_slug, resolve_tenant_slug_from_request

# router = APIRouter()


# class BusinessCardText(BaseModel):
#     text: str


# EMAIL_REGEX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# WEBSITE_REGEX = re.compile(
#     r"(?:https?://)?(?:www\.)?[A-Za-z0-9][A-Za-z0-9.-]+\.(?:com|in|co|net|org|io|biz|info|me|tech|ai)(?:/[^\s]*)?",
#     re.I,
# )
# PHONE_BLOCK_REGEX = re.compile(r"(?:\+?\d[\d\s()./-]{5,}\d)")
# GSTIN_REGEX = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z0-9]Z[A-Z0-9]\b", re.I)

# DESIGNATION_WORDS = [
#     "manager", "director", "owner", "sales", "marketing", "executive",
#     "proprietor", "partner", "founder", "co-founder", "ceo", "cto", "cfo",
#     "md", "designer", "engineer", "consultant", "head", "lead", "developer",
#     "accountant", "chairman", "president", "admin", "hr", "officer", "agent",
#     "specialist", "advisor", "architect", "analyst", "secretary", "maths",
#     "principal", "teacher", "faculty",
# ]

# ADDRESS_WORDS = [
#     "floor", "road", "street", "st.", "nagar", "market", "chowk", "office",
#     "address", "pin", "uttar", "pradesh", "near", "opp", "opposite", "block",
#     "sector", "colony", "shop", "plot", "gali", "lane", "marg", "industrial",
#     "estate", "area", "tower", "building", "complex", "plaza", "suite", "city",
#     "district", "state", "india", "agra", "delhi", "mumbai", "jaipur", "noida",
#     "gurgaon", "bangalore", "hyderabad", "pincode", "pin code", "mandi",
#     "fatehabad", "tajganj", "college", "chauraha", "branch", "centre",
# ]

# COMPANY_HINTS = [
#     "pvt", "pvt.", "ltd", "ltd.", "limited", "llp", "inc", "corp", "corporation",
#     "company", "co.", "enterprises", "enterprise", "solutions", "technology",
#     "technologies", "tech", "traders", "industries", "exports", "imports",
#     "group", "studio", "agency", "associates", "systems", "services", "fashion",
#     "textiles", "digital", "software", "consultancy", "pharma", "labs",
#     "hotel", "residency", "palace", "restaurant", "resort", "inn", "guest house",
#     "coaching", "centre", "center", "classes", "academy", "school", "institute",
#     "college", "tutorial", "education", "clinic", "hospital", "store", "mart",
#     "jewellers", "jewelers", "sweets", "bakery", "foods", "motors", "travels",
# ]

# NAME_PREFIX_REGEX = re.compile(
#     r"^(?:mr|mrs|ms|miss|dr|prof|shri|smt)\.?\s+",
#     re.I,
# )

# INITIAL_NAME_REGEX = re.compile(
#     r"^(?:[A-Z]\.?\s*){1,4}[A-Z][A-Za-z]+(?:\s*\([A-Za-z]+\))?$"
# )

# FULL_NAME_REGEX = re.compile(
#     r"^[A-Z][A-Za-z.]{1,20}(?:\s+[A-Z][A-Za-z.]{1,25}){0,3}(?:\s*\([A-Za-z]+\))?$"
# )

# NAME_BLOCKLIST = [
#     "pvt", "ltd", "limited", "llp", "enterprise", "enterprises", "solutions",
#     "technologies", "technology", "road", "street", "nagar", "market", "office",
#     "floor", "gali", "chowk", "sector", "address", "gstin", "india", "website",
#     "www", "email", "e-mail", "mobile", "phone", "tel", "contact", "hotel",
#     "residency", "palace", "coaching", "centre", "center", "academy", "school",
#     "institute", "college", "branch", "near", "opp", "opposite", "director",
# ]


# def get_vision_client() -> vision.ImageAnnotatorClient:
#     json_key = os.getenv("GOOGLE_VISION_CREDENTIALS_JSON")

#     if json_key:
#         try:
#             credentials_info = json.loads(json_key)
#             credentials = service_account.Credentials.from_service_account_info(credentials_info)
#             return vision.ImageAnnotatorClient(credentials=credentials)
#         except Exception as exc:
#             raise HTTPException(
#                 status_code=500,
#                 detail=f"Invalid GOOGLE_VISION_CREDENTIALS_JSON: {str(exc)}"
#             )

#     credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
#     if credentials_path:
#         try:
#             return vision.ImageAnnotatorClient()
#         except Exception as exc:
#             raise HTTPException(
#                 status_code=500,
#                 detail=f"Failed to initialize Google Vision client: {str(exc)}"
#             )

#     raise HTTPException(
#         status_code=500,
#         detail="Google Vision credentials not configured. Set GOOGLE_VISION_CREDENTIALS_JSON in Railway."
#     )


# def clean_line(line: str) -> str:
#     line = re.sub(r"[|•·]+", " ", line or "")
#     line = re.sub(r"[\t\r]+", " ", line)
#     line = re.sub(r"\s+", " ", line)
#     return line.strip(" -,:;|")


# def unique_list(items: List[str]) -> List[str]:
#     output: List[str] = []
#     seen = set()

#     for item in items:
#         value = clean_line(item)
#         if not value:
#             continue
#         key = value.lower()
#         if key not in seen:
#             seen.add(key)
#             output.append(value)

#     return output


# def digits_only(value: str) -> str:
#     return re.sub(r"\D", "", value or "")


# PHONE_COUNTRIES = [
#     {"country": "IN", "dialCode": "+91"},
#     {"country": "US", "dialCode": "+1"},
#     {"country": "CA", "dialCode": "+1"},
#     {"country": "PK", "dialCode": "+92"},
#     {"country": "IL", "dialCode": "+972"},
#     {"country": "CN", "dialCode": "+86"},
#     {"country": "KW", "dialCode": "+965"},
#     {"country": "GB", "dialCode": "+44"},
#     {"country": "AE", "dialCode": "+971"},
#     {"country": "SG", "dialCode": "+65"},
#     {"country": "AU", "dialCode": "+61"},
#     {"country": "SA", "dialCode": "+966"},
#     {"country": "QA", "dialCode": "+974"},
#     {"country": "OM", "dialCode": "+968"},
#     {"country": "BH", "dialCode": "+973"},
#     {"country": "DE", "dialCode": "+49"},
#     {"country": "FR", "dialCode": "+33"},
#     {"country": "IT", "dialCode": "+39"},
#     {"country": "ES", "dialCode": "+34"},
#     {"country": "NL", "dialCode": "+31"},
#     {"country": "TR", "dialCode": "+90"},
#     {"country": "TH", "dialCode": "+66"},
#     {"country": "MY", "dialCode": "+60"},
#     {"country": "JP", "dialCode": "+81"},
#     {"country": "KR", "dialCode": "+82"},
#     {"country": "HK", "dialCode": "+852"},
# ]

# SORTED_PHONE_COUNTRIES = sorted(
#     PHONE_COUNTRIES,
#     key=lambda item: len(item["dialCode"].replace("+", "")),
#     reverse=True,
# )

# PHONE_LABEL_REGEX = re.compile(
#     r"(?:phone|mobile|mob|cell|tel|telephone|office|whatsapp|wa|contact)\s*[:：-]?\s*(.+)",
#     re.I,
# )


# def get_fallback_country(digits: str) -> Dict[str, str]:
#     for item in SORTED_PHONE_COUNTRIES:
#         code_digits = item["dialCode"].replace("+", "")
#         if digits.startswith(code_digits):
#             return item
#     return {}


# def reject_false_phone(raw: str) -> bool:
#     value = raw or ""
#     lowered = value.lower()

#     # Reject prices, dimensions and decimals like 92.50, $3.85, 20x32.
#     if "$" in value or "₹" in value or "€" in value or "£" in value:
#         return True
#     if re.search(r"\b\d+\s*[x×]\s*\d+\b", lowered):
#         return True
#     if "+" not in value and re.search(r"\d+\.\d+", value):
#         return True
#     return False


# def phone_detail_from_phonenumbers(value: str, default_region: str = "IN") -> Dict[str, str]:
#     if phonenumbers is None:
#         return {}

#     raw = clean_line(value or "")
#     if reject_false_phone(raw):
#         return {}

#     try:
#         parsed = phonenumbers.parse(raw, None if "+" in raw else default_region)
#         if not phonenumbers.is_possible_number(parsed) or not phonenumbers.is_valid_number(parsed):
#             return {}
#         country = phonenumbers.region_code_for_number(parsed) or default_region
#         dial_code = f"+{parsed.country_code}"
#         national_number = str(parsed.national_number)
#         if not (6 <= len(national_number) <= 15):
#             return {}
#         return {
#             "number": national_number,
#             "country": country,
#             "dialCode": dial_code,
#             "raw": raw,
#         }
#     except Exception:
#         return {}


# def normalize_phone_detail(value: str, fallback_country: str = "") -> Dict[str, str]:
#     raw = clean_line(value or "")
#     raw = re.sub(r"(?:ext\.?|extension|x)\s*\d+$", "", raw, flags=re.I)

#     if reject_false_phone(raw):
#         return {"number": "", "country": "", "dialCode": "", "raw": raw}

#     default_region = fallback_country or "IN"
#     parsed = phone_detail_from_phonenumbers(raw, default_region=default_region)
#     if parsed:
#         return parsed

#     digits = digits_only(raw)
#     if not digits or len(digits) < 6:
#         return {"number": "", "country": "", "dialCode": "", "raw": raw}

#     country = ""
#     dial_code = ""

#     # International number: remove exact country code only, never guess from random digits.
#     if "+" in raw:
#         match = get_fallback_country(digits)
#         if not match:
#             return {"number": "", "country": "", "dialCode": "", "raw": raw}
#         country = match["country"]
#         dial_code = match["dialCode"]
#         digits = digits[len(dial_code.replace("+", "")):]

#     elif fallback_country:
#         country = fallback_country
#         match = next((item for item in PHONE_COUNTRIES if item["country"] == fallback_country), None)
#         dial_code = match["dialCode"] if match else ""

#     elif len(digits) == 10 and digits[0] in "6789":
#         country = "IN"
#         dial_code = "+91"

#     else:
#         # Do not treat random amounts/measurements as phone numbers.
#         return {"number": "", "country": "", "dialCode": "", "raw": raw}

#     if not (6 <= len(digits) <= 15):
#         return {"number": "", "country": "", "dialCode": "", "raw": raw}

#     return {
#         "number": digits,
#         "country": country,
#         "dialCode": dial_code,
#         "raw": raw,
#     }


# def add_phone(phones: List[Dict[str, str]], seen: set, phone: Dict[str, str]) -> None:
#     number = phone.get("number", "")
#     if not number:
#         return
#     key = (phone.get("country", ""), number)
#     if key not in seen:
#         seen.add(key)
#         phones.append(phone)


# def extract_phone_details(text: str) -> List[Dict[str, str]]:
#     phones: List[Dict[str, str]] = []
#     seen = set()
#     full_text = text or ""

#     # Best path: Google OCR text + libphonenumber exact validation for all countries.
#     if PhoneNumberMatcher is not None:
#         for match in PhoneNumberMatcher(full_text, "IN"):
#             raw = match.raw_string
#             phone = phone_detail_from_phonenumbers(raw, default_region="IN")
#             add_phone(phones, seen, phone)

#     # Fallback path: only parse regex blocks if they contain +country-code or phone label context.
#     last_country = ""
#     for line in split_lines(full_text):
#         label_match = PHONE_LABEL_REGEX.search(line)
#         line_has_phone_label = bool(label_match)
#         candidates = PHONE_BLOCK_REGEX.findall(line)

#         for candidate in candidates:
#             has_plus = "+" in candidate
#             if not has_plus and not line_has_phone_label:
#                 continue

#             phone = normalize_phone_detail(candidate, fallback_country=last_country if not has_plus else "")
#             if phone.get("country"):
#                 last_country = phone["country"]
#             add_phone(phones, seen, phone)

#     return phones

# def normalize_phone(value: str) -> str:
#     return normalize_phone_detail(value).get("number", "")


# def extract_phone_details(text: str) -> List[Dict[str, str]]:
#     phones: List[Dict[str, str]] = []
#     seen = set()
#     last_country = ""

#     for candidate in PHONE_BLOCK_REGEX.findall(text or ""):
#         phone = normalize_phone_detail(candidate, fallback_country=last_country)
#         number = phone.get("number", "")
#         if not number:
#             continue

#         if phone.get("country"):
#             last_country = phone["country"]

#         key = (phone.get("country", ""), number)
#         if key not in seen:
#             seen.add(key)
#             phones.append(phone)

#     return phones


# def extract_emails(text: str) -> List[str]:
#     return unique_list(EMAIL_REGEX.findall(text or ""))


# def extract_websites(text: str) -> List[str]:
#     websites = []
#     for item in WEBSITE_REGEX.findall(text or ""):
#         cleaned = clean_line(item).rstrip(".,;")
#         if cleaned and "@" not in cleaned:
#             websites.append(cleaned.lower())
#     return unique_list(websites)


# def extract_phones(text: str) -> List[str]:
#     return [phone["number"] for phone in extract_phone_details(text)]


# def extract_gstin(text: str) -> str:
#     match = GSTIN_REGEX.search((text or "").upper())
#     return match.group(0) if match else ""


# def looks_like_email(line: str) -> bool:
#     return bool(EMAIL_REGEX.search(line or ""))


# def looks_like_phone(line: str) -> bool:
#     return bool(normalize_phone(line))


# def looks_like_website(line: str) -> bool:
#     return bool(WEBSITE_REGEX.search(line or ""))


# def has_company_hint(line: str) -> bool:
#     lowered = (line or "").lower()
#     return any(word in lowered for word in COMPANY_HINTS)


# def is_probable_address(line: str) -> bool:
#     lowered = (line or "").lower()

#     if looks_like_email(line) or looks_like_website(line):
#         return False

#     if any(word in lowered for word in ADDRESS_WORDS):
#         return True

#     if re.search(r"\b\d{6}\b", line or ""):
#         return True

#     if "," in line and any(ch.isdigit() for ch in line):
#         return True

#     return False


# def is_probable_designation(line: str) -> bool:
#     lowered = (line or "").lower()
#     if has_company_hint(line):
#         return False
#     return any(word in lowered for word in DESIGNATION_WORDS)


# def is_all_caps_like(line: str) -> bool:
#     letters = re.sub(r"[^A-Za-z]", "", line or "")
#     return bool(letters) and letters.isupper()


# def is_noise_line(line: str) -> bool:
#     lowered = (line or "").lower().strip()

#     if not lowered:
#         return True

#     noise_words = [
#         "email", "e-mail", "mail", "phone", "tel", "mobile", "contact",
#         "website", "web", "www", "fax",
#     ]

#     if lowered in noise_words:
#         return True

#     if lowered.startswith("email") or lowered.startswith("e-mail"):
#         return True

#     return False


# # def looks_like_person_name(line: str) -> bool:
# #     line = clean_line(line)

# #     if not line:
# #         return False

# #     lowered = line.lower()

# #     if is_noise_line(line):
# #         return False

# #     if re.search(r"\d", line):
# #         return False

# #     if looks_like_email(line) or looks_like_website(line) or looks_like_phone(line):
# #         return False

# #     if is_probable_address(line):
# #         return False

# #     if has_company_hint(line):
# #         return False

# #     if any(word in lowered for word in NAME_BLOCKLIST):
# #         return False

# #     line_without_prefix = NAME_PREFIX_REGEX.sub("", line).strip()
# #     words = [w for w in re.split(r"\s+", line_without_prefix) if w]

# #     if not 1 <= len(words) <= 4:
# #         return False

# #     if not any(re.search(r"[A-Za-z]", word) for word in words):
# #         return False

# #     if INITIAL_NAME_REGEX.match(line_without_prefix):
# #         return True

# #     if FULL_NAME_REGEX.match(line_without_prefix):
# #         return True

# #     return False 

# def looks_like_person_name(line: str) -> bool:
#     line = clean_line(line)

#     if not line:
#         return False

#     lowered = line.lower()

#     if is_noise_line(line):
#         return False

#     if looks_like_email(line) or looks_like_website(line) or looks_like_phone(line):
#         return False

#     if is_probable_address(line):
#         return False

#     if has_company_hint(line):
#         return False

#     if any(word in lowered for word in NAME_BLOCKLIST):
#         return False

#     # ✅ IMPORTANT:
#     # If line has subject/designation in brackets like:
#     # V.K. Agarwal(maths)
#     # do NOT treat it as person name.
#     # This prevents wrong auto-fill.
#     if re.search(r"\([^)]*\)", line):
#         return False

#     words = [w for w in re.split(r"\s+", line.strip()) if w]

#     # Reject single-word brands like Daawat
#     if not 2 <= len(words) <= 4:
#         return False

#     if re.search(r"\d", line):
#         return False

#     if INITIAL_NAME_REGEX.match(line):
#         return True

#     if FULL_NAME_REGEX.match(line):
#         return True

#     return False

# def score_company_candidate(line: str, index: int) -> int:
#     line = clean_line(line)
#     lowered = line.lower()

#     if not line:
#         return -100

#     if is_noise_line(line):
#         return -100

#     if looks_like_email(line) or looks_like_phone(line) or looks_like_website(line):
#         return -100

#     if extract_gstin(line):
#         return -100

#     score = 0

#     if has_company_hint(line):
#         score += 15

#     if len(line.split()) >= 2:
#         score += 4

#     if len(line) >= 10:
#         score += 3

#     if is_all_caps_like(line):
#         score += 2

#     if index <= 5:
#         score += 5

#     if is_probable_address(line):
#         score -= 8

#     if looks_like_person_name(line):
#         score -= 10

#     if is_probable_designation(line):
#         score -= 8

#     address_markers = ["near", "opp", "opposite", "road", "branch", "block", "mandi"]
#     if any(word in lowered for word in address_markers):
#         score -= 8

#     return score


# def split_lines(raw_text: str) -> List[str]:
#     raw_lines = raw_text.splitlines() if raw_text else []
#     cleaned = [clean_line(line) for line in raw_lines]
#     return [line for line in cleaned if line]


# def merge_likely_company_lines(lines: List[str]) -> List[str]:
#     merged = list(lines)

#     for i in range(len(lines) - 1):
#         first = clean_line(lines[i])
#         second = clean_line(lines[i + 1])

#         if not first or not second:
#             continue

#         combined = f"{first} {second}"

#         if has_company_hint(combined) and not is_probable_address(combined):
#             if combined not in merged:
#                 merged.append(combined)

#     return merged


# def pick_company(lines: List[str]) -> str:
#     candidates: List[Tuple[int, str]] = []

#     company_lines = merge_likely_company_lines(lines[:12])

#     for idx, line in enumerate(company_lines):
#         score = score_company_candidate(line, idx)
#         candidates.append((score, line))

#     candidates.sort(key=lambda x: x[0], reverse=True)

#     if candidates and candidates[0][0] > 0:
#         return candidates[0][1]

#     return ""


# def pick_designation(lines: List[str], company: str) -> str:
#     for line in lines:
#         if line == company:
#             continue

#         # Do not use name-like bracket lines as designation
#         if re.search(r"\([^)]*\)", line):
#             continue

#         if is_probable_designation(line):
#             return line

#     return ""


# # def pick_name(lines: List[str], company: str, designation: str) -> str:
# #     top_lines = lines[:10]

# #     for line in top_lines:
# #         if line in {company, designation}:
# #             continue

# #         if looks_like_person_name(line):
# #             return line

# #     return "" 
# def pick_name(lines: List[str], company: str, designation: str) -> str:
#     for line in lines[:10]:
#         if line in {company, designation}:
#             continue

#         if looks_like_person_name(line):
#             # remove subject/designation inside brackets
#             clean_name = re.sub(r"\([^)]*\)", "", line).strip()
#             clean_name = clean_line(clean_name)
#             return clean_name

#     return ""


# def group_address(lines: List[str], company: str, designation: str, person_name: str) -> str:
#     address_lines: List[str] = []

#     for line in lines:
#         if line in {company, designation, person_name}:
#             continue

#         if looks_like_email(line) or looks_like_phone(line) or looks_like_website(line):
#             continue

#         if extract_gstin(line):
#             continue

#         if has_company_hint(line) and not is_probable_address(line):
#             continue

#         if is_probable_address(line):
#             address_lines.append(line)

#     return ", ".join(unique_list(address_lines))


# def build_notes(
#     lines: List[str],
#     company: str,
#     designation: str,
#     person_name: str,
#     address: str,
#     phones: List[str],
#     emails: List[str],
#     websites: List[str],
#     gstin: str,
# ) -> str:
#     address_parts = [part.strip() for part in address.split(",") if part.strip()]
#     skip_values = set(
#         [company, designation, person_name, gstin, *address_parts, *phones, *emails, *websites]
#     )

#     notes: List[str] = []

#     for line in lines:
#         if line in skip_values:
#             continue

#         if is_noise_line(line):
#             continue

#         if looks_like_email(line) or looks_like_phone(line) or looks_like_website(line):
#             continue

#         if extract_gstin(line):
#             continue

#         if is_probable_address(line):
#             continue

#         if line == company or line == person_name or line == designation:
#             continue

#         notes.append(line)

#     return " | ".join(unique_list(notes))


# def parse_text(raw_text: str) -> Tuple[Dict[str, Any], List[str]]:
#     lines = split_lines(raw_text)
#     full_text = "\n".join(lines)

#     emails = extract_emails(full_text)
#     websites = extract_websites(full_text)
#     phone_details = extract_phone_details(full_text)
#     phones = [phone["number"] for phone in phone_details]
#     gstin = extract_gstin(full_text)

#     company = pick_company(lines)
#     designation = pick_designation(lines, company)
#     person_name = pick_name(lines, company, designation)
#     address = group_address(lines, company, designation, person_name)

#     notes = build_notes(
#         lines=lines,
#         company=company,
#         designation=designation,
#         person_name=person_name,
#         address=address,
#         phones=phones,
#         emails=emails,
#         websites=websites,
#         gstin=gstin,
#     )

#     parsed: Dict[str, Any] = {
#         "type": "",
#         "level": "",
#         "category": "",
#         "product": "",
#         "item_data": [],
#         "customerCompany": company,
#         "personName": person_name,
#         "designation": designation,
#         "mobile": phone_details[0]["number"] if len(phone_details) > 0 else "",
#         "mobile2": phone_details[1]["number"] if len(phone_details) > 1 else "",
#         "mobileCountry": phone_details[0].get("country") if len(phone_details) > 0 else "IN",
#         "mobile2Country": phone_details[1].get("country") if len(phone_details) > 1 else (phone_details[0].get("country") if len(phone_details) > 0 else "IN"),
#         "mobileDialCode": phone_details[0].get("dialCode") if len(phone_details) > 0 else "+91",
#         "mobile2DialCode": phone_details[1].get("dialCode") if len(phone_details) > 1 else (phone_details[0].get("dialCode") if len(phone_details) > 0 else "+91"),
#         "email": emails[0] if len(emails) > 0 else "",
#         "email2": emails[1] if len(emails) > 1 else "",
#         "address": address,
#         "notes": notes,
#         "qtyScope": "",
#         "gstin": gstin,
#         "website": websites[0] if websites else "",
#         "rawText": raw_text or "",
#     }

#     return parsed, lines


# def build_selections(parsed: Dict[str, Any], lines: List[str]) -> List[Dict[str, str]]:
#     labels = {
#         "customerCompany": "Company",
#         "personName": "Name",
#         "designation": "Designation",
#         "mobile": "Mobile",
#         "mobile2": "Mobile 2",
#         "email": "Email",
#         "email2": "Email 2",
#         "address": "Address",
#         "notes": "Notes",
#         "gstin": "GSTIN",
#         "website": "Website",
#     }

#     selections: List[Dict[str, str]] = []

#     for key, label in labels.items():
#         value = clean_line(str(parsed.get(key, "") or ""))
#         if value:
#             selections.append({"label": label, "value": value})

#     for index, line in enumerate(lines):
#         if line:
#             selections.append({"label": f"Line {index + 1}", "value": line})

#     final: List[Dict[str, str]] = []
#     seen = set()

#     for item in selections:
#         value = clean_line(item["value"])
#         key = value.lower()
#         if value and key not in seen:
#             seen.add(key)
#             final.append({"label": item["label"], "value": value})

#     return final


# def google_document_text_detection(image_bytes: bytes) -> str:
#     client = get_vision_client()

#     image = vision.Image(content=image_bytes)
#     image_context = vision.ImageContext(language_hints=["en"])

#     response = client.document_text_detection(
#         image=image,
#         image_context=image_context,
#     )

#     if response.error.message:
#         raise HTTPException(status_code=500, detail=response.error.message)

#     if response.full_text_annotation and response.full_text_annotation.text:
#         return response.full_text_annotation.text

#     text_annotations = getattr(response, "text_annotations", None) or []
#     if text_annotations:
#         return text_annotations[0].description or ""

#     return ""


# async def upload_image_to_tenant_php(
#     tenant: Any,
#     image: UploadFile,
#     source: Optional[str] = None,
#     timestamp: Optional[str] = None,
#     name: Optional[str] = None,
#     phone: Optional[str] = None,
#     email: Optional[str] = None,
#     company: Optional[str] = None,
# ) -> Dict[str, Any]:
#     php_upload_url = getattr(tenant, "php_upload_url", None) or os.getenv("PHP_UPLOAD_URL")

#     if not php_upload_url:
#         raise HTTPException(
#             status_code=500,
#             detail=f"php_upload_url is missing for tenant {tenant.slug}"
#         )

#     file_content = await image.read()
#     if not file_content:
#         raise HTTPException(status_code=400, detail="Empty image file")

#     files = {
#         "image": (
#             image.filename or "business-card.jpg",
#             file_content,
#             image.content_type or "image/jpeg",
#         )
#     }

#     data = {
#         "source": source or "business_card_scan",
#         "timestamp": timestamp or "",
#         "name": name or "",
#         "phone": phone or "",
#         "email": email or "",
#         "company": company or "",
#         "tenant": tenant.slug,
#     }

#     try:
#         response = requests.post(
#             php_upload_url,
#             files=files,
#             data=data,
#             timeout=30,
#         )
#     except requests.RequestException as exc:
#         raise HTTPException(status_code=500, detail=f"PHP upload failed: {str(exc)}")

#     if response.status_code != 200:
#         raise HTTPException(
#             status_code=500,
#             detail=f"PHP returned {response.status_code}: {response.text}"
#         )

#     try:
#         result = response.json()
#     except Exception:
#         raise HTTPException(status_code=500, detail=f"Invalid PHP response: {response.text}")

#     if not result.get("status"):
#         raise HTTPException(
#             status_code=500,
#             detail=result.get("message", "Image upload failed on PHP")
#         )

#     return {
#         "status": True,
#         "filename": result.get("filename") or result.get("image_name") or "",
#         "image_url": result.get("url") or result.get("image_url") or "",
#         "raw": result,
#         "file_content": file_content,
#     }


# @router.post("/business-card/scan")
# async def scan_business_card(
#     file: UploadFile = File(...),
# ):
#     if not file.content_type or not file.content_type.startswith("image/"):
#         raise HTTPException(status_code=400, detail="Only image files are allowed")

#     image_bytes = await file.read()
#     if not image_bytes:
#         raise HTTPException(status_code=400, detail="Empty image file")

#     if len(image_bytes) > 10 * 1024 * 1024:
#         raise HTTPException(status_code=400, detail="Image size must be less than 10MB")

#     raw_text = google_document_text_detection(image_bytes)
#     parsed, lines = parse_text(raw_text)

#     return {
#         "status": True,
#         "message": "Business card scanned successfully",
#         "data": parsed,
#         "selections": build_selections(parsed, lines),
#         "rawText": raw_text,
#     }


# @router.post("/business-card/parse")
# def parse_business_card(data: BusinessCardText):
#     parsed, lines = parse_text(data.text or "")

#     return {
#         "status": True,
#         "message": "Business card parsed successfully",
#         "data": parsed,
#         "selections": build_selections(parsed, lines),
#         "rawText": data.text or "",
#     }


# @router.post("/business-card/scan-live")
# async def scan_business_card_live(
#     request: Request,
#     image: UploadFile = File(...),
#     source: Optional[str] = Form(default="business_card_scan"),
#     timestamp: Optional[str] = Form(default=None),
#     name: Optional[str] = Form(default=None),
#     phone: Optional[str] = Form(default=None),
#     email: Optional[str] = Form(default=None),
#     company: Optional[str] = Form(default=None),
#     tenant_slug: str = Depends(resolve_tenant_slug_from_request),
# ):
#     if not image.content_type or not image.content_type.startswith("image/"):
#         raise HTTPException(status_code=400, detail="Only image files are allowed")

#     tenant = get_tenant_by_slug(tenant_slug)

#     uploaded = await upload_image_to_tenant_php(
#         tenant=tenant,
#         image=image,
#         source=source,
#         timestamp=timestamp,
#         name=name,
#         phone=phone,
#         email=email,
#         company=company,
#     )

#     image_bytes = uploaded["file_content"]

#     if len(image_bytes) > 10 * 1024 * 1024:
#         raise HTTPException(status_code=400, detail="Image size must be less than 10MB")

#     raw_text = google_document_text_detection(image_bytes)
#     parsed, lines = parse_text(raw_text)

#     parsed["image_name"] = uploaded["filename"]
#     parsed["image_url"] = uploaded["image_url"]

#     return {
#         "status": True,
#         "tenant": tenant.slug,
#         "message": "Business card scanned successfully",
#         "data": parsed,
#         "selections": build_selections(parsed, lines),
#         "rawText": raw_text,
#         "image_name": uploaded["filename"],
#         "image_url": uploaded["image_url"],
#     } 

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import requests
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from google.cloud import vision
from google.oauth2 import service_account
from pydantic import BaseModel

try:
    import phonenumbers
    from phonenumbers import NumberParseException, PhoneNumberMatcher
except Exception:  # phonenumbers is optional but recommended
    phonenumbers = None
    NumberParseException = Exception
    PhoneNumberMatcher = None

from components.tenant_resolver import get_tenant_by_slug, resolve_tenant_slug_from_request

router = APIRouter()


class BusinessCardText(BaseModel):
    text: str


EMAIL_REGEX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
WEBSITE_REGEX = re.compile(
    r"(?:https?://)?(?:www\.)?[A-Za-z0-9][A-Za-z0-9.-]+\.(?:com|in|co|net|org|io|biz|info|me|tech|ai)(?:/[^\s]*)?",
    re.I,
)
PHONE_BLOCK_REGEX = re.compile(r"(?:\+?\d[\d\s()./-]{5,}\d)")
GSTIN_REGEX = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z0-9]Z[A-Z0-9]\b", re.I)

DESIGNATION_WORDS = [
    "manager", "director", "owner", "sales", "marketing", "executive",
    "proprietor", "partner", "founder", "co-founder", "ceo", "cto", "cfo",
    "md", "designer", "engineer", "consultant", "head", "lead", "developer",
    "accountant", "chairman", "president", "admin", "hr", "officer", "agent",
    "specialist", "advisor", "architect", "analyst", "secretary", "maths",
    "principal", "teacher", "faculty",
]

ADDRESS_WORDS = [
    "floor", "road", "street", "st.", "nagar", "market", "chowk", "office",
    "address", "pin", "uttar", "pradesh", "near", "opp", "opposite", "block",
    "sector", "colony", "shop", "plot", "gali", "lane", "marg", "industrial",
    "estate", "area", "tower", "building", "complex", "plaza", "suite", "city",
    "district", "state", "india", "agra", "delhi", "mumbai", "jaipur", "noida",
    "gurgaon", "bangalore", "hyderabad", "pincode", "pin code", "mandi",
    "fatehabad", "tajganj", "college", "chauraha", "branch", "centre",
]

COMPANY_HINTS = [
    "pvt", "pvt.", "ltd", "ltd.", "limited", "llp", "inc", "corp", "corporation",
    "company", "co.", "enterprises", "enterprise", "solutions", "technology",
    "technologies", "tech", "traders", "industries", "exports", "imports",
    "group", "studio", "agency", "associates", "systems", "services", "fashion",
    "textiles", "digital", "software", "consultancy", "pharma", "labs",
    "hotel", "residency", "palace", "restaurant", "resort", "inn", "guest house",
    "coaching", "centre", "center", "classes", "academy", "school", "institute",
    "college", "tutorial", "education", "clinic", "hospital", "store", "mart",
    "jewellers", "jewelers", "sweets", "bakery", "foods", "motors", "travels",
]

NAME_PREFIX_REGEX = re.compile(
    r"^(?:mr|mrs|ms|miss|dr|prof|shri|smt)\.?\s+",
    re.I,
)

INITIAL_NAME_REGEX = re.compile(
    r"^(?:[A-Z]\.?\s*){1,4}[A-Z][A-Za-z]+(?:\s*\([A-Za-z]+\))?$"
)

FULL_NAME_REGEX = re.compile(
    r"^[A-Z][A-Za-z.]{1,20}(?:\s+[A-Z][A-Za-z.]{1,25}){0,3}(?:\s*\([A-Za-z]+\))?$"
)

NAME_BLOCKLIST = [
    "pvt", "ltd", "limited", "llp", "enterprise", "enterprises", "solutions",
    "technologies", "technology", "road", "street", "nagar", "market", "office",
    "floor", "gali", "chowk", "sector", "address", "gstin", "india", "website",
    "www", "email", "e-mail", "mobile", "phone", "tel", "contact", "hotel",
    "residency", "palace", "coaching", "centre", "center", "academy", "school",
    "institute", "college", "branch", "near", "opp", "opposite", "director",
]


def get_vision_client() -> vision.ImageAnnotatorClient:
    json_key = os.getenv("GOOGLE_VISION_CREDENTIALS_JSON")

    if json_key:
        try:
            credentials_info = json.loads(json_key)
            credentials = service_account.Credentials.from_service_account_info(credentials_info)
            return vision.ImageAnnotatorClient(credentials=credentials)
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Invalid GOOGLE_VISION_CREDENTIALS_JSON: {str(exc)}"
            )

    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if credentials_path:
        try:
            return vision.ImageAnnotatorClient()
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize Google Vision client: {str(exc)}"
            )

    raise HTTPException(
        status_code=500,
        detail="Google Vision credentials not configured. Set GOOGLE_VISION_CREDENTIALS_JSON in Railway."
    )


def clean_line(line: str) -> str:
    line = re.sub(r"[|•·]+", " ", line or "")
    line = re.sub(r"[\t\r]+", " ", line)
    line = re.sub(r"\s+", " ", line)
    return line.strip(" -,:;|")


def unique_list(items: List[str]) -> List[str]:
    output: List[str] = []
    seen = set()

    for item in items:
        value = clean_line(item)
        if not value:
            continue
        key = value.lower()
        if key not in seen:
            seen.add(key)
            output.append(value)

    return output


def digits_only(value: str) -> str:
    return re.sub(r"\D", "", value or "")


PHONE_COUNTRIES = [
    {"country": "IN", "dialCode": "+91"},
    {"country": "US", "dialCode": "+1"},
    {"country": "CA", "dialCode": "+1"},
    {"country": "PK", "dialCode": "+92"},
    {"country": "IL", "dialCode": "+972"},
    {"country": "CN", "dialCode": "+86"},
    {"country": "KW", "dialCode": "+965"},
    {"country": "GB", "dialCode": "+44"},
    {"country": "AE", "dialCode": "+971"},
    {"country": "SG", "dialCode": "+65"},
    {"country": "AU", "dialCode": "+61"},
    {"country": "SA", "dialCode": "+966"},
    {"country": "QA", "dialCode": "+974"},
    {"country": "OM", "dialCode": "+968"},
    {"country": "BH", "dialCode": "+973"},
    {"country": "DE", "dialCode": "+49"},
    {"country": "FR", "dialCode": "+33"},
    {"country": "IT", "dialCode": "+39"},
    {"country": "ES", "dialCode": "+34"},
    {"country": "NL", "dialCode": "+31"},
    {"country": "TR", "dialCode": "+90"},
    {"country": "TH", "dialCode": "+66"},
    {"country": "MY", "dialCode": "+60"},
    {"country": "JP", "dialCode": "+81"},
    {"country": "KR", "dialCode": "+82"},
    {"country": "HK", "dialCode": "+852"},
]

SORTED_PHONE_COUNTRIES = sorted(
    PHONE_COUNTRIES,
    key=lambda item: len(item["dialCode"].replace("+", "")),
    reverse=True,
)

PHONE_LABEL_REGEX = re.compile(
    r"(?:phone|mobile|mob|cell|tel|telephone|office|whatsapp|wa|contact|direct|dir|handphone|hp)\s*[:：-]?\s*(.+)",
    re.I,
)
PHONE_CONTEXT_REGEX = re.compile(
    r"\b(?:mobile|mob|cell|tel|telephone|phone|direct|dir|office|whatsapp|wa|contact|handphone|hp)\b",
    re.I,
)
ADDRESS_PHONE_CONTEXT_REGEX = re.compile(
    r"\b(?:address|add|office|suite|tower|building|floor|road|street|st\.?|ave|avenue|blvd|district|city|state|china|india|usa|kuwait|israel|new york|california)\b",
    re.I,
)
MOBILE_PRIORITY_REGEX = re.compile(
    r"\b(?:mobile|mob|cell|whatsapp|wa|handphone|hp|direct|dir)\b",
    re.I,
)
OFFICE_PRIORITY_REGEX = re.compile(r"\boffice\b", re.I)


def get_fallback_country(digits: str) -> Dict[str, str]:
    for item in SORTED_PHONE_COUNTRIES:
        code_digits = item["dialCode"].replace("+", "")
        if digits.startswith(code_digits):
            return item
    return {}


def reject_false_phone(raw: str) -> bool:
    value = raw or ""
    lowered = value.lower()
    if "$" in value or "₹" in value or "€" in value or "£" in value:
        return True
    if re.search(r"\b\d+\s*[x×]\s*\d+\b", lowered):
        return True
    if "+" not in value and re.search(r"\d+\.\d+", value):
        return True
    return False


def phone_detail_from_phonenumbers(value: str, default_region: str = "IN") -> Dict[str, str]:
    if phonenumbers is None:
        return {}

    raw = clean_line(value or "")
    if reject_false_phone(raw):
        return {}

    try:
        parsed = phonenumbers.parse(raw, None if "+" in raw else default_region)
        if not phonenumbers.is_possible_number(parsed) or not phonenumbers.is_valid_number(parsed):
            return {}
        country = phonenumbers.region_code_for_number(parsed) or default_region
        dial_code = f"+{parsed.country_code}"
        national_number = str(parsed.national_number)
        if not (6 <= len(national_number) <= 15):
            return {}
        return {
            "number": national_number,
            "country": country,
            "dialCode": dial_code,
            "raw": raw,
        }
    except Exception:
        return {}


def normalize_phone_detail(value: str, fallback_country: str = "") -> Dict[str, str]:
    raw = clean_line(value or "")
    raw = re.sub(r"(?:ext\.?|extension|x)\s*\d+$", "", raw, flags=re.I)

    if reject_false_phone(raw):
        return {"number": "", "country": "", "dialCode": "", "raw": raw}

    default_region = fallback_country or "IN"
    parsed = phone_detail_from_phonenumbers(raw, default_region=default_region)
    if parsed:
        return parsed

    digits = digits_only(raw)
    if not digits or len(digits) < 6:
        return {"number": "", "country": "", "dialCode": "", "raw": raw}

    country = ""
    dial_code = ""

    if "+" in raw:
        match = get_fallback_country(digits)
        if not match:
            return {"number": "", "country": "", "dialCode": "", "raw": raw}
        country = match["country"]
        dial_code = match["dialCode"]
        digits = digits[len(dial_code.replace("+", "")):]
    elif fallback_country:
        country = fallback_country
        match = next((item for item in PHONE_COUNTRIES if item["country"] == fallback_country), None)
        dial_code = match["dialCode"] if match else ""
    elif len(digits) == 10 and digits[0] in "6789":
        country = "IN"
        dial_code = "+91"
    else:
        return {"number": "", "country": "", "dialCode": "", "raw": raw}

    if not (6 <= len(digits) <= 15):
        return {"number": "", "country": "", "dialCode": "", "raw": raw}

    return {
        "number": digits,
        "country": country,
        "dialCode": dial_code,
        "raw": raw,
    }


def add_phone(phones: List[Dict[str, Any]], seen: set, phone: Dict[str, Any]) -> None:
    number = phone.get("number", "")
    if not number:
        return
    key = (phone.get("country", ""), number)
    if key not in seen:
        seen.add(key)
        phones.append(phone)


def phone_priority(line: str, candidate: str, phone: Dict[str, str], order: int) -> int:
    score = 0
    lowered = (line or "").lower()
    raw = (candidate or "").strip()
    digits = phone.get("number", "")
    raw_digits = digits_only(raw)

    if MOBILE_PRIORITY_REGEX.search(lowered):
        score += 120
    if OFFICE_PRIORITY_REGEX.search(lowered):
        score += 70
    if PHONE_CONTEXT_REGEX.search(lowered):
        score += 45
    if raw.strip().startswith("+"):
        score += 35
    if len(digits) >= 8:
        score += 10
    if ADDRESS_PHONE_CONTEXT_REGEX.search(lowered):
        score -= 12
    if re.search(r"\b(?:fax|gst|tax|zip|pin|pincode)\b", lowered):
        score -= 100
    score -= order
    return score


def extract_phone_details(text: str) -> List[Dict[str, str]]:
    phones: List[Dict[str, Any]] = []
    seen = set()
    full_text = text or ""
    lines = split_lines(full_text)
    last_country = ""
    order = 0

    for line in lines:
        line_has_phone_label = bool(PHONE_CONTEXT_REGEX.search(line))
        candidates = PHONE_BLOCK_REGEX.findall(line)

        if PhoneNumberMatcher is not None:
            try:
                matches = list(PhoneNumberMatcher(line, last_country or "IN"))
            except Exception:
                matches = []
            for match in matches:
                raw = match.raw_string
                phone = phone_detail_from_phonenumbers(raw, default_region=last_country or "IN")
                if not phone.get("number"):
                    continue
                if phone.get("country"):
                    last_country = phone["country"]
                phone["priority"] = phone_priority(line, raw, phone, order)
                phone["sourceLine"] = line
                add_phone(phones, seen, phone)
                order += 1

        for candidate in candidates:
            has_plus = "+" in candidate
            if not has_plus and not line_has_phone_label:
                continue
            phone = normalize_phone_detail(candidate, fallback_country=last_country if not has_plus else "")
            if not phone.get("number"):
                continue
            if phone.get("country"):
                last_country = phone["country"]
            phone["priority"] = phone_priority(line, candidate, phone, order)
            phone["sourceLine"] = line
            add_phone(phones, seen, phone)
            order += 1

    phones.sort(key=lambda item: item.get("priority", 0), reverse=True)
    return [{k: v for k, v in item.items() if k in {"number", "country", "dialCode", "raw"}} for item in phones[:2]]


def normalize_phone(value: str) -> str:
    return normalize_phone_detail(value).get("number", "")

def extract_emails(text: str) -> List[str]:
    return unique_list(EMAIL_REGEX.findall(text or ""))


def extract_websites(text: str) -> List[str]:
    websites = []
    for item in WEBSITE_REGEX.findall(text or ""):
        cleaned = clean_line(item).rstrip(".,;")
        if cleaned and "@" not in cleaned:
            websites.append(cleaned.lower())
    return unique_list(websites)


def extract_phones(text: str) -> List[str]:
    return [phone["number"] for phone in extract_phone_details(text)]


def extract_gstin(text: str) -> str:
    match = GSTIN_REGEX.search((text or "").upper())
    return match.group(0) if match else ""


def looks_like_email(line: str) -> bool:
    return bool(EMAIL_REGEX.search(line or ""))


def looks_like_phone(line: str) -> bool:
    return bool(normalize_phone(line))


def looks_like_website(line: str) -> bool:
    return bool(WEBSITE_REGEX.search(line or ""))


def has_company_hint(line: str) -> bool:
    lowered = (line or "").lower()
    return any(word in lowered for word in COMPANY_HINTS)


def is_probable_address(line: str) -> bool:
    lowered = (line or "").lower()

    if looks_like_email(line) or looks_like_website(line):
        return False

    if any(word in lowered for word in ADDRESS_WORDS):
        return True

    if re.search(r"\b\d{6}\b", line or ""):
        return True

    if "," in line and any(ch.isdigit() for ch in line):
        return True

    return False


def is_probable_designation(line: str) -> bool:
    lowered = (line or "").lower()
    if has_company_hint(line):
        return False
    return any(word in lowered for word in DESIGNATION_WORDS)


def is_all_caps_like(line: str) -> bool:
    letters = re.sub(r"[^A-Za-z]", "", line or "")
    return bool(letters) and letters.isupper()


def is_noise_line(line: str) -> bool:
    lowered = (line or "").lower().strip()

    if not lowered:
        return True

    noise_words = [
        "email", "e-mail", "mail", "phone", "tel", "mobile", "contact",
        "website", "web", "www", "fax",
    ]

    if lowered in noise_words:
        return True

    if lowered.startswith("email") or lowered.startswith("e-mail"):
        return True

    return False


# def looks_like_person_name(line: str) -> bool:
#     line = clean_line(line)

#     if not line:
#         return False

#     lowered = line.lower()

#     if is_noise_line(line):
#         return False

#     if re.search(r"\d", line):
#         return False

#     if looks_like_email(line) or looks_like_website(line) or looks_like_phone(line):
#         return False

#     if is_probable_address(line):
#         return False

#     if has_company_hint(line):
#         return False

#     if any(word in lowered for word in NAME_BLOCKLIST):
#         return False

#     line_without_prefix = NAME_PREFIX_REGEX.sub("", line).strip()
#     words = [w for w in re.split(r"\s+", line_without_prefix) if w]

#     if not 1 <= len(words) <= 4:
#         return False

#     if not any(re.search(r"[A-Za-z]", word) for word in words):
#         return False

#     if INITIAL_NAME_REGEX.match(line_without_prefix):
#         return True

#     if FULL_NAME_REGEX.match(line_without_prefix):
#         return True

#     return False 

def looks_like_person_name(line: str) -> bool:
    line = clean_line(line)

    if not line:
        return False

    lowered = line.lower()

    if is_noise_line(line):
        return False

    if looks_like_email(line) or looks_like_website(line) or looks_like_phone(line):
        return False

    if is_probable_address(line):
        return False

    if has_company_hint(line):
        return False

    if any(word in lowered for word in NAME_BLOCKLIST):
        return False

    # ✅ IMPORTANT:
    # If line has subject/designation in brackets like:
    # V.K. Agarwal(maths)
    # do NOT treat it as person name.
    # This prevents wrong auto-fill.
    if re.search(r"\([^)]*\)", line):
        return False

    words = [w for w in re.split(r"\s+", line.strip()) if w]

    # Reject single-word brands like Daawat
    if not 2 <= len(words) <= 4:
        return False

    if re.search(r"\d", line):
        return False

    if INITIAL_NAME_REGEX.match(line):
        return True

    if FULL_NAME_REGEX.match(line):
        return True

    return False

def score_company_candidate(line: str, index: int) -> int:
    line = clean_line(line)
    lowered = line.lower()

    if not line:
        return -100

    if is_noise_line(line):
        return -100

    if looks_like_email(line) or looks_like_phone(line) or looks_like_website(line):
        return -100

    if extract_gstin(line):
        return -100

    score = 0

    if has_company_hint(line):
        score += 15

    if len(line.split()) >= 2:
        score += 4

    if len(line) >= 10:
        score += 3

    if is_all_caps_like(line):
        score += 2

    if index <= 5:
        score += 5

    if is_probable_address(line):
        score -= 8

    if looks_like_person_name(line):
        score -= 10

    if is_probable_designation(line):
        score -= 8

    address_markers = ["near", "opp", "opposite", "road", "branch", "block", "mandi"]
    if any(word in lowered for word in address_markers):
        score -= 8

    return score


def split_lines(raw_text: str) -> List[str]:
    raw_lines = raw_text.splitlines() if raw_text else []
    cleaned = [clean_line(line) for line in raw_lines]
    return [line for line in cleaned if line]


def merge_likely_company_lines(lines: List[str]) -> List[str]:
    merged = list(lines)

    for i in range(len(lines) - 1):
        first = clean_line(lines[i])
        second = clean_line(lines[i + 1])

        if not first or not second:
            continue

        combined = f"{first} {second}"

        if has_company_hint(combined) and not is_probable_address(combined):
            if combined not in merged:
                merged.append(combined)

    return merged


def pick_company(lines: List[str]) -> str:
    candidates: List[Tuple[int, str]] = []

    company_lines = merge_likely_company_lines(lines[:12])

    for idx, line in enumerate(company_lines):
        score = score_company_candidate(line, idx)
        candidates.append((score, line))

    candidates.sort(key=lambda x: x[0], reverse=True)

    if candidates and candidates[0][0] > 0:
        return candidates[0][1]

    return ""


def pick_designation(lines: List[str], company: str) -> str:
    for line in lines:
        if line == company:
            continue

        # Do not use name-like bracket lines as designation
        if re.search(r"\([^)]*\)", line):
            continue

        if is_probable_designation(line):
            return line

    return ""


# def pick_name(lines: List[str], company: str, designation: str) -> str:
#     top_lines = lines[:10]

#     for line in top_lines:
#         if line in {company, designation}:
#             continue

#         if looks_like_person_name(line):
#             return line

#     return "" 
def pick_name(lines: List[str], company: str, designation: str) -> str:
    for line in lines[:10]:
        if line in {company, designation}:
            continue

        if looks_like_person_name(line):
            # remove subject/designation inside brackets
            clean_name = re.sub(r"\([^)]*\)", "", line).strip()
            clean_name = clean_line(clean_name)
            return clean_name

    return ""


def group_address(lines: List[str], company: str, designation: str, person_name: str) -> str:
    address_lines: List[str] = []

    for line in lines:
        if line in {company, designation, person_name}:
            continue

        if looks_like_email(line) or looks_like_phone(line) or looks_like_website(line):
            continue

        if extract_gstin(line):
            continue

        if has_company_hint(line) and not is_probable_address(line):
            continue

        if is_probable_address(line):
            address_lines.append(line)

    return ", ".join(unique_list(address_lines))


def build_notes(
    lines: List[str],
    company: str,
    designation: str,
    person_name: str,
    address: str,
    phones: List[str],
    emails: List[str],
    websites: List[str],
    gstin: str,
) -> str:
    address_parts = [part.strip() for part in address.split(",") if part.strip()]
    skip_values = set(
        [company, designation, person_name, gstin, *address_parts, *phones, *emails, *websites]
    )

    notes: List[str] = []

    for line in lines:
        if line in skip_values:
            continue

        if is_noise_line(line):
            continue

        if looks_like_email(line) or looks_like_phone(line) or looks_like_website(line):
            continue

        if extract_gstin(line):
            continue

        if is_probable_address(line):
            continue

        if line == company or line == person_name or line == designation:
            continue

        notes.append(line)

    return " | ".join(unique_list(notes))


def parse_text(raw_text: str) -> Tuple[Dict[str, Any], List[str]]:
    lines = split_lines(raw_text)
    full_text = "\n".join(lines)

    emails = extract_emails(full_text)
    websites = extract_websites(full_text)
    phone_details = extract_phone_details(full_text)
    phones = [phone["number"] for phone in phone_details]
    gstin = extract_gstin(full_text)

    company = pick_company(lines)
    designation = pick_designation(lines, company)
    person_name = pick_name(lines, company, designation)
    address = group_address(lines, company, designation, person_name)

    notes = build_notes(
        lines=lines,
        company=company,
        designation=designation,
        person_name=person_name,
        address=address,
        phones=phones,
        emails=emails,
        websites=websites,
        gstin=gstin,
    )

    parsed: Dict[str, Any] = {
        "type": "",
        "level": "",
        "category": "",
        "product": "",
        "item_data": [],
        "customerCompany": company,
        "personName": person_name,
        "designation": designation,
        "mobile": phone_details[0]["number"] if len(phone_details) > 0 else "",
        "mobile2": phone_details[1]["number"] if len(phone_details) > 1 else "",
        "mobileCountry": phone_details[0].get("country") if len(phone_details) > 0 else "IN",
        "mobile2Country": phone_details[1].get("country") if len(phone_details) > 1 else (phone_details[0].get("country") if len(phone_details) > 0 else "IN"),
        "mobileDialCode": phone_details[0].get("dialCode") if len(phone_details) > 0 else "+91",
        "mobile2DialCode": phone_details[1].get("dialCode") if len(phone_details) > 1 else (phone_details[0].get("dialCode") if len(phone_details) > 0 else "+91"),
        "email": emails[0] if len(emails) > 0 else "",
        "email2": emails[1] if len(emails) > 1 else "",
        "address": address,
        "notes": notes,
        "qtyScope": "",
        "gstin": gstin,
        "website": websites[0] if websites else "",
        "rawText": raw_text or "",
    }

    return parsed, lines


def build_selections(parsed: Dict[str, Any], lines: List[str]) -> List[Dict[str, str]]:
    labels = {
        "customerCompany": "Company",
        "personName": "Name",
        "designation": "Designation",
        "mobile": "Mobile",
        "mobile2": "Mobile 2",
        "email": "Email",
        "email2": "Email 2",
        "address": "Address",
        "notes": "Notes",
        "gstin": "GSTIN",
        "website": "Website",
    }

    selections: List[Dict[str, str]] = []

    for key, label in labels.items():
        value = clean_line(str(parsed.get(key, "") or ""))
        if value:
            selections.append({"label": label, "value": value})

    for index, line in enumerate(lines):
        if line:
            selections.append({"label": f"Line {index + 1}", "value": line})

    final: List[Dict[str, str]] = []
    seen = set()

    for item in selections:
        value = clean_line(item["value"])
        key = value.lower()
        if value and key not in seen:
            seen.add(key)
            final.append({"label": item["label"], "value": value})

    return final


def google_document_text_detection(image_bytes: bytes) -> str:
    client = get_vision_client()

    image = vision.Image(content=image_bytes)
    image_context = vision.ImageContext(language_hints=["en"])

    response = client.document_text_detection(
        image=image,
        image_context=image_context,
    )

    if response.error.message:
        raise HTTPException(status_code=500, detail=response.error.message)

    if response.full_text_annotation and response.full_text_annotation.text:
        return response.full_text_annotation.text

    text_annotations = getattr(response, "text_annotations", None) or []
    if text_annotations:
        return text_annotations[0].description or ""

    return ""


async def upload_image_to_tenant_php(
    tenant: Any,
    image: UploadFile,
    source: Optional[str] = None,
    timestamp: Optional[str] = None,
    name: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    company: Optional[str] = None,
) -> Dict[str, Any]:
    php_upload_url = getattr(tenant, "php_upload_url", None) or os.getenv("PHP_UPLOAD_URL")

    if not php_upload_url:
        raise HTTPException(
            status_code=500,
            detail=f"php_upload_url is missing for tenant {tenant.slug}"
        )

    file_content = await image.read()
    if not file_content:
        raise HTTPException(status_code=400, detail="Empty image file")

    files = {
        "image": (
            image.filename or "business-card.jpg",
            file_content,
            image.content_type or "image/jpeg",
        )
    }

    data = {
        "source": source or "business_card_scan",
        "timestamp": timestamp or "",
        "name": name or "",
        "phone": phone or "",
        "email": email or "",
        "company": company or "",
        "tenant": tenant.slug,
    }

    try:
        response = requests.post(
            php_upload_url,
            files=files,
            data=data,
            timeout=30,
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=500, detail=f"PHP upload failed: {str(exc)}")

    if response.status_code != 200:
        raise HTTPException(
            status_code=500,
            detail=f"PHP returned {response.status_code}: {response.text}"
        )

    try:
        result = response.json()
    except Exception:
        raise HTTPException(status_code=500, detail=f"Invalid PHP response: {response.text}")

    if not result.get("status"):
        raise HTTPException(
            status_code=500,
            detail=result.get("message", "Image upload failed on PHP")
        )

    return {
        "status": True,
        "filename": result.get("filename") or result.get("image_name") or "",
        "image_url": result.get("url") or result.get("image_url") or "",
        "raw": result,
        "file_content": file_content,
    }


@router.post("/business-card/scan")
async def scan_business_card(
    file: UploadFile = File(...),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty image file")

    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image size must be less than 10MB")

    raw_text = google_document_text_detection(image_bytes)
    parsed, lines = parse_text(raw_text)

    return {
        "status": True,
        "message": "Business card scanned successfully",
        "data": parsed,
        "selections": build_selections(parsed, lines),
        "rawText": raw_text,
    }


@router.post("/business-card/parse")
def parse_business_card(data: BusinessCardText):
    parsed, lines = parse_text(data.text or "")

    return {
        "status": True,
        "message": "Business card parsed successfully",
        "data": parsed,
        "selections": build_selections(parsed, lines),
        "rawText": data.text or "",
    }


@router.post("/business-card/scan-live")
async def scan_business_card_live(
    request: Request,
    image: UploadFile = File(...),
    source: Optional[str] = Form(default="business_card_scan"),
    timestamp: Optional[str] = Form(default=None),
    name: Optional[str] = Form(default=None),
    phone: Optional[str] = Form(default=None),
    email: Optional[str] = Form(default=None),
    company: Optional[str] = Form(default=None),
    tenant_slug: str = Depends(resolve_tenant_slug_from_request),
):
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    tenant = get_tenant_by_slug(tenant_slug)

    uploaded = await upload_image_to_tenant_php(
        tenant=tenant,
        image=image,
        source=source,
        timestamp=timestamp,
        name=name,
        phone=phone,
        email=email,
        company=company,
    )

    image_bytes = uploaded["file_content"]

    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image size must be less than 10MB")

    raw_text = google_document_text_detection(image_bytes)
    parsed, lines = parse_text(raw_text)

    parsed["image_name"] = uploaded["filename"]
    parsed["image_url"] = uploaded["image_url"]

    return {
        "status": True,
        "tenant": tenant.slug,
        "message": "Business card scanned successfully",
        "data": parsed,
        "selections": build_selections(parsed, lines),
        "rawText": raw_text,
        "image_name": uploaded["filename"],
        "image_url": uploaded["image_url"],
    } 


