import base64
import binascii
import json
import os
import re
from datetime import datetime
from pathlib import Path
from decimal import Decimal
from typing import Any, Dict, List, Optional

import pymysql
import requests
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from google.cloud import vision
from google.oauth2 import service_account

from components.db import get_connection
from components.tenant_resolver import get_tenant_by_slug, resolve_tenant_slug_from_request

router = APIRouter(prefix="/barcode", tags=["Barcode Scanner"])


BARCODE_LABELS = ["barcode", "bar code", "barcode no", "barcode number", "ean", "upc"]
SIZE_LABELS = ["size", "sz"]
COLOR_LABELS = ["color", "colour", "clr"]
MODEL_LABELS = ["model", "model no", "model number", "style", "article", "item code", "item"]
PRICE_LABELS = ["price", "mrp", "m.r.p", "rate", "amount", "rs", "inr"]

PRICE_REGEX = re.compile(r"(?:₹|rs\.?|inr|mrp|m\.r\.p|price|rate)\s*[:：#-]?\s*([0-9]+(?:\.[0-9]{1,2})?)", re.I)
PRICE_NUMBER_REGEX = re.compile(r"([0-9]+(?:\.[0-9]{1,2})?)")
DATE_YYYYMMDD_REGEX = re.compile(r"\b(20\d{2}|19\d{2})(0[1-9]|1[0-2])([0-2]\d|3[01])\b")
BARCODE_REGEX = re.compile(r"\b\d{8,14}\b")
MODEL_NUMBER_REGEX = re.compile(r"\b\d{3,6}\b")
SIZE_VALUE_REGEX = re.compile(r"\b(?:FREE\s*SIZE|XS|S|M|L|XL|XXL|XXXL)\b", re.I)

COMMON_COLORS = [
    "black", "white", "red", "blue", "green", "yellow", "pink", "purple", "orange",
    "brown", "grey", "gray", "navy", "maroon", "beige", "gold", "silver", "cream",
    "multi", "multicolor", "multicolour", "olive", "peach", "violet", "sky", "mustard"
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
                detail=f"Invalid GOOGLE_VISION_CREDENTIALS_JSON: {str(exc)}",
            )

    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if credentials_path:
        try:
            return vision.ImageAnnotatorClient()
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize Google Vision client: {str(exc)}",
            )

    raise HTTPException(
        status_code=500,
        detail="Google Vision credentials not configured. Set GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_VISION_CREDENTIALS_JSON.",
    )


def clean_text(value: str) -> str:
    value = re.sub(r"[|•·]+", " ", value or "")
    value = re.sub(r"\s+", " ", value)
    return value.strip(" -,:;|\t\r\n")


def split_lines(raw_text: str) -> List[str]:
    return [clean_text(line) for line in (raw_text or "").splitlines() if clean_text(line)]


def normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def line_has_label(line: str, labels: List[str]) -> bool:
    normalized_line = normalize_key(line)
    return any(normalize_key(label) in normalized_line for label in labels)


def remove_label(line: str, labels: List[str]) -> str:
    output = line or ""
    for label in labels:
        output = re.sub(rf"\b{re.escape(label)}\b\s*[:：#-]?", "", output, flags=re.I)
    return clean_text(output)


def get_value_by_label(lines: List[str], labels: List[str]) -> str:
    for idx, line in enumerate(lines):
        if not line_has_label(line, labels):
            continue

        value = remove_label(line, labels)
        if value and normalize_key(value) not in [normalize_key(x) for x in labels]:
            return value

        if idx + 1 < len(lines):
            return clean_text(lines[idx + 1])

    return ""


def extract_barcode(lines: List[str], full_text: str) -> str:
    labelled = get_value_by_label(lines, BARCODE_LABELS)
    match = BARCODE_REGEX.search(labelled)
    if match:
        return match.group(0)

    candidates = BARCODE_REGEX.findall(full_text or "")
    filtered = []
    for candidate in candidates:
        if DATE_YYYYMMDD_REGEX.fullmatch(candidate):
            continue
        filtered.append(candidate)

    if filtered:
        return max(filtered, key=len)

    return clean_text(labelled)


def extract_price(lines: List[str], full_text: str) -> str:
    for line in lines:
        if line_has_label(line, PRICE_LABELS) or "₹" in line:
            match = PRICE_REGEX.search(line)
            if match:
                return match.group(1)

            cleaned_line = remove_label(line, PRICE_LABELS)
            match = PRICE_NUMBER_REGEX.search(cleaned_line)
            if match:
                return match.group(1)

    labelled = get_value_by_label(lines, PRICE_LABELS)
    if labelled:
        match = PRICE_NUMBER_REGEX.search(labelled)
        if match:
            return match.group(1)

    return ""


def extract_color(lines: List[str]) -> str:
    labelled = get_value_by_label(lines, COLOR_LABELS)
    if labelled:
        return labelled

    full = " ".join(lines).lower()
    for color in COMMON_COLORS:
        if re.search(rf"\b{re.escape(color)}\b", full):
            return color.title()
    return ""


def extract_model(lines: List[str], barcode: str = "", price: str = "") -> str:
    def valid_model_candidate(value: str, source_line: str = "") -> bool:
        candidate = clean_text(value)
        if not MODEL_NUMBER_REGEX.fullmatch(candidate):
            return False
        if price and candidate == str(price):
            return False
        if barcode and candidate == str(barcode):
            return False
        if DATE_YYYYMMDD_REGEX.fullmatch(candidate):
            return False
        if source_line and line_has_label(source_line, PRICE_LABELS):
            return False
        return True

    labelled = get_value_by_label(lines, MODEL_LABELS)
    if labelled:
        labelled = remove_label(labelled, MODEL_LABELS)
        match = MODEL_NUMBER_REGEX.search(labelled)
        if match and valid_model_candidate(match.group(0), labelled):
            return match.group(0)
        if labelled and labelled not in {barcode, price}:
            return labelled

    for line in lines:
        for candidate in MODEL_NUMBER_REGEX.findall(line):
            if valid_model_candidate(candidate, line):
                return candidate

    return ""


