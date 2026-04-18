# import os
# from fastapi import FastAPI, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel, EmailStr
# from dotenv import load_dotenv
# import pymysql
# from datetime import datetime

# # Load env
# load_dotenv()

# # ================= DB CONNECTION =================
# def get_connection():
#     return pymysql.connect(
#         host=os.getenv("DB_HOST"),
#         port=int(os.getenv("DB_PORT", 3306)),
#         user=os.getenv("DB_USER"),
#         password=os.getenv("DB_PASSWORD"),
#         database=os.getenv("DB_NAME"),
#         cursorclass=pymysql.cursors.DictCursor,
#         autocommit=True
#     )

# # ================= FASTAPI =================
# app = FastAPI()

# # ================= CORS =================
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # 🔴 change in production
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # ================= PYDANTIC MODEL =================
# class ScanCard(BaseModel):
#     level: str | None = None
#     customerCompany: str | None = None
#     personName: str | None = None
#     designation: str | None = None
#     mobile: str | None = None
#     email: EmailStr | None = None
#     address: str | None = None
#     notes: str | None = None

# # ================= HEALTH =================
# @app.get("/")
# def health():
#     return {"status": "API running"}

# # ================= SAVE DATA =================
# @app.post("/save-card")
# def save_card(data: ScanCard):
#     try:
#         conn = get_connection()
#         cursor = conn.cursor()

#         query = """
#         INSERT INTO scan_cards (
#             phone,
#             customer_company,
#             person_name,
#             designation,
#             email,
#             address,
#             level,
#             remark,
#             added_date,
#             added_by
#         )
#         VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
#         """

#         cursor.execute(query, (
#             int(data.mobile) if data.mobile else None,  # phone (bigint)
#             data.customerCompany,
#             data.personName,
#             data.designation,
#             data.email,
#             data.address,
#             data.level,
#             data.notes,  # mapping notes → remark
#             datetime.now(),  # added_date
#             1  # 🔴 you can later replace with logged-in user ID
#         ))

#         inserted_id = cursor.lastrowid

#         cursor.close()
#         conn.close()

#         return {
#             "success": True,
#             "message": "Data saved successfully",
#             "id": inserted_id
#         }

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# # ================= GET ALL =================
# @app.get("/cards")
# def get_cards():
#     try:
#         conn = get_connection()
#         cursor = conn.cursor()

#         cursor.execute("SELECT * FROM scan_cards ORDER BY id DESC")
#         result = cursor.fetchall()

#         cursor.close()
#         conn.close()

#         return result

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

import os
from datetime import datetime

import pymysql
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr


# Load env
load_dotenv()


# ================= ENV HELPERS =================
def parse_csv_env(name: str, default: str = ""):
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


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
allowed_origins = parse_csv_env("ALLOWED_ORIGINS")
allow_credentials = os.getenv("ALLOW_CREDENTIALS", "true").lower() == "true"

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ================= PYDANTIC MODEL =================
class ScanCard(BaseModel):
    level: str | None = None
    customerCompany: str | None = None
    personName: str | None = None
    designation: str | None = None
    mobile: str | None = None
    email: EmailStr | None = None
    address: str | None = None
    notes: str | None = None


# ================= API HEALTH =================
@app.get("/api/health")
def health():
    return {"status": "API running"}


# ================= SAVE DATA =================
@app.post("/save-card")
def save_card(data: ScanCard):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        phone_value = None
        if data.mobile:
            digits = "".join(ch for ch in data.mobile if ch.isdigit())
            phone_value = int(digits) if digits else None

        query = """
        INSERT INTO scan_cards (
            phone,
            customer_company,
            person_name,
            designation,
            email,
            address,
            level,
            remark,
            added_date,
            added_by
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        cursor.execute(query, (
            phone_value,
            data.customerCompany,
            data.personName,
            data.designation,
            data.email,
            data.address,
            data.level,
            data.notes,
            datetime.now(),
            1
        ))

        inserted_id = cursor.lastrowid

        cursor.close()
        conn.close()

        return {
            "success": True,
            "message": "Data saved successfully",
            "id": inserted_id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================= GET ALL =================
@app.get("/cards")
def get_cards():
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM scan_cards ORDER BY id DESC")
        result = cursor.fetchall()

        cursor.close()
        conn.close()

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================= SERVE REACT BUILD =================

# Static files (JS, CSS)
app.mount("/static", StaticFiles(directory="build/static"), name="static")


# Root → React app
@app.get("/")
def serve_react():
    return FileResponse("build/index.html")


# Handle all frontend routes (React Router)
@app.get("/{full_path:path}")
def serve_react_app(full_path: str):
    return FileResponse("build/index.html")