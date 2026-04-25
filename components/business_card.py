import re
from typing import List, Dict

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class BusinessCardText(BaseModel):
    text: str


def clean_line(line: str) -> str:
    line = re.sub(r"[|•·]+", " ", line or "")
    line = re.sub(r"\s+", " ", line)
    return line.strip(" -,:;|")


def only_digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def normalize_phone(value: str) -> str:
    digits = only_digits(value)

    if len(digits) >= 12 and digits.startswith("91"):
        digits = digits[-10:]
    elif len(digits) >= 10:
        digits = digits[-10:]

    if len(digits) == 10 and digits[0] in "6789":
        return digits

    return ""


def unique_list(items: List[str]) -> List[str]:
    output: List[str] = []
    seen = set()

    for item in items:
        value = clean_line(item)
        key = value.lower()
        if value and key not in seen:
            seen.add(key)
            output.append(value)

    return output


def looks_like_email(line: str) -> bool:
    return bool(re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", line or ""))


def looks_like_website(line: str) -> bool:
    return bool(re.search(r"(www\.|https?://|\.[a-z]{2,4}\b)", (line or "").lower()))


def looks_like_phone(line: str) -> bool:
    return normalize_phone(line) != ""


def extract_gstin(text: str) -> str:
    match = re.search(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z0-9]Z[A-Z0-9]\b", (text or "").upper())
    return match.group(0) if match else ""


def extract_label_value(line: str):
    lower = (line or "").lower().strip()
    labels = [
        "name", "company", "designation", "title", "mobile", "phone",
        "email", "address", "addr", "website", "web", "gstin", "gst"
    ]

    for label in labels:
        prefix = f"{label}:"
        if lower.startswith(prefix):
            return label, line.split(":", 1)[1].strip()

    return "", ""


def is_probable_name(line: str) -> bool:
    if not line or re.search(r"\d", line):
        return False

    words = [w for w in re.split(r"\s+", line.strip()) if w]
    if not (1 <= len(words) <= 5):
        return False

    lowered = line.lower()
    blocked = [
        "pvt", "ltd", "limited", "llp", "enterprise", "enterprises", "solutions",
        "technologies", "tech", "road", "street", "nagar", "market", "office",
        "floor", "gali", "chowk", "sector", "block", "address", "gstin", "www"
    ]
    if any(token in lowered for token in blocked):
        return False

    uppercase_words = sum(1 for w in words if w[:1].isupper() or w.isupper())
    return uppercase_words >= max(1, len(words) - 1)


def is_probable_company(line: str) -> bool:
    lowered = (line or "").lower()
    company_keywords = [
        "pvt", "ltd", "limited", "llp", "inc", "corp", "corporation", "company",
        "enterprise", "enterprises", "industries", "traders", "associates", "solutions",
        "technologies", "tech", "systems", "exports", "imports", "group", "store",
        "studio", "agency", "agencies", "fashion", "boutique", "textiles", "dcss"
    ]
    return any(word in lowered for word in company_keywords)


def is_probable_designation(line: str) -> bool:
    lowered = (line or "").lower()
    designation_keywords = [
        "manager", "director", "owner", "sales", "marketing", "executive", "proprietor",
        "partner", "founder", "ceo", "md", "designer", "engineer", "consultant",
        "head", "lead", "architect", "developer", "accountant", "chairman", "president",
        "business development"
    ]
    return any(word in lowered for word in designation_keywords)


def is_probable_address(line: str) -> bool:
    lowered = (line or "").lower()
    address_keywords = [
        "floor", "road", "rd", "street", "st", "nagar", "market", "delhi", "agra",
        "chowk", "office", "address", "pin", "uttar", "pradesh", "near", "opp",
        "opposite", "block", "sector", "phase", "colony", "sarai", "industrial",
        "estate", "area", "shop", "plot", "gali", "lane", "marg", "malviya", "nai sarak"
    ]
    return any(word in lowered for word in address_keywords) or bool(re.search(r"\b\d{6}\b", line or ""))


def score_company_candidate(line: str) -> int:
    score = 0
    lowered = line.lower()
    if is_probable_company(line):
        score += 4
    if len(line.split()) >= 2:
        score += 1
    if line.isupper():
        score += 1
    if re.search(r"\b(estd|since)\b", lowered):
        score += 1
    if re.search(r"\bdcss\b", lowered):
        score += 3
    if is_probable_address(line) or is_probable_designation(line):
        score -= 2
    if looks_like_phone(line) or looks_like_email(line) or looks_like_website(line):
        score -= 3
    return score


def build_selections(parsed: Dict[str, str], lines: List[str]) -> List[Dict[str, str]]:
    selections: List[Dict[str, str]] = []
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

    final_selections: List[Dict[str, str]] = []
    seen = set()
    for item in selections:
        value = clean_line(item.get("value", ""))
        key = value.lower()
        if value and key not in seen:
            seen.add(key)
            final_selections.append({"label": item["label"], "value": value})

    return final_selections


@router.post("/business-card/parse")
def parse_business_card(data: BusinessCardText):
    raw_text = data.text or ""
    lines = [clean_line(line) for line in raw_text.splitlines() if clean_line(line)]
    full_text = "\n".join(lines)

    emails = unique_list(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", full_text))

    phone_candidates = re.findall(r"(?:\+?\d[\d\s().-]{8,}\d)", full_text)
    phones: List[str] = []
    for candidate in phone_candidates:
        phone = normalize_phone(candidate)
        if phone and phone not in phones:
            phones.append(phone)

    gstin = extract_gstin(full_text)

    websites = unique_list(
        re.findall(
            r"(?:https?://)?(?:www\.)?[A-Za-z0-9.-]+\.(?:com|in|co|net|org)(?:/[^\s]*)?",
            full_text,
            flags=re.I,
        )
    )

    label_values: Dict[str, str] = {}
    for line in lines:
        label, value = extract_label_value(line)
        if label and value and label not in label_values:
            label_values[label] = value

    company = label_values.get("company", "")
    person_name = label_values.get("name", "")
    designation = label_values.get("designation") or label_values.get("title", "")
    address_lines: List[str] = []
    if label_values.get("address"):
        address_lines.append(label_values["address"])
    if label_values.get("addr"):
        address_lines.append(label_values["addr"])
    notes_lines: List[str] = []

    filtered_lines: List[str] = []
    for line in lines:
        lower = line.lower()
        if looks_like_email(line) or looks_like_phone(line) or looks_like_website(line):
            continue
        if gstin and gstin.lower() in lower:
            continue
        if any(lower.startswith(f"{k}:") for k in label_values.keys()):
            continue
        filtered_lines.append(line)

    if not company:
        scored = sorted(((score_company_candidate(line), line) for line in filtered_lines[:8]), reverse=True)
        if scored and scored[0][0] > 0:
            company = scored[0][1]

    if not designation:
        for line in filtered_lines[:10]:
            if line != company and is_probable_designation(line):
                designation = line
                break

    if not person_name:
        for line in filtered_lines[:10]:
            if line in {company, designation}:
                continue
            if is_probable_name(line):
                person_name = line
                break

    for line in filtered_lines:
        if line in {company, person_name, designation}:
            continue
        if is_probable_address(line):
            address_lines.append(line)
        else:
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

    return {
        "status": True,
        "data": parsed,
        "selections": build_selections(parsed, lines),
    }
