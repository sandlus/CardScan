# import json
# import os
# import re
# from typing import Dict, List

# from fastapi import APIRouter, File, HTTPException, UploadFile
# from google.cloud import vision
# from google.oauth2 import service_account
# from pydantic import BaseModel

# router = APIRouter()


# class BusinessCardText(BaseModel):
#     text: str


# def get_vision_client():
#     json_key = os.getenv("GOOGLE_VISION_CREDENTIALS_JSON")

#     if json_key:
#         credentials_info = json.loads(json_key)
#         credentials = service_account.Credentials.from_service_account_info(
#             credentials_info
#         )
#         return vision.ImageAnnotatorClient(credentials=credentials)

#     return vision.ImageAnnotatorClient()


# def clean_line(line: str) -> str:
#     line = re.sub(r"[|•·]+", " ", line or "")
#     line = re.sub(r"\s+", " ", line)
#     return line.strip(" -,:;|")


# def only_digits(value: str) -> str:
#     return re.sub(r"\D", "", value or "")


# def normalize_phone(value: str) -> str:
#     digits = only_digits(value)

#     if len(digits) >= 12 and digits.startswith("91"):
#         digits = digits[-10:]
#     elif len(digits) >= 10:
#         digits = digits[-10:]

#     if len(digits) == 10 and digits[0] in "6789":
#         return digits

#     return ""


# def unique_list(items: List[str]) -> List[str]:
#     output = []
#     seen = set()

#     for item in items:
#         value = clean_line(item)
#         key = value.lower()

#         if value and key not in seen:
#             seen.add(key)
#             output.append(value)

#     return output


# def extract_gstin(text: str) -> str:
#     match = re.search(
#         r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z0-9]Z[A-Z0-9]\b",
#         (text or "").upper(),
#     )
#     return match.group(0) if match else ""


# def looks_like_email(line: str) -> bool:
#     return bool(
#         re.search(
#             r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
#             line or "",
#         )
#     )


# def looks_like_phone(line: str) -> bool:
#     return normalize_phone(line) != ""


# def looks_like_website(line: str) -> bool:
#     return bool(
#         re.search(
#             r"(www\.|https?://|\.[a-z]{2,4}\b)",
#             (line or "").lower(),
#         )
#     )


# def is_probable_address(line: str) -> bool:
#     lowered = (line or "").lower()

#     keywords = [
#         "floor", "road", "street", "nagar", "market", "delhi", "agra",
#         "chowk", "office", "address", "pin", "uttar", "pradesh",
#         "near", "opp", "opposite", "block", "sector", "colony",
#         "shop", "plot", "gali", "lane", "marg", "malviya",
#         "nai sarak", "maliwara", "industrial", "estate", "area",
#     ]

#     return any(word in lowered for word in keywords) or bool(
#         re.search(r"\b\d{6}\b", line or "")
#     )


# def is_probable_designation(line: str) -> bool:
#     lowered = (line or "").lower()

#     keywords = [
#         "manager", "director", "owner", "sales", "marketing",
#         "executive", "proprietor", "partner", "founder", "ceo",
#         "md", "designer", "engineer", "consultant", "head",
#         "lead", "developer", "accountant", "chairman", "president",
#     ]

#     return any(word in lowered for word in keywords)


# def is_probable_name(line: str) -> bool:
#     if not line or re.search(r"\d", line):
#         return False

#     words = line.split()

#     if not 1 <= len(words) <= 4:
#         return False

#     lowered = line.lower()

#     blocked = [
#         "pvt", "ltd", "limited", "llp", "enterprise", "solutions",
#         "technologies", "road", "street", "nagar", "market", "office",
#         "floor", "gali", "chowk", "sector", "address", "gstin",
#         "sarees", "lehenga", "gowns", "suits", "designer",
#     ]

#     return not any(word in lowered for word in blocked)


# def score_company_candidate(line: str) -> int:
#     lowered = line.lower()
#     score = 0