def extract_size(lines: List[str]) -> str:
    full = " ".join(lines)

    match = SIZE_VALUE_REGEX.search(full)
    if match:
        return re.sub(r"\s+", " ", match.group(0).upper()).strip()

    labelled = get_value_by_label(lines, SIZE_LABELS)
    if labelled:
        return labelled

    size_patterns = [
        r"\b\d{1,2}\s*(?:CM|MM|INCH|IN)\b",
        r"\b\d{1,2}\s*[xX×]\s*\d{1,2}\b",
    ]
    for pattern in size_patterns:
        match = re.search(pattern, full, flags=re.I)
        if match:
            return match.group(0).upper()
    return ""


def parse_barcode_text(raw_text: str) -> Dict[str, Any]:
    lines = split_lines(raw_text)
    full_text = "\n".join(lines)

    barcode = extract_barcode(lines, full_text)
    price = extract_price(lines, full_text)

    return {
        "barcode": barcode,
        "size": extract_size(lines),
        "color": extract_color(lines),
        "modelNumber": extract_model(lines, barcode=barcode, price=price),
        "category": "",
        "price": price,
    }


def _serialize_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        value = float(value)
        if value.is_integer():
            return int(value)
        return value
    return value


def build_product_image_url(image_name: Any) -> str:
    image_value = str(image_name or "").strip()

    if not image_value:
        return ""

    if image_value.startswith(("http://", "https://")):
        return image_value

    base_url = os.getenv("DESIPOS_IMAGE_BASE_URL", "").strip().rstrip("/")
    if not base_url:
        return ""

    return f"{base_url}/{image_value.lstrip('/')}"


def get_capture_image_root() -> Path:
    """Folder where scanned item images are stored.

    Local default: ./uploads/barcode_captures
    Railway production recommendation: /data/barcode_captures
    """
    configured_path = os.getenv("BARCODE_CAPTURE_IMAGE_DIR", "./uploads/barcode_captures").strip()
    return Path(configured_path).expanduser().resolve()


def sanitize_path_part(value: Any, fallback: str = "bill") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", str(value or "").strip())
    cleaned = cleaned.strip("-_")
    return cleaned or fallback


def get_capture_image_base_url(request: Request) -> str:
    env_base_url = os.getenv("BARCODE_CAPTURE_IMAGE_BASE_URL", "").strip().rstrip("/")
    if env_base_url:
        return env_base_url
    return str(request.base_url).rstrip("/") + "/barcode/capture-image"


def build_capture_image_url(capture_img: Any, request: Request) -> str:
    capture_value = str(capture_img or "").strip().replace("\\", "/")

    if not capture_value:
        return ""

    if capture_value.startswith(("http://", "https://")):
        return capture_value

    base_url = os.getenv(
        "BARCODE_IMAGE_BASE_URL",
        ""
    ).strip().rstrip("/")

    if not base_url:
        return ""

    return f"{base_url}/{capture_value}"




def upload_image_to_php(
    bill_number: str,
    capture_image_data: str,
) -> str:

    upload_url = os.getenv(
        "BARCODE_UPLOAD_API_URL",
        ""
    ).strip()

    if not upload_url:
        raise HTTPException(
            status_code=500,
            detail="BARCODE_UPLOAD_API_URL not configured."
        )

    # Remove data:image/jpeg;base64,
    image_data = capture_image_data

    match = re.match(
        r"^data:image/([a-zA-Z0-9.+-]+);base64,(.*)$",
        image_data,
        flags=re.S
    )

    extension = "jpg"

    if match:
        extension = match.group(1)
        image_data = match.group(2)

    image_bytes = base64.b64decode(image_data)

    files = {
        "image": (
            f"{bill_number}.{extension}",
            image_bytes,
            f"image/{extension}"
        )
    }

    data = {
        "bill_number": bill_number,
        "type": "capture_barcode"
    }

    response = requests.post(
        upload_url,
        data=data,
        files=files,
        timeout=30
    )

    print("Status Code:", response.status_code)
    print("Response Text:", response.text)

    response.raise_for_status()

    result = response.json()

    if not result.get("status"):
        raise HTTPException(
            status_code=500,
            detail=result.get(
                "message",
                "Image upload failed."
            )
        )

    return str(result.get("filename") or "")
    print("Status Code:", response.status_code)
    print("Response Text:", response.text)

    response.raise_for_status()

    result = response.json()

    if not result.get("status"):
        raise HTTPException(
            status_code=500,
            detail="Image upload failed."
        )

    return str(result.get("filename") or "")

def save_capture_image_from_data_url(
    capture_image_data: Any,
    bill_number: str,
    item_index: int,
    barcode: str = "",
) -> str:
    """Save base64/data-url image into bill-number folder and return relative DB path."""
    image_data = str(capture_image_data or "").strip()
    if not image_data:
        return ""

    extension = "jpg"
    base64_payload = image_data

    data_url_match = re.match(r"^data:image/([a-zA-Z0-9.+-]+);base64,(.*)$", image_data, flags=re.S)
    if data_url_match:
        mime_ext = data_url_match.group(1).lower()
        base64_payload = data_url_match.group(2)
        if mime_ext in {"jpeg", "jpg", "png", "webp"}:
            extension = "jpg" if mime_ext == "jpeg" else mime_ext

    try:
        image_bytes = base64.b64decode(base64_payload, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid capture image data for item {item_index}.") from exc

    if not image_bytes:
        return ""

    if len(image_bytes) > 8 * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"Capture image for item {item_index} is too large.")

    safe_bill_number = sanitize_path_part(bill_number, "bill")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{timestamp}.{extension}"

    root_dir = get_capture_image_root()
    bill_dir = root_dir / safe_bill_number
    bill_dir.mkdir(parents=True, exist_ok=True)

    file_path = bill_dir / filename
    file_path.write_bytes(image_bytes)

    return f"{safe_bill_number}/{filename}"


