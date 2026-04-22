# import json
# import os
# from datetime import datetime

# from dotenv import load_dotenv
# from fastapi import Depends, FastAPI, HTTPException, Request
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import FileResponse
# from fastapi.staticfiles import StaticFiles
# from pydantic import BaseModel, EmailStr, field_validator

# from components.catalog import router as catalog_router
# from components.db import get_connection
# from components.image_upload import router as image_upload_router
# from components.tenant_config import TENANTS
# from components.tenant_resolver import get_tenant_by_slug, resolve_tenant_slug_from_request

# load_dotenv()

# app = FastAPI()


# # ================= CORS =================
# allowed_origins = set()

# for tenant in TENANTS.values():
#     for host in tenant.allowed_hosts:
#         allowed_origins.add(f"https://{host}")
#         allowed_origins.add(f"http://{host}")

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=list(allowed_origins) if allowed_origins else ["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# # ================= MODEL =================
# class ScanCard(BaseModel):
#     type: str | None = None
#     level: str | None = None
#     category: str | None = None
#     product: str | None = None
#     item_data: list[dict] | None = None
#     customerCompany: str | None = None
#     personName: str | None = None
#     designation: str | None = None
#     mobile: str | None = None
#     mobile2: str | None = None
#     email: EmailStr | None = None
#     email2: EmailStr | None = None
#     address: str | None = None
#     notes: str | None = None
#     qtyScope: str | None = None
#     image_name: str | None = None

#     @field_validator("email", "email2", mode="before")
#     @classmethod
#     def empty_email_to_none(cls, v):
#         if v == "" or v is None:
#             return None
#         return v


# # ================= HELPERS =================
# def clean(val):
#     return val.strip() if val and str(val).strip() else None


# def clean_phone(val):
#     if not val:
#         return None
#     digits = "".join(ch for ch in str(val) if ch.isdigit())
#     return digits if digits else None


# # ================= ROUTERS =================
# app.include_router(catalog_router)
# app.include_router(image_upload_router)


# # ================= HEALTH =================
# @app.get("/api/health")
# def health():
#     return {"status": "API running"}


# @app.get("/tenant-debug")
# def tenant_debug(
#     request: Request,
#     tenant_slug: str = Depends(resolve_tenant_slug_from_request)
# ):
#     tenant = get_tenant_by_slug(tenant_slug)
#     return {
#         "status": True,
#         "tenant": tenant.slug,
#         "database": tenant.db.database,
#         "host": request.headers.get("host"),
#         "origin": request.headers.get("origin"),
#         "referer": request.headers.get("referer"),
#         "path": request.url.path
#     }


# # ================= SAVE DATA =================
# @app.post("/save-card")
# def save_card(
#     data: ScanCard,
#     tenant_slug: str = Depends(resolve_tenant_slug_from_request)
# ):
#     conn = None
#     cursor = None

#     try:
#         tenant = get_tenant_by_slug(tenant_slug)

#         print("Incoming Tenant:", tenant.slug)
#         print("Incoming Data:", data.model_dump())

#         conn = get_connection(tenant.db)
#         cursor = conn.cursor()

#         item_data_json = json.dumps(data.item_data or [], ensure_ascii=False)

#         query = """
#         INSERT INTO scan_cards (
#             type,
#             level,
#             item_data,
#             customer_company,
#             person_name,
#             designation,
#             phone,
#             other_phone,
#             email,
#             email2,
#             address,
#             remark,
#             qty,
#             card_image,
#             added_date,
#             added_by
#         )
#         VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
#         """

#         cursor.execute(query, (
#             clean(data.type),
#             clean(data.level),
#             item_data_json,
#             clean(data.customerCompany),
#             clean(data.personName),
#             clean(data.designation),
#             clean_phone(data.mobile),
#             clean_phone(data.mobile2),
#             clean(data.email),
#             clean(data.email2),
#             clean(data.address),
#             clean(data.notes),
#             clean(data.qtyScope),
#             clean(data.image_name),
#             datetime.now(),
#             1
#         ))

#         inserted_id = cursor.lastrowid

#         return {
#             "success": True,
#             "tenant": tenant.slug,
#             "database": tenant.db.database,
#             "message": "Data saved successfully",
#             "id": inserted_id
#         }

#     except Exception as e:
#         print("ERROR:", str(e))
#         raise HTTPException(status_code=500, detail=str(e))

#     finally:
#         if cursor:
#             cursor.close()
#         if conn:
#             conn.close()


# # ================= GET ALL =================
# @app.get("/cards")
# def get_cards(
#     tenant_slug: str = Depends(resolve_tenant_slug_from_request)
# ):
#     conn = None
#     cursor = None

#     try:
#         tenant = get_tenant_by_slug(tenant_slug)
#         conn = get_connection(tenant.db)
#         cursor = conn.cursor()

#         cursor.execute("SELECT * FROM scan_cards ORDER BY id DESC")
#         result = cursor.fetchall()

#         return {
#             "status": True,
#             "tenant": tenant.slug,
#             "data": result
#         }

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

#     finally:
#         if cursor:
#             cursor.close()
#         if conn:
#             conn.close()


# # ================= SERVE REACT =================
# BUILD_DIR = "build"

# static_path = os.path.join(BUILD_DIR, "static")
# if os.path.exists(static_path):
#     app.mount("/static", StaticFiles(directory=static_path), name="static")


# @app.get("/")
# def serve_react():
#     index_path = os.path.join(BUILD_DIR, "index.html")
#     if os.path.exists(index_path):
#         return FileResponse(index_path)
#     return {"status": "API running"}


# @app.get("/{full_path:path}")
# def serve_react_app(full_path: str):
#     index_path = os.path.join(BUILD_DIR, "index.html")
#     if os.path.exists(index_path):
#         return FileResponse(index_path)
#     return {"error": "Frontend not built"}  

import json
import os
from datetime import datetime

import requests
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, field_validator

from components.catalog import router as catalog_router
from components.db import get_connection
from components.tenant_config import TENANTS
from components.tenant_resolver import get_tenant_by_slug, resolve_tenant_slug_from_request

load_dotenv()

app = FastAPI()


allowed_origins = set()

for tenant in TENANTS.values():
    for host in tenant.allowed_hosts:
        allowed_origins.add(f"https://{host}")
        allowed_origins.add(f"http://{host}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(allowed_origins) if allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ScanCard(BaseModel):
    type: str | None = None
    level: str | None = None
    category: str | None = None
    product: str | None = None
    item_data: list[dict] | None = None
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
    image_name: str | None = None

    @field_validator("email", "email2", mode="before")
    @classmethod
    def empty_email_to_none(cls, v):
        if v == "" or v is None:
            return None
        return v


def clean(val):
    return val.strip() if val and str(val).strip() else None


def clean_phone(val):
    if not val:
        return None
    digits = "".join(ch for ch in str(val) if ch.isdigit())
    return digits if digits else None


app.include_router(catalog_router)


@app.get("/api/health")
def health():
    return {"status": "API running"}


@app.get("/tenant-debug")
def tenant_debug(
    request: Request,
    tenant_slug: str = Depends(resolve_tenant_slug_from_request),
):
    tenant = get_tenant_by_slug(tenant_slug)
    return {
        "status": True,
        "tenant": tenant.slug,
        "database": tenant.db.database,
        "host": request.headers.get("host"),
        "origin": request.headers.get("origin"),
        "referer": request.headers.get("referer"),
        "path": request.url.path,
    }


@app.get("/branding")
def get_branding(
    tenant_slug: str = Depends(resolve_tenant_slug_from_request),
):
    tenant = get_tenant_by_slug(tenant_slug)

    fallback = {
        "status": True,
        "tenant": tenant.slug,
        "company_name": tenant.slug.title(),
        "logo": "",
        "primary_color": "#4F46E5",
        "back_url": tenant.client_domain or "",
        "favicon": "",
    }

    if not tenant.branding_api:
        return fallback

    try:
        response = requests.get(tenant.branding_api, timeout=8)
        response.raise_for_status()
        data = response.json()

        return {
            "status": True,
            "tenant": tenant.slug,
            "company_name": data.get("company_name") or fallback["company_name"],
            "logo": data.get("logo") or fallback["logo"],
            "primary_color": data.get("primary_color") or fallback["primary_color"],
            "back_url": data.get("back_url") or fallback["back_url"],
            "favicon": data.get("favicon") or data.get("logo") or fallback["favicon"],
        }

    except Exception as e:
        print("BRANDING ERROR:", str(e))
        return fallback


@app.post("/save-card")
def save_card(
    data: ScanCard,
    tenant_slug: str = Depends(resolve_tenant_slug_from_request),
):
    conn = None
    cursor = None

    try:
        tenant = get_tenant_by_slug(tenant_slug)

        print("Incoming Tenant:", tenant.slug)
        print("Incoming Data:", data.model_dump())

        conn = get_connection(tenant.db)
        cursor = conn.cursor()

        item_data_json = json.dumps(data.item_data or [], ensure_ascii=False)

        query = """
        INSERT INTO scan_cards (
            type,
            level,
            item_data,
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
            card_image,
            added_date,
            added_by
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        cursor.execute(
            query,
            (
                clean(data.type),
                clean(data.level),
                item_data_json,
                clean(data.customerCompany),
                clean(data.personName),
                clean(data.designation),
                clean_phone(data.mobile),
                clean_phone(data.mobile2),
                clean(data.email),
                clean(data.email2),
                clean(data.address),
                clean(data.notes),
                clean(data.qtyScope),
                clean(data.image_name),
                datetime.now(),
                1,
            ),
        )

        inserted_id = cursor.lastrowid

        return {
            "success": True,
            "tenant": tenant.slug,
            "database": tenant.db.database,
            "message": "Data saved successfully",
            "id": inserted_id,
        }

    except Exception as e:
        print("ERROR:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.get("/cards")
def get_cards(
    tenant_slug: str = Depends(resolve_tenant_slug_from_request),
):
    conn = None
    cursor = None

    try:
        tenant = get_tenant_by_slug(tenant_slug)
        conn = get_connection(tenant.db)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM scan_cards ORDER BY id DESC")
        result = cursor.fetchall()

        return {
            "status": True,
            "tenant": tenant.slug,
            "data": result,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


BUILD_DIR = "build"

static_path = os.path.join(BUILD_DIR, "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.get("/")
def serve_react():
    index_path = os.path.join(BUILD_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"status": "API running"}


@app.get("/{full_path:path}")
def serve_react_app(full_path: str):
    index_path = os.path.join(BUILD_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "Frontend not built"}