#     company_words = [
#         "pvt", "ltd", "limited", "llp", "enterprise", "enterprises",
#         "solutions", "technologies", "textiles", "fashion", "studio",
#         "traders", "industries", "exports", "imports", "group",
#         "sarees", "gowns", "suits", "designer",
#     ]

#     if line.isupper():
#         score += 3

#     if len(line.split()) >= 2:
#         score += 2

#     if any(word in lowered for word in company_words):
#         score += 4

#     if looks_like_phone(line) or looks_like_email(line) or looks_like_website(line):
#         score -= 5

#     if is_probable_address(line):
#         score -= 3

#     return score


# def build_selections(parsed: Dict[str, str], lines: List[str]) -> List[Dict[str, str]]:
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

#     selections = []

#     for key, label in labels.items():
#         if parsed.get(key):
#             selections.append({"label": label, "value": parsed[key]})

#     for index, line in enumerate(lines):
#         if line:
#             selections.append({"label": f"Line {index + 1}", "value": line})

#     final = []
#     seen = set()

#     for item in selections:
#         value = clean_line(item["value"])
#         key = value.lower()

#         if value and key not in seen:
#             seen.add(key)
#             final.append({"label": item["label"], "value": value})

#     return final


# def parse_text(raw_text: str):
#     lines = [clean_line(line) for line in raw_text.splitlines() if clean_line(line)]
#     full_text = "\n".join(lines)

#     emails = unique_list(
#         re.findall(
#             r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
#             full_text,
#         )
#     )

#     websites = unique_list(
#         re.findall(
#             r"(?:https?://)?(?:www\.)?[A-Za-z0-9.-]+\.(?:com|in|co|net|org)(?:/[^\s]*)?",
#             full_text,
#             flags=re.I,
#         )
#     )

#     phone_candidates = re.findall(r"(?:\+?\d[\d\s().-]{8,}\d)", full_text)
#     phones = []

#     for candidate in phone_candidates:
#         phone = normalize_phone(candidate)
#         if phone and phone not in phones:
#             phones.append(phone)

#     gstin = extract_gstin(full_text)

#     clean_candidates = []
#     for line in lines:
#         lower = line.lower()

#         if looks_like_email(line):
#             continue
#         if looks_like_phone(line):
#             continue
#         if looks_like_website(line):
#             continue
#         if gstin and gstin.lower() in lower:
#             continue

#         clean_candidates.append(line)

#     company = ""
#     person_name = ""
#     designation = ""
#     address_lines = []
#     notes_lines = []

#     scored_companies = sorted(
#         [(score_company_candidate(line), line) for line in clean_candidates[:8]],
#         reverse=True,
#     )

#     if scored_companies and scored_companies[0][0] > 0:
#         company = scored_companies[0][1]

#     for line in clean_candidates:
#         if line == company:
#             continue

#         if not designation and is_probable_designation(line):
#             designation = line
#             continue

#         if not person_name and is_probable_name(line):
#             person_name = line
#             continue

#         if is_probable_address(line):
#             address_lines.append(line)
#         else:
#             notes_lines.append(line)

#     parsed = {
#         "type": "",
#         "level": "",
#         "category": "",
#         "product": "",
#         "item_data": [],
#         "customerCompany": company,
#         "personName": person_name,
#         "designation": designation,
#         "mobile": phones[0] if len(phones) > 0 else "",
#         "mobile2": phones[1] if len(phones) > 1 else "",
#         "email": emails[0] if len(emails) > 0 else "",
#         "email2": emails[1] if len(emails) > 1 else "",
#         "address": ", ".join(unique_list(address_lines)),
#         "notes": " | ".join(unique_list(notes_lines)),
#         "qtyScope": "",
#         "gstin": gstin,
#         "website": websites[0] if websites else "",
#         "rawText": raw_text,
#     }

#     return parsed, lines


# def google_document_text_detection(image_bytes: bytes) -> str:
#     client = get_vision_client()

#     image = vision.Image(content=image_bytes)