def normalize_product_row(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not row:
        return None

    item_simage = row.get("item_simage") or ""

    return {
        "item_id": _serialize_value(row.get("item_id")),
        "barcode": str(row.get("barcode") or ""),
        "modelNumber": str(row.get("modelNumber") or ""),
        "category": str(row.get("category") or ""),
        "price": _serialize_value(row.get("price") or ""),
        "product_qty": _serialize_value(row.get("product_qty") or 0),
        "size": str(row.get("size") or ""),
        "color": str(row.get("color") or ""),
        "item_simage": str(item_simage),
        "is_feature_item": _serialize_value(row.get("is_feature_item") or 0),
        
    }


def is_missing_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() in {"", "0", "0.0", "0.00"}
    if isinstance(value, (int, float, Decimal)):
        return value == 0
    return False


def merge_db_with_ocr(db_product: Dict[str, Any], ocr_data: Dict[str, Any]) -> tuple[Dict[str, Any], List[str]]:
    final_product = dict(db_product)
    ocr_filled_fields: List[str] = []

    for key in ["barcode", "modelNumber", "category", "price", "size", "color"]:
        db_value = final_product.get(key)
        ocr_value = ocr_data.get(key)

        if is_missing_value(db_value) and not is_missing_value(ocr_value):
            final_product[key] = ocr_value
            ocr_filled_fields.append(key)

    return final_product, ocr_filled_fields


def get_product_by_barcode(cursor: pymysql.cursors.DictCursor, barcode: str) -> Optional[Dict[str, Any]]:
    query = """
        SELECT
            i.item_id,
            i.barcode,
            i.item_name AS modelNumber,
            COALESCE(c.cat_name, i.item_desc, '') AS category,
            i.item_price AS price,
            i.product_qty,
            COALESCE(ms.name, i.size) AS size,
            COALESCE(mc.name, i.color) AS color,
            i.item_simage AS item_simage,
            i.is_feature_item AS is_feature_item
        FROM item i
        LEFT JOIN master ms
            ON i.size = ms.id
           AND ms.title = 'size'
        LEFT JOIN master mc
            ON i.color = mc.id
           AND mc.title = 'color'
        LEFT JOIN category c
            ON i.cat_id = c.cat_id
        WHERE i.barcode = %s
        LIMIT 1
    """

    cursor.execute(query, (barcode,))
    return normalize_product_row(cursor.fetchone())


def get_products_by_model(cursor: pymysql.cursors.DictCursor, model: str) -> List[Dict[str, Any]]:
    clean_model = str(model or "").strip()
    if not clean_model:
        return []

    like_model = f"%{clean_model}%"
    barcode_prefix = f"{clean_model}%"

    query = """
        SELECT
            i.item_id,
            i.barcode,
            i.item_name AS modelNumber,
            COALESCE(c.cat_name, i.item_desc, '') AS category,
            i.item_price AS price,
            i.product_qty,
            COALESCE(ms.name, i.size) AS size,
            COALESCE(mc.name, i.color) AS color,
            i.item_simage AS item_simage,
            i.is_feature_item AS is_feature_item
        FROM item i
        LEFT JOIN master ms
            ON i.size = ms.id
           AND ms.title = 'size'
        LEFT JOIN master mc
            ON i.color = mc.id
           AND mc.title = 'color'
        LEFT JOIN category c
            ON i.cat_id = c.cat_id
        WHERE i.item_name LIKE %s
           OR i.barcode LIKE %s
        ORDER BY i.item_id DESC
        LIMIT 10
    """

    cursor.execute(query, (like_model, barcode_prefix))
    return [normalize_product_row(row) for row in (cursor.fetchall() or []) if row]


def build_model_suggestions(rows: List[Dict[str, Any]]) -> List[str]:
    suggestions: List[str] = []
    seen = set()

    for row in rows or []:
        model = str((row or {}).get("modelNumber") or "").strip()
        if model and model not in seen:
            seen.add(model)
            suggestions.append(model)

    return suggestions[:10]


def build_selections(parsed: Dict[str, Any], raw_text: str) -> List[Dict[str, str]]:
    labels = {
        "barcode": "Barcode Number",
        "size": "Size",
        "color": "Color",
        "modelNumber": "Model Number",
        "category": "Category",
        "price": "Price",
    }

    selections = []
    for key, label in labels.items():
        value = parsed.get(key)
        if value not in [None, ""]:
            selections.append({"field": key, "label": label, "value": str(value)})

    if raw_text:
        selections.append({"field": "rawText", "label": "Raw OCR Text", "value": raw_text})

    return selections




class HoldBillItemPayload(BaseModel):
    tbl_id: Optional[int] = None
    item_id: Optional[int] = None
    barcode: Optional[str] = ""
    modelNumber: Optional[str] = ""
    category: Optional[str] = ""
    size: Optional[str] = ""
    color: Optional[str] = ""
    price: float = 0
    qty: int = Field(default=1, ge=1)
    captureImageData: Optional[str] = None
    capture_img: Optional[str] = ""

    class Config:
        allow_population_by_field_name = True


class HoldBillPayload(BaseModel):
    billId: Optional[int] = Field(default=None, alias="bill_id")
    billNumber: Optional[str] = Field(default="", alias="bill_number")
    customerName: Optional[str] = Field(default="Walk-In Customer", alias="customer_name")
    customerMobile: Optional[str] = Field(default="", alias="customer_mobile")
    billDate: Optional[str] = Field(default=None, alias="bill_date")
    subtotal: Optional[float] = None
    gstAmount: Optional[float] = Field(default=None, alias="gst_amount")
    totalAmount: Optional[float] = Field(default=None, alias="total_amount")
    items: List[HoldBillItemPayload]

    class Config:
        allow_population_by_field_name = True


def get_bill_number_prefix(cursor: pymysql.cursors.DictCursor) -> str:
    query = """
        SELECT bill_number_prefix
        FROM company_settings
        LIMIT 1
    """
    cursor.execute(query)
    row = cursor.fetchone() or {}
    prefix = str(row.get("bill_number_prefix") or "DES").strip()
    return prefix or "DES"


# def generate_bill_number(cursor: pymysql.cursors.DictCursor, prefix: str) -> str:
#     query = """
#         SELECT bill_id, bill_number
#         FROM bill_details
#         ORDER BY bill_id DESC
#         LIMIT 1
#     """
#     cursor.execute(query)
#     row = cursor.fetchone()

#     last_bill_id = int((row or {}).get("bill_id") or 0)
#     new_bill_id = last_bill_id + 1

#     return f"{prefix}-{new_bill_id:05d}"

def generate_bill_number(cursor, prefix):

    cursor.execute("""
        SELECT bill_number
        FROM bill_details
        WHERE bill_number IS NOT NULL
          AND bill_number <> ''
        ORDER BY bill_id DESC
        LIMIT 1
    """)

    row = cursor.fetchone()

    if not row:
        return f"{prefix}-00001"

    last_bill_number = str(row.get("bill_number") or "").strip()

    try:
        last_sequence = int(last_bill_number.split("-")[-1])
    except Exception:
        last_sequence = 0

    next_sequence = last_sequence + 1

    return f"{prefix}-{next_sequence:05d}"


def find_item_id_for_hold_bill(cursor: pymysql.cursors.DictCursor, item: HoldBillItemPayload) -> int:
    if item.item_id:
        return int(item.item_id)

    barcode = str(item.barcode or "").strip()
    if not barcode:
        raise HTTPException(status_code=400, detail="Every hold bill item must have item_id or barcode.")

    cursor.execute("SELECT item_id FROM item WHERE barcode = %s LIMIT 1", (barcode,))
    row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=400, detail=f"Item not found for barcode: {barcode}")

    return int(row["item_id"])


