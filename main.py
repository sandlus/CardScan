import os
from datetime import datetime

import pymysql
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, field_validator

from components.catalog import router as catalog_router
from components.image_upload import router as image_upload_router


# Load env
load_dotenv()


# ================= DB CONNECTION =================
def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )


# ================= FASTAPI =================
app = FastAPI()


# ================= CORS =================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # change in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ================= MODEL =================
class ScanCard(BaseModel):
    type: str | None = None
    level: str | None = None
    category: str | None = None
    product: str | None = None
    item_id: int | None = None   # ✅ ADD THIS
    customerCompany: str | None = None
    personName: str | None = None
    designation: str | None = None
    mobile: str | None = None
    mobile2: str | None = None
    email: EmailStr | None = None
    email2: EmailStr | None = None
    address: str | None = None
    notes: str | None = None
    qtyScope: str | None = None
     # ✅ ADD THIS
    image_name: str | None = None

    @field_validator("email", "email2", mode="before")
    @classmethod
    def empty_email_to_none(cls, v):
        if v == "" or v is None:
            return None
        return v


# ================= HELPERS =================
def clean(val):
    return val.strip() if val and str(val).strip() else None


def clean_phone(val):
    if not val:
        return None
    digits = "".join(ch for ch in str(val) if ch.isdigit())
    return digits if digits else None


# 🔗 Register single router
app.include_router(catalog_router)
app.include_router(image_upload_router)


# ================= API =================
@app.get("/api/health")
def health():
    return {"status": "API running"}


# ================= SAVE DATA =================
@app.post("/save-card")
def save_card(data: ScanCard):
    conn = None
    cursor = None

    try:
        print("Incoming Data:", data.model_dump())

        conn = get_connection()
        cursor = conn.cursor()

        query = """
        INSERT INTO scan_cards (
            type,
            level,
            item_id,   -- ✅ ADD
            customer_company,
            person_name,
            designation,
            phone,
            other_phone,
            email,
            email2,
            address,
            remark,
            qty,
            card_image,   -- ✅ ADD THIS
            added_date,
            added_by
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        cursor.execute(query, (
            clean(data.type),
            clean(data.level),
            data.item_id,  # ✅ ADD (no clean needed for int)
            clean(data.customerCompany),
            clean(data.personName),
            clean(data.designation),
            clean_phone(data.mobile),
            clean_phone(data.mobile2),
            clean(data.email),
            clean(data.email2),
            clean(data.address),
            clean(data.notes),
            clean(data.qtyScope),   # frontend qtyScope -> DB qty
            data.image_name,   # ✅ THIS IS YOUR FILENAME
            datetime.now(),
            1
        ))

        inserted_id = cursor.lastrowid

        return {
            "success": True,
            "message": "Data saved successfully",
            "id": inserted_id
        }

    except Exception as e:
        print("ERROR:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ================= GET ALL =================
@app.get("/cards")
def get_cards():
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM scan_cards ORDER BY id DESC")
        result = cursor.fetchall()

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ================= SERVE REACT (SAFE) =================
BUILD_DIR = "build"


# Mount static only if exists
static_path = os.path.join(BUILD_DIR, "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")


# Root route
@app.get("/")
def serve_react():
    index_path = os.path.join(BUILD_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"status": "API running"}


# React Router support
@app.get("/{full_path:path}")
def serve_react_app(full_path: str):
    index_path = os.path.join(BUILD_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "Frontend not built"}