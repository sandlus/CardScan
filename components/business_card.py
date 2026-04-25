# import re
# from fastapi import APIRouter
# from pydantic import BaseModel

# router = APIRouter()


# class BusinessCardText(BaseModel):
#     text: str


# def clean_line(line: str):
#     return re.sub(r"\s+", " ", line).strip()


# def only_digits(value: str):
#     return re.sub(r"\D", "", value or "")


# def last_10_digits(value: str):
#     digits = only_digits(value)
#     if len(digits) >= 10:
#         return digits[-10:]
#     return digits


# @router.post("/business-card/parse")
# def parse_business_card(data: BusinessCardText):
#     raw_text = data.text or ""

#     lines = [
#         clean_line(line)
#         for line in raw_text.splitlines()
#         if clean_line(line)
#     ]

#     full_text = "\n".join(lines)

#     emails = re.findall(
#         r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
#         full_text
#     )

#     phone_candidates = re.findall(
#         r"(?:\+91[\s-]?)?[6-9]\d[\d\s-]{7,12}",
#         full_text
#     )

#     phones = []
#     for phone in phone_candidates:
#         clean_phone = last_10_digits(phone)
#         if len(clean_phone) == 10 and clean_phone not in phones:
#             phones.append(clean_phone)

#     gst_match = re.search(
#         r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z0-9]Z[A-Z0-9]\b",
#         full_text.upper()
#     )

#     company = ""
#     person_name = ""
#     designation = ""
#     address_lines = []
#     notes_lines = []

#     designation_keywords = [
#         "manager",
#         "director",
#         "owner",
#         "sales",
#         "marketing",
#         "executive",
#         "proprietor",
#         "partner",
#         "founder",
#         "ceo",
#         "md",
#         "designer",
#     ]

#     address_keywords = [
#         "floor",
#         "road",
#         "street",
#         "nagar",
#         "sarai",
#         "mal",
#         "market",
#         "delhi",
#         "agra",
#         "chowk",
#         "office",
#         "address",
#         "pin",
#         "110",
#         "201",
#         "uttar",
#         "pradesh",
#     ]

#     ignore_keywords = [
#         "gstin",
#         "mobile",
#         "phone",
#         "email",
#         "www",
#         "http",
#         "estd",
#     ]

#     for index, line in enumerate(lines):
#         lower = line.lower()

#         if any(email.lower() in lower for email in emails):
#             continue

#         if any(phone in only_digits(line) for phone in phones):
#             continue

#         if gst_match and gst_match.group(0).lower() in lower:
#             continue

#         if "deep chand" in lower or "shyam sunder" in lower:
#             company = line
#             continue

#         if any(word in lower for word in designation_keywords) and not designation:
#             designation = line
#             continue

#         if any(word in lower for word in address_keywords):
#             address_lines.append(line)
#             continue

#         if index == 0 and not company and not any(word in lower for word in ignore_keywords):
#             company = line
#         elif not person_name and len(line.split()) <= 3 and not any(word in lower for word in ignore_keywords):
#             person_name = line
#         else:
#             notes_lines.append(line)

#     if not company and lines:
#         company = lines[0]

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
#         "address": ", ".join(address_lines),
#         "notes": " | ".join(notes_lines),
#         "qtyScope": "",
#         "gstin": gst_match.group(0) if gst_match else "",
#         "rawText": raw_text,
#     }

#     selections = []

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
#     }

#     for key, label in labels.items():
#         if parsed.get(key):
#             selections.append({
#                 "label": label,
#                 "value": parsed[key],
#             })

#     for idx, line in enumerate(lines):
#         selections.append({
#             "label": f"Line {idx + 1}",
#             "value": line,
#         })

#     unique = []
#     seen = set()

#     for item in selections:
#         value = item["value"].strip()
#         if value and value not in seen:
#             seen.add(value)
#             unique.append(item)

#     return {
#         "status": True,
#         "data": parsed,
#         "selections": unique,
#     }  

import re
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class BusinessCardText(BaseModel):
    text: str


def clean_line(line: str):
    line = re.sub(r"[|•·]+", " ", line)
    line = re.sub(r"\s+", " ", line)
    return line.strip(" -,:;|")


def only_digits(value: str):
    return re.sub(r"\D", "", value or "")


def normalize_phone(value: str):
    digits = only_digits(value)

    if len(digits) >= 12 and digits.startswith("91"):
        digits = digits[-10:]
    elif len(digits) >= 10:
        digits = digits[-10:]

    if len(digits) == 10 and digits[0] in "6789":
        return digits

    return ""


def unique_list(items):
    output = []
    seen = set()

    for item in items:
        value = clean_line(item)
        key = value.lower()

        if value and key not in seen:
            seen.add(key)
            output.append(value)

    return output


def looks_like_email(line):
    return re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", line)


def looks_like_website(line):
    return re.search(r"(www\.|https?://|\.com|\.in|\.co|\.net|\.org)", line.lower())


def looks_like_phone(line):
    return normalize_phone(line) != ""


def looks_like_gstin(line):
    return re.search(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z0-9]Z[A-Z0-9]\b", line.upper())


def extract_label_value(line):
    lower = line.lower()

    labels = [
        "name",
        "company",
        "designation",
        "title",
        "mobile",
        "phone",
        "email",
        "address",
        "addr",
        "website",
        "web",
        "gstin",
        "gst",
    ]

    for label in labels:
        if lower.startswith(label + ":"):
            return label, line.split(":", 1)[1].strip()

    return "", ""


@router.post("/business-card/parse")
def parse_business_card(data: BusinessCardText):
    raw_text = data.text or ""

    raw_lines = raw_text.splitlines()
    lines = [clean_line(line) for line in raw_lines if clean_line(line)]
    full_text = "\n".join(lines)

    emails = unique_list(
        re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", full_text)
    )

    phone_candidates = re.findall(
        r"(?:\+?\d[\d\s().-]{8,}\d)",
        full_text
    )

    phones = []
    for candidate in phone_candidates:
        phone = normalize_phone(candidate)
        if phone and phone not in phones:
            phones.append(phone)

    gst_match = looks_like_gstin(full_text)
    gstin = gst_match.group(0) if gst_match else ""

    websites = unique_list(
        re.findall(
            r"(?:https?://)?(?:www\.)?[A-Za-z0-9.-]+\.(?:com|in|co|net|org)(?:/[^\s]*)?",
            full_text,
            flags=re.I,
        )
    )

    designation_keywords = [
        "manager", "director", "owner", "sales", "marketing", "executive",
        "proprietor", "partner", "founder", "ceo", "md", "designer",
        "engineer", "consultant", "head", "lead", "architect", "developer",
        "accountant", "chairman", "president", "business development",
    ]

    company_keywords = [
        "pvt", "ltd", "limited", "llp", "inc", "corp", "corporation",
        "company", "enterprise", "enterprises", "industries", "traders",
        "associates", "solutions", "technologies", "tech", "systems",
        "deep chand", "shyam sunder", "agencies", "exports", "imports",
        "group", "store", "studio",
    ]

    address_keywords = [
        "floor", "road", "rd", "street", "st", "nagar", "market", "delhi",
        "agra", "chowk", "office", "address", "pin", "uttar", "pradesh",
        "near", "opp", "opposite", "block", "sector", "phase", "colony",
        "sarai", "mal", "industrial", "estate", "area", "shop", "plot",
        "no.", "no ", "gali", "lane", "marg",
    ]

    company = ""
    person_name = ""
    designation = ""
    address_lines = []
    notes_lines = []

    label_values = {}

    for line in lines:
        label, value = extract_label_value(line)
        if label and value:
            label_values[label] = value

    if label_values.get("name"):
        person_name = label_values.get("name", "")

    if label_values.get("company"):
        company = label_values.get("company", "")

    if label_values.get("designation") or label_values.get("title"):
        designation = label_values.get("designation") or label_values.get("title")

    if label_values.get("address") or label_values.get("addr"):
        address_lines.append(label_values.get("address") or label_values.get("addr"))

    filtered_lines = []

    for line in lines:
        lower = line.lower()

        if looks_like_email(line):
            continue

        if looks_like_phone(line):
            continue

        if looks_like_gstin(line):
            continue

        if looks_like_website(line):
            continue

        if any(lower.startswith(k + ":") for k in label_values.keys()):
            continue

        filtered_lines.append(line)

    for index, line in enumerate(filtered_lines):
        lower = line.lower()

        if not company and any(word in lower for word in company_keywords):
            company = line
            continue

        if not designation and any(word in lower for word in designation_keywords):
            designation = line
            continue

        if any(word in lower for word in address_keywords) or re.search(r"\b\d{6}\b", line):
            address_lines.append(line)
            continue

    if not company:
        for line in filtered_lines[:5]:
            lower = line.lower()
            if len(line) >= 3 and not any(word in lower for word in designation_keywords):
                if len(line.split()) <= 8:
                    company = line
                    break

    if not person_name:
        for line in filtered_lines[:8]:
            lower = line.lower()

            if line == company or line == designation:
                continue

            if any(word in lower for word in company_keywords + address_keywords + designation_keywords):
                continue

            if len(line.split()) <= 4 and not re.search(r"\d", line):
                person_name = line
                break

    for line in filtered_lines:
        if line in [company, person_name, designation]:
            continue

        if line in address_lines:
            continue

        notes_lines.append(line)

    address_lines = unique_list(address_lines)
    notes_lines = unique_list(notes_lines)

    parsed = {
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
        "address": ", ".join(address_lines),
        "notes": " | ".join(notes_lines),
        "qtyScope": "",
        "gstin": gstin,
        "website": websites[0] if websites else "",
        "rawText": raw_text,
    }

    selections = []

    field_labels = {
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

    for key, label in field_labels.items():
        if parsed.get(key):
            selections.append({"label": label, "value": parsed[key]})

    for idx, line in enumerate(lines):
        selections.append({"label": f"Line {idx + 1}", "value": line})

    final_selections = []
    seen = set()

    for item in selections:
        value = clean_line(item.get("value", ""))
        if value and value.lower() not in seen:
            seen.add(value.lower())
            final_selections.append({
                "label": item["label"],
                "value": value,
            })

    return {
        "status": True,
        "data": parsed,
        "selections": final_selections,
    }