def calculate_hold_bill_amounts(payload: HoldBillPayload) -> tuple[float, float, float]:
    subtotal = payload.subtotal
    if subtotal is None:
        subtotal = sum((float(item.price or 0) * int(item.qty or 1)) for item in payload.items)

    gst_amount = payload.gstAmount
    if gst_amount is None:
        gst_amount = subtotal * 0.18

    total_amount = payload.totalAmount
    if total_amount is None:
        total_amount = subtotal + gst_amount

    return round(float(subtotal), 2), round(float(gst_amount), 2), round(float(total_amount), 2)


def get_bill_by_id(cursor: pymysql.cursors.DictCursor, bill_id: int) -> Optional[Dict[str, Any]]:
    cursor.execute(
        """
        SELECT bill_id, bill_number, quote_status
        FROM bill_details
        WHERE bill_id = %s
        LIMIT 1
        """,
        (bill_id,),
    )
    return cursor.fetchone()


def upsert_bill_amounts(
    cursor: pymysql.cursors.DictCursor,
    bill_id: int,
    taxable_amount: float,
    gst_amount: float,
    total_amount: float,
    qty_total: int,
) -> None:
    cursor.execute("SELECT bill_amount_id FROM bill_amounts WHERE bill_id = %s LIMIT 1", (bill_id,))
    existing_amount = cursor.fetchone()

    if existing_amount:
        cursor.execute(
            """
            UPDATE bill_amounts
            SET
                bill_item_subtotal = %s,
                bill_item_qtytotal = %s,
                bill_tax_rate = %s,
                bill_tax_amount = %s,
                bill_other_charge = %s,
                bill_total = %s,
                quote_discount = %s,
                quote_discount_rate = %s,
                bill_date_created = CURDATE()
            WHERE bill_id = %s
            """,
            (
                taxable_amount,
                qty_total,
                "18",
                gst_amount,
                0,
                total_amount,
                0,
                "0",
                bill_id,
            ),
        )
        return

    cursor.execute(
        """
        INSERT INTO bill_amounts
        (
            bill_id,
            bill_item_subtotal,
            bill_item_qtytotal,
            bill_tax_rate,
            bill_tax_amount,
            bill_other_charge,
            bill_total,
            quote_discount,
            quote_discount_rate,
            bill_date_created
        )
        VALUES
        (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, CURDATE()
        )
        """,
        (
            bill_id,
            taxable_amount,
            qty_total,
            "18",
            gst_amount,
            0,
            total_amount,
            0,
            "0",
        ),
    )


def save_or_update_bill_item(
    cursor: pymysql.cursors.DictCursor,
    item: HoldBillItemPayload,
    bill_id: int,
    bill_number: str,
    item_index: int,
    request: Request,
) -> Dict[str, Any]:
    item_id = find_item_id_for_hold_bill(cursor, item)
    capture_img = str(item.capture_img or "").strip()

    if item.captureImageData:
        capture_img = upload_image_to_php(
            bill_number=bill_number,
            capture_image_data=item.captureImageData,
        )

    if item.tbl_id:
        cursor.execute(
            """
            UPDATE bill_items
            SET
                item_qty = %s,
                item_price = %s,
                capture_img = COALESCE(%s, capture_img)
            WHERE tbl_id = %s
              AND bill_id = %s
            """,
            (
                int(item.qty or 1),
                float(item.price or 0),
                capture_img or None,
                int(item.tbl_id),
                bill_id,
            ),
        )
        tbl_id = int(item.tbl_id)
    else:
        cursor.execute(
            """
            INSERT INTO bill_items
            (
                bill_id,
                item_id,
                item_qty,
                item_price,
                capture_img
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
                bill_id,
                item_id,
                int(item.qty or 1),
                float(item.price or 0),
                capture_img or None,
            ),
        )
        tbl_id = int(cursor.lastrowid)

    return {
        "tbl_id": tbl_id,
        "item_id": item_id,
        "barcode": item.barcode,
        "modelNumber": item.modelNumber,
        "category": item.category,
        "size": item.size,
        "color": item.color,
        "qty": int(item.qty or 1),
        "price": float(item.price or 0),
        "capture_img": capture_img,
        "captureImageUrl": build_capture_image_url(capture_img, request),
    }


@router.post("/hold-bill")
async def save_hold_bill(
    payload: HoldBillPayload,
    request: Request,
    tenant_slug: str = Depends(resolve_tenant_slug_from_request),
):
    if not payload.items:
        raise HTTPException(status_code=400, detail="Please add items before putting bill on hold.")

    conn = None
    cursor = None

    try:
        tenant = get_tenant_by_slug(tenant_slug)
        conn = get_connection(tenant.db)
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        prefix = get_bill_number_prefix(cursor)
        bill_number = generate_bill_number(cursor, prefix)
        taxable_amount, gst_amount, total_amount = calculate_hold_bill_amounts(payload)

        bill_details_query = """
            INSERT INTO bill_details
            (
                bill_number,
                bill_date,
                quote_status,
                date_created
            )
            VALUES
            (
                %s,
                COALESCE(%s, CURDATE()),
                %s,
                NOW()
            )
        """

        cursor.execute(
            bill_details_query,
            (
                bill_number,
                payload.billDate,
                1,
            ),
        )

        bill_id = cursor.lastrowid

        saved_items = []
        for index, item in enumerate(payload.items, start=1):
            saved_items.append(
                save_or_update_bill_item(
                    cursor=cursor,
                    item=item,
                    bill_id=bill_id,
                    bill_number=bill_number,
                    item_index=index,
                    request=request,
                )
            )

        qty_total = sum(int(item.qty or 1) for item in payload.items)

        bill_amount_query = """
            INSERT INTO bill_amounts
            (
                bill_id,
                bill_item_subtotal,
                bill_item_qtytotal,
                bill_tax_rate,
                bill_tax_amount,
                bill_other_charge,
                bill_total,
                quote_discount,
                quote_discount_rate,
                bill_date_created
            )
            VALUES
            (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, CURDATE()
            )
        """

        cursor.execute(
            bill_amount_query,
            (
                bill_id,
                taxable_amount,
                qty_total,
                "18",
                gst_amount,
                0,
                total_amount,
                0,
                "0",
            ),
        )

        conn.commit()

        return {
            "status": True,
            "tenant": tenant.slug,
            "message": "Bill saved on hold as draft successfully.",
            "data": {
                "bill_id": bill_id,
                "bill_number": bill_number,
                "quote_status": 1,
                "customerName": payload.customerName or "Walk-In Customer",
                "billDate": payload.billDate,
                "taxableAmount": taxable_amount,
                "gstAmount": gst_amount,
                "totalAmount": total_amount,
                "items": saved_items,
            },
        }

    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as exc:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Save hold bill failed: {str(exc)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@router.get("/hold-bills")
async def fetch_hold_bills(
    request: Request,
    tenant_slug: str = Depends(resolve_tenant_slug_from_request),
):
    conn = None
    cursor = None

    try:
        tenant = get_tenant_by_slug(tenant_slug)
        conn = get_connection(tenant.db)
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        bills_query = """
            SELECT
                bd.bill_id,
                bd.bill_number,
                COALESCE(DATE(bd.bill_date), DATE(bd.date_created)) AS bill_date,
                bd.quote_status,
                ba.bill_item_subtotal,
                ba.bill_tax_amount,
                ba.bill_total
            FROM bill_details bd
            LEFT JOIN bill_amounts ba
                ON bd.bill_id = ba.bill_id
            WHERE bd.quote_status = 1
            ORDER BY bd.bill_id DESC
        """

        cursor.execute(bills_query)
        bills = cursor.fetchall() or []

        items_query = """
            SELECT
                bi.bill_id,
                bi.tbl_id,
                bi.item_id,
                bi.item_qty,
                bi.item_price,
                bi.capture_img,
                i.barcode,
                i.item_name AS modelNumber,
                COALESCE(c.cat_name, i.item_desc, '') AS category,
                COALESCE(ms.name, i.size) AS size,
                COALESCE(mc.name, i.color) AS color,
                i.item_simage AS item_simage
            FROM bill_items bi
            JOIN item i
                ON bi.item_id = i.item_id
            LEFT JOIN master ms
                ON i.size = ms.id
               AND ms.title = 'size'
            LEFT JOIN master mc
                ON i.color = mc.id
               AND mc.title = 'color'
            LEFT JOIN category c
                ON i.cat_id = c.cat_id
            WHERE bi.bill_id = %s
            ORDER BY bi.tbl_id ASC
        """

        output = []
        for bill in bills:
            cursor.execute(items_query, (bill["bill_id"],))
            rows = cursor.fetchall() or []

            items = []
            for row in rows:
                item_simage = row.get("item_simage") or ""
                items.append(
                    {
                        "tbl_id": _serialize_value(row.get("tbl_id")),
                        "item_id": _serialize_value(row.get("item_id")),
                        "barcode": str(row.get("barcode") or ""),
                        "modelNumber": str(row.get("modelNumber") or ""),
                        "category": str(row.get("category") or ""),
                        "size": str(row.get("size") or ""),
                        "color": str(row.get("color") or ""),
                        "qty": _serialize_value(row.get("item_qty") or 0),
                        "price": _serialize_value(row.get("item_price") or 0),
                        "item_simage": str(item_simage),
                        "capture_img": str(row.get("capture_img") or ""),
                        "captureImageUrl": build_capture_image_url(row.get("capture_img"), request),
                    }
                )

            output.append(
                {
                    "bill_id": _serialize_value(bill.get("bill_id")),
                    "bill_number": str(bill.get("bill_number") or ""),
                    "customerName": "Walk-In Customer",
                    "billDate": str(bill.get("bill_date") or ""),
                    "status": _serialize_value(bill.get("quote_status") or 1),
                    "taxableAmount": _serialize_value(bill.get("bill_item_subtotal") or 0),
                    "gstAmount": _serialize_value(bill.get("bill_tax_amount") or 0),
                    "totalAmount": _serialize_value(bill.get("bill_total") or 0),
                    "items": items,
                }
            )

        return {
            "status": True,
            "tenant": tenant.slug,
            "message": "Hold bills fetched successfully.",
            "data": output,
            "items": output,
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Fetch hold bills failed: {str(exc)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()



@router.get("/all-bills")
async def fetch_all_bills(
    request: Request,
    from_date: Optional[str] = Query(default=None, description="Filter bills from this date YYYY-MM-DD"),
    to_date: Optional[str] = Query(default=None, description="Filter bills up to this date YYYY-MM-DD"),
    tenant_slug: str = Depends(resolve_tenant_slug_from_request),
):
    """Fetch final submitted bills for the All Bills screen.

    quote_status = 0 means final submitted bill in the current billing flow.
    Optional date filters apply on bill_details.bill_date.
    """
    conn = None
    cursor = None

    try:
        tenant = get_tenant_by_slug(tenant_slug)
        conn = get_connection(tenant.db)
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        filters = ["bd.quote_status = 6"]
        params: List[Any] = []

        bill_filter_date = "COALESCE(DATE(bd.bill_date), DATE(bd.date_created))"

        if from_date:
            filters.append(f"{bill_filter_date} >= %s")
            params.append(from_date)

        if to_date:
            filters.append(f"{bill_filter_date} <= %s")
            params.append(to_date)

        where_clause = " AND ".join(filters)

        query = f"""
            SELECT
                bd.bill_id,
                bd.bill_number,
                COALESCE(DATE(bd.bill_date), DATE(bd.date_created)) AS bill_date,
                bd.quote_status,
                COALESCE(ba.bill_total, 0) AS total_amount,
                COALESCE(ba.bill_item_qtytotal, 0) AS total_qty,
                COUNT(bi.tbl_id) AS item_count
            FROM bill_details bd
            LEFT JOIN bill_amounts ba
                ON bd.bill_id = ba.bill_id
            LEFT JOIN bill_items bi
                ON bd.bill_id = bi.bill_id
            WHERE {where_clause}
            GROUP BY
                bd.bill_id,
                bd.bill_number,
                bd.bill_date,
                bd.quote_status,
                ba.bill_total,
                ba.bill_item_qtytotal
            ORDER BY bd.bill_id DESC
            LIMIT 200
        """

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall() or []

        output = []
        for row in rows:
            output.append(
                {
                    "bill_id": _serialize_value(row.get("bill_id")),
                    "bill_number": str(row.get("bill_number") or ""),
                    "bill_date": str(row.get("bill_date") or ""),
                    "quote_status": _serialize_value(row.get("quote_status") or 0),
                    "total_amount": _serialize_value(row.get("total_amount") or 0),
                    "total_qty": _serialize_value(row.get("total_qty") or 0),
                    "item_count": _serialize_value(row.get("item_count") or 0),
                }
            )

        return {
            "status": True,
            "tenant": tenant.slug,
            "message": "All final bills fetched successfully.",
            "data": output,
            "items": output,
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Fetch all bills failed: {str(exc)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@router.get("/bill-details/{bill_id}")
async def get_bill_details(
    bill_id: int,
    request: Request,
    tenant_slug: str = Depends(resolve_tenant_slug_from_request),
):
    conn = None
    cursor = None

    try:
        tenant = get_tenant_by_slug(tenant_slug)
        conn = get_connection(tenant.db)
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # Bill Header
        cursor.execute(
            """
            SELECT
                bd.bill_id,
                bd.bill_number,
                COALESCE(DATE(bd.bill_date), DATE(bd.date_created)) AS bill_date,
                bd.quote_status,
                COALESCE(ba.bill_item_subtotal,0) AS taxable_amount,
                COALESCE(ba.bill_tax_amount,0) AS gst_amount,
                COALESCE(ba.bill_total,0) AS total_amount
            FROM bill_details bd
            LEFT JOIN bill_amounts ba
                ON bd.bill_id = ba.bill_id
            WHERE bd.bill_id = %s
            LIMIT 1
            """,
            (bill_id,),
        )

        bill = cursor.fetchone()

        if not bill:
            raise HTTPException(
                status_code=404,
                detail="Bill not found."
            )

        # Bill Items
        cursor.execute(
            """
            SELECT
                bi.tbl_id,
                bi.item_id,
                bi.item_qty,
                bi.item_price,
                bi.capture_img,
                i.barcode,
                i.item_name AS modelNumber,
                COALESCE(c.cat_name, i.item_desc, '') AS category,
                COALESCE(ms.name, i.size) AS size,
                COALESCE(mc.name, i.color) AS color,
                i.item_simage
            FROM bill_items bi
            JOIN item i
                ON bi.item_id = i.item_id
            LEFT JOIN master ms
                ON i.size = ms.id
               AND ms.title = 'size'
            LEFT JOIN master mc
                ON i.color = mc.id
               AND mc.title = 'color'
            LEFT JOIN category c
                ON i.cat_id = c.cat_id
            WHERE bi.bill_id = %s
            ORDER BY bi.tbl_id ASC
            """,
            (bill_id,),
        )

        rows = cursor.fetchall() or []

        items = []

        for row in rows:
            item_simage = row.get("item_simage") or ""

            items.append(
                {
                    "tbl_id": _serialize_value(row.get("tbl_id")),
                    "item_id": _serialize_value(row.get("item_id")),
                    "barcode": str(row.get("barcode") or ""),
                    "modelNumber": str(row.get("modelNumber") or ""),
                    "category": str(row.get("category") or ""),
                    "size": str(row.get("size") or ""),
                    "color": str(row.get("color") or ""),
                    "qty": _serialize_value(row.get("item_qty") or 0),
                    "price": _serialize_value(row.get("item_price") or 0),
                    "item_simage": str(item_simage),
                    "capture_img": str(row.get("capture_img") or ""),
                    "captureImageUrl": build_capture_image_url(
                        row.get("capture_img"),
                        request
                    ),
                }
            )

        return {
            "status": True,
            "tenant": tenant.slug,
            "message": "Bill details fetched successfully.",
            "data": {
                "bill_id": _serialize_value(bill.get("bill_id")),
                "bill_number": str(bill.get("bill_number") or ""),
                "bill_date": str(bill.get("bill_date") or ""),
                "quote_status": _serialize_value(bill.get("quote_status") or 0),
                "taxableAmount": _serialize_value(
                    bill.get("taxable_amount") or 0
                ),
                "gstAmount": _serialize_value(
                    bill.get("gst_amount") or 0
                ),
                "totalAmount": _serialize_value(
                    bill.get("total_amount") or 0
                ),
                "customerName": "Walk-In Customer",
                "items": items,
            },
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Fetch bill details failed: {str(exc)}"
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@router.get("/thermal-print/{bill_id}")
async def thermal_print_data(
    bill_id: int,
    request: Request,
    tenant_slug: str = Depends(resolve_tenant_slug_from_request),
):
    conn = None
    cursor = None

    try:
        tenant = get_tenant_by_slug(tenant_slug)

        conn = get_connection(tenant.db)
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        cursor.execute(
            """
            SELECT
                bd.bill_id,
                bd.bill_number,
                COALESCE(DATE(bd.bill_date), DATE(bd.date_created)) AS bill_date,
                COALESCE(ba.bill_total,0) AS total_amount
            FROM bill_details bd
            LEFT JOIN bill_amounts ba
                ON bd.bill_id = ba.bill_id
            WHERE bd.bill_id = %s
            LIMIT 1
            """,
            (bill_id,),
        )

        bill = cursor.fetchone()

        if not bill:
            raise HTTPException(
                status_code=404,
                detail="Bill not found."
            )

        cursor.execute(
            """
            SELECT
                bi.item_qty,
                bi.item_price,
                i.barcode,
                i.item_name AS modelNumber,
                COALESCE(ms.name, i.size) AS size,
                COALESCE(mc.name, i.color) AS color
            FROM bill_items bi
            JOIN item i
                ON bi.item_id = i.item_id
            LEFT JOIN master ms
                ON i.size = ms.id
               AND ms.title = 'size'
            LEFT JOIN master mc
                ON i.color = mc.id
               AND mc.title = 'color'
            WHERE bi.bill_id = %s
            ORDER BY bi.tbl_id
            """,
            (bill_id,),
        )

        rows = cursor.fetchall() or []

        items = []

        for row in rows:
            qty = int(row.get("item_qty") or 0)
            price = float(row.get("item_price") or 0)

            items.append(
                {
                    "barcode": str(row.get("barcode") or ""),
                    "modelNumber": str(row.get("modelNumber") or ""),
                    "size": str(row.get("size") or ""),
                    "color": str(row.get("color") or ""),
                    "qty": qty,
                    "price": price,
                    "amount": round(qty * price, 2),
                }
            )

        return {
            "status": True,
            "tenant": tenant.slug,
            "message": "Thermal print data fetched successfully.",
            "data": {
                "bill_id": bill["bill_id"],
                "bill_number": bill["bill_number"],
                "bill_date": str(bill["bill_date"]),
                "customer_name": "Walk-In Customer",
                "total_amount": float(
                    bill.get("total_amount") or 0
                ),
                "items": items,
            },
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Thermal print failed: {str(exc)}"
        )

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()

@router.post("/submit-bill")
async def submit_bill(
    payload: HoldBillPayload,
    request: Request,
    tenant_slug: str = Depends(resolve_tenant_slug_from_request),
):
    """Submit a bill.

    - If bill_id is not supplied: create a new final bill with quote_status = 0.
    - If bill_id is supplied: finalize the existing hold bill by changing quote_status from 1 to 0,
      update existing rows with tbl_id, insert only newly-added rows, and update bill_amounts.
    """
    if not payload.items:
        raise HTTPException(status_code=400, detail="Please add items before submitting bill.")

    conn = None
    cursor = None

    try:
        tenant = get_tenant_by_slug(tenant_slug)
        conn = get_connection(tenant.db)
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        taxable_amount, gst_amount, total_amount = calculate_hold_bill_amounts(payload)
        qty_total = sum(int(item.qty or 1) for item in payload.items)

        is_existing_hold_bill = bool(payload.billId)

        if is_existing_hold_bill:
            bill_row = get_bill_by_id(cursor, int(payload.billId))
            if not bill_row:
                raise HTTPException(status_code=404, detail="Hold bill not found.")

            bill_id = int(bill_row["bill_id"])
            bill_number = str(bill_row.get("bill_number") or payload.billNumber or "").strip()
            if not bill_number:
                raise HTTPException(status_code=400, detail="Bill number not found for selected hold bill.")

            cursor.execute(
                """
                UPDATE bill_details
                SET
                    quote_status = %s,
                    bill_date = COALESCE(%s, bill_date)
                WHERE bill_id = %s
                """,
                (6, payload.billDate, bill_id),
            )
        else:
            prefix = get_bill_number_prefix(cursor)
            bill_number = generate_bill_number(cursor, prefix)

            cursor.execute(
                """
                INSERT INTO bill_details
                (
                    bill_number,
                    bill_date,
                    quote_status,
                    date_created
                )
                VALUES
                (
                    %s,
                    COALESCE(%s, CURDATE()),
                    %s,
                    NOW()
                )
                """,
                (bill_number, payload.billDate, 6),
            )
            bill_id = int(cursor.lastrowid)

        saved_items = []
        for index, item in enumerate(payload.items, start=1):
            saved_items.append(
                save_or_update_bill_item(
                    cursor=cursor,
                    item=item,
                    bill_id=bill_id,
                    bill_number=bill_number,
                    item_index=index,
                    request=request,
                )
            )

        upsert_bill_amounts(
            cursor=cursor,
            bill_id=bill_id,
            taxable_amount=taxable_amount,
            gst_amount=gst_amount,
            total_amount=total_amount,
            qty_total=qty_total,
        )

        conn.commit()

        return {
            "status": True,
            "tenant": tenant.slug,
            "message": "Hold bill submitted successfully." if is_existing_hold_bill else "Bill submitted successfully.",
            "data": {
                "bill_id": bill_id,
                "bill_number": bill_number,
                "quote_status": 6,
                "customerName": payload.customerName or "Walk-In Customer",
                "billDate": payload.billDate,
                "taxableAmount": taxable_amount,
                "gstAmount": gst_amount,
                "totalAmount": total_amount,
                "items": saved_items,
            },
        }

    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as exc:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Submit bill failed: {str(exc)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@router.get("/capture-image/{capture_path:path}")
async def get_capture_image(capture_path: str):
    safe_capture_path = str(capture_path or "").strip().replace("\\", "/")

    if not safe_capture_path or ".." in Path(safe_capture_path).parts:
        raise HTTPException(status_code=400, detail="Invalid image path.")

    root_dir = get_capture_image_root()
    file_path = (root_dir / safe_capture_path).resolve()

    if root_dir not in file_path.parents and file_path != root_dir:
        raise HTTPException(status_code=400, detail="Invalid image path.")

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Capture image not found.")

    return FileResponse(str(file_path))


@router.get("/model-search")
async def search_products_by_model_number(
    request: Request,
    model: str = Query("", description="Model number or barcode prefix"),
    tenant_slug: str = Depends(resolve_tenant_slug_from_request),
):
    clean_model = str(model or "").strip()

    if not clean_model:
        return {
            "status": True,
            "tenant": tenant_slug,
            "model": clean_model,
            "message": "Please enter a model number.",
            "suggestions": [],
            "items": [],
        }

    conn = None
    cursor = None

    try:
        tenant = get_tenant_by_slug(tenant_slug)
        conn = get_connection(tenant.db)
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        items = get_products_by_model(cursor, clean_model)

        return {
            "status": True,
            "tenant": tenant.slug,
            "model": clean_model,
            "message": "Model data found" if items else "No item data found for this model number.",
            "suggestions": build_model_suggestions(items),
            "items": items,
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Model search failed: {str(exc)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@router.post("/scan")
async def scan_barcode(
    request: Request,
    file: UploadFile = File(...),
    tenant_slug: str = Depends(resolve_tenant_slug_from_request),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Please upload a valid image file.")

    conn = None
    cursor = None

    try:
        image_bytes = await file.read()
        if not image_bytes:
            raise HTTPException(status_code=400, detail="Uploaded image is empty.")

        client = get_vision_client()
        image = vision.Image(content=image_bytes)
        response = client.text_detection(image=image)

        if response.error.message:
            raise HTTPException(status_code=500, detail=response.error.message)

        raw_text = ""
        if response.text_annotations:
            raw_text = response.text_annotations[0].description or ""

        ocr_parsed = parse_barcode_text(raw_text)
        barcode = ocr_parsed.get("barcode") or ""

        if not barcode:
            return {
                "status": False,
                "tenant": tenant_slug,
                "message": "Barcode number could not be detected from the image.",
                "data": ocr_parsed,
                "ocrFilledFields": [],
                "rawText": raw_text,
                "selections": build_selections(ocr_parsed, raw_text),
            }

        tenant = get_tenant_by_slug(tenant_slug)
        conn = get_connection(tenant.db)
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        db_product = get_product_by_barcode(cursor, barcode)

        if db_product:
            final_product, ocr_filled_fields = merge_db_with_ocr(db_product, ocr_parsed)

            return {
                "status": True,
                "tenant": tenant.slug,
                "source": "database_with_ocr_merge" if ocr_filled_fields else "database",
                "message": "Product details fetched from database successfully.",
                "data": final_product,
                "ocrData": ocr_parsed,
                "ocrFilledFields": ocr_filled_fields,
                "rawText": raw_text,
                "selections": build_selections(final_product, raw_text),
            }

        ocr_filled_fields = [
                key for key in ["barcode", "modelNumber", "category", "price", "size", "color"]
                if not is_missing_value(ocr_parsed.get(key))
            ]

        return {
                "status": True,
                "tenant": tenant.slug,
                "source": "ocr_fallback",
                "message": "Barcode detected, but product was not found in database. Showing OCR values.",
                "data": ocr_parsed,
                "ocrFilledFields": ocr_filled_fields,
                "rawText": raw_text,
                "selections": build_selections(ocr_parsed, raw_text),
            }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Barcode scan failed: {str(exc)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
