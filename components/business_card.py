import re
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class BusinessCardText(BaseModel):
    text: str


def clean_line(line: str):
    return re.sub(r"\s+", " ", line).strip()


def only_digits(value: str):
    return re.sub(r"\D", "", value or "")


def last_10_digits(value: str):
    digits = only_digits(value)
    if len(digits) >= 10:
        return digits[-10:]
    return digits


@router.post("/business-card/parse")
def parse_business_card(data: BusinessCardText):
    raw_text = data.text or ""

    lines = [
        clean_line(line)
        for line in raw_text.splitlines()
        if clean_line(line)
    ]

    full_text = "\n".join(lines)

    emails = re.findall(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        full_text
    )

    phone_candidates = re.findall(
        r"(?:\+91[\s-]?)?[6-9]\d[\d\s-]{7,12}",
        full_text
    )

    phones = []
    for phone in phone_candidates:
        clean_phone = last_10_digits(phone)
        if len(clean_phone) == 10 and clean_phone not in phones:
            phones.append(clean_phone)

    gst_match = re.search(
        r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z0-9]Z[A-Z0-9]\b",
        full_text.upper()
    )

    company = ""
    person_name = ""
    designation = ""
    address_lines = []
    notes_lines = []

    designation_keywords = [
        "manager",
        "director",
        "owner",
        "sales",
        "marketing",
        "executive",
        "proprietor",
        "partner",
        "founder",
        "ceo",
        "md",
        "designer",
    ]

    address_keywords = [
        "floor",
        "road",
        "street",
        "nagar",
        "sarai",
        "mal",
        "market",
        "delhi",
        "agra",
        "chowk",
        "office",
        "address",
        "pin",
        "110",
        "201",
        "uttar",
        "pradesh",
    ]

    ignore_keywords = [
        "gstin",
        "mobile",
        "phone",
        "email",
        "www",
        "http",
        "estd",
    ]

    for index, line in enumerate(lines):
        lower = line.lower()

        if any(email.lower() in lower for email in emails):
            continue

        if any(phone in only_digits(line) for phone in phones):
            continue

        if gst_match and gst_match.group(0).lower() in lower:
            continue

        if "deep chand" in lower or "shyam sunder" in lower:
            company = line
            continue

        if any(word in lower for word in designation_keywords) and not designation:
            designation = line
            continue

        if any(word in lower for word in address_keywords):
            address_lines.append(line)
            continue

        if index == 0 and not company and not any(word in lower for word in ignore_keywords):
            company = line
        elif not person_name and len(line.split()) <= 3 and not any(word in lower for word in ignore_keywords):
            person_name = line
        else:
            notes_lines.append(line)

    if not company and lines:
        company = lines[0]

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
        "gstin": gst_match.group(0) if gst_match else "",
        "rawText": raw_text,
    }

    selections = []

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
    }

    for key, label in labels.items():
        if parsed.get(key):
            selections.append({
                "label": label,
                "value": parsed[key],
            })

    for idx, line in enumerate(lines):
        selections.append({
            "label": f"Line {idx + 1}",
            "value": line,
        })

    unique = []
    seen = set()

    for item in selections:
        value = item["value"].strip()
        if value and value not in seen:
            seen.add(value)
            unique.append(item)

    return {
        "status": True,
        "data": parsed,
        "selections": unique,
    }