#     image_context = vision.ImageContext(
#         language_hints=["en"]
#     )

#     response = client.document_text_detection(
#         image=image,
#         image_context=image_context,
#     )

#     if response.error.message:
#         raise HTTPException(status_code=500, detail=response.error.message)

#     if response.full_text_annotation and response.full_text_annotation.text:
#         return response.full_text_annotation.text

#     return ""


# @router.post("/business-card/scan")
# async def scan_business_card(file: UploadFile = File(...)):
#     if not file.content_type or not file.content_type.startswith("image/"):
#         raise HTTPException(status_code=400, detail="Only image files are allowed")

#     image_bytes = await file.read()

#     if not image_bytes:
#         raise HTTPException(status_code=400, detail="Empty image file")

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
#         "data": parsed,
#         "selections": build_selections(parsed, lines),
#         "rawText": data.text or "",
#     } 

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, File, HTTPException, UploadFile
from google.cloud import vision
from google.oauth2 import service_account
from pydantic import BaseModel

router = APIRouter()


class BusinessCardText(BaseModel):
    text: str


EMAIL_REGEX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
WEBSITE_REGEX = re.compile(
    r"(?:https?://)?(?:www\.)?[A-Za-z0-9][A-Za-z0-9.-]+\.(?:com|in|co|net|org|io|biz|info|me|tech|ai)(?:/[^\s]*)?",
    re.I,
)
PHONE_BLOCK_REGEX = re.compile(r"(?:\+?\d[\d\s()./-]{7,}\d)")
GSTIN_REGEX = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z0-9]Z[A-Z0-9]\b", re.I)

DESIGNATION_WORDS = [
    "manager", "director", "owner", "sales", "marketing", "executive",
    "proprietor", "partner", "founder", "co-founder", "ceo", "cto", "cfo",
    "md", "designer", "engineer", "consultant", "head", "lead", "developer",
    "accountant", "chairman", "president", "admin", "hr", "officer", "agent",
    "specialist", "advisor", "architect", "analyst", "secretary"
]

ADDRESS_WORDS = [
    "floor", "road", "street", "st.", "nagar", "market", "chowk", "office",
    "address", "pin", "uttar", "pradesh", "near", "opp", "opposite", "block",
    "sector", "colony", "shop", "plot", "gali", "lane", "marg", "industrial",
    "estate", "area", "tower", "building", "complex", "plaza", "suite", "city",
    "district", "state", "india", "agra", "delhi", "mumbai", "jaipur", "noida",
    "gurgaon", "bangalore", "hyderabad", "pincode", "pin code"
]

COMPANY_HINTS = [
    "pvt", "pvt.", "ltd", "ltd.", "limited", "llp", "inc", "corp", "corporation",
    "company", "co.", "enterprises", "enterprise", "solutions", "technology",
    "technologies", "tech", "traders", "industries", "exports", "imports",
    "group", "studio", "agency", "associates", "systems", "services", "fashion",
    "textiles", "digital", "software", "consultancy", "pharma", "labs"
]

NAME_BLOCKLIST = [
    "pvt", "ltd", "limited", "llp", "enterprise", "enterprises", "solutions",
    "technologies", "technology", "road", "street", "nagar", "market", "office",
    "floor", "gali", "chowk", "sector", "address", "gstin", "india", "website",
    "www", "email", "mobile", "phone", "tel", "contact"
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
        return vision.ImageAnnotatorClient()

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


def normalize_phone(value: str) -> str:
    digits = digits_only(value)

    if len(digits) > 10 and digits.startswith("91"):
        digits = digits[-10:]
    elif len(digits) > 10:
        digits = digits[-10:]

    if len(digits) == 10 and digits[0] in "6789":
        return digits

    return ""


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
    phones: List[str] = []
    for candidate in PHONE_BLOCK_REGEX.findall(text or ""):
        phone = normalize_phone(candidate)
        if phone and phone not in phones:
            phones.append(phone)
    return phones


def extract_gstin(text: str) -> str:
    match = GSTIN_REGEX.search((text or "").upper())
    return match.group(0) if match else ""


def looks_like_email(line: str) -> bool:
    return bool(EMAIL_REGEX.search(line or ""))


def looks_like_phone(line: str) -> bool:
    return bool(normalize_phone(line))


def looks_like_website(line: str) -> bool:
    return bool(WEBSITE_REGEX.search(line or ""))


def is_probable_address(line: str) -> bool:
    lowered = (line or "").lower()
    if any(word in lowered for word in ADDRESS_WORDS):
        return True
    if re.search(r"\b\d{6}\b", line or ""):
        return True
    if "," in line and any(ch.isdigit() for ch in line):
        return True
    return False


def is_probable_designation(line: str) -> bool:
    lowered = (line or "").lower()
    return any(word in lowered for word in DESIGNATION_WORDS)


def is_all_caps_like(line: str) -> bool:
    letters = re.sub(r"[^A-Za-z]", "", line or "")
    return bool(letters) and letters.isupper()


def looks_like_person_name(line: str) -> bool:
    if not line:
        return False
    if re.search(r"\d", line):
        return False
    if looks_like_email(line) or looks_like_website(line):
        return False

    words = [w for w in re.split(r"\s+", line.strip()) if w]
    if not 1 <= len(words) <= 4:
        return False

    lowered = line.lower()
    if any(word in lowered for word in NAME_BLOCKLIST):
        return False

    alpha_words = [w for w in words if re.search(r"[A-Za-z]", w)]
    if not alpha_words:
        return False

    title_like = 0
    for word in alpha_words:
        pure = re.sub(r"[^A-Za-z]", "", word)
        if pure and (pure[0].isupper() or pure.isupper()):
            title_like += 1

    return title_like >= max(1, len(alpha_words) - 1)


def score_company_candidate(line: str, index: int) -> int:
    lowered = line.lower()
    score = 0

    if not line:
        return -100

    if looks_like_email(line) or looks_like_phone(line) or looks_like_website(line):
        return -100

    if is_probable_address(line):
        score -= 5

    if any(word in lowered for word in COMPANY_HINTS):
        score += 8

    if len(line.split()) >= 2:
        score += 2

    if is_all_caps_like(line):
        score += 3

    if index <= 2:
        score += 3

    if looks_like_person_name(line):
        score -= 3

    if is_probable_designation(line):
        score -= 2

    return score


def split_lines(raw_text: str) -> List[str]:
    raw_lines = raw_text.splitlines() if raw_text else []
    cleaned = [clean_line(line) for line in raw_lines]
    return [line for line in cleaned if line]


def pick_company(lines: List[str]) -> str:
    candidates: List[Tuple[int, str]] = []

    for idx, line in enumerate(lines[:10]):
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
        if is_probable_designation(line):
            return line
    return ""


def pick_name(lines: List[str], company: str, designation: str) -> str:
    for idx, line in enumerate(lines[:8]):
        if line in {company, designation}:
            continue
        if looks_like_person_name(line):
            return line

    if company:
        company_index = next((i for i, l in enumerate(lines) if l == company), -1)
        if company_index != -1:
            for line in lines[company_index + 1: company_index + 4]:
                if line not in {designation} and looks_like_person_name(line):
                    return line

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
        if looks_like_email(line) or looks_like_phone(line) or looks_like_website(line):
            continue
        if extract_gstin(line):
            continue
        if is_probable_address(line):
            continue
        notes.append(line)

    return " | ".join(unique_list(notes))


def parse_text(raw_text: str) -> Tuple[Dict[str, Any], List[str]]:
    lines = split_lines(raw_text)
    full_text = "\n".join(lines)

    emails = extract_emails(full_text)
    websites = extract_websites(full_text)
    phones = extract_phones(full_text)
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
        "mobile": phones[0] if len(phones) > 0 else "",
        "mobile2": phones[1] if len(phones) > 1 else "",
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


@router.post("/business-card/scan")
async def scan_business_card(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty image file")

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