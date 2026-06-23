from datetime import datetime
from typing import Optional

import pymysql
import hashlib
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Cookie
from pydantic import BaseModel, EmailStr

from components.auth import (
    create_user_session,
    delete_session,
    get_session_data
)
from components.db import get_connection
from components.tenant_resolver import (
    get_tenant_by_slug,
    resolve_tenant_slug_from_request
)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/login")
def login(
    payload: LoginRequest,
    response: Response,
    tenant_slug: str = Depends(
        resolve_tenant_slug_from_request
    )
):
    conn = None
    cursor = None

    try:
        tenant = get_tenant_by_slug(
            tenant_slug
        )

        conn = get_connection(
            tenant.db
        )

        cursor = conn.cursor(
            pymysql.cursors.DictCursor
        )

        query = """
            SELECT
                id,
                fname,
                lname,
                email,
                password,
                role,
                is_active
            FROM app_user
            WHERE email=%s
            LIMIT 1
        """

        cursor.execute(
            query,
            (payload.email,)
        )

        user = cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )

        if int(user.get("is_active", 0)) != 0:
            raise HTTPException(
                status_code=403,
                detail="User account is inactive"
            )

        # ------------------------------------------------
        # CURRENT PASSWORD CHECK
        # ------------------------------------------------
        # Replace later with bcrypt check
        # ------------------------------------------------

        print("DB EMAIL:", user["email"])
        print("DB PASSWORD:", repr(user["password"]))
        print("ENTERED PASSWORD:", repr(payload.password))
        print("HASH GENERATED:", entered_password_hash)
        print("IS_ACTIVE:", user["is_active"])

        

        entered_password_hash = hashlib.sha1(
            payload.password.encode()
        ).hexdigest()

        if user["password"] != entered_password_hash:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )
           

        session_payload = {
            "user_id": user["id"],
            "tenant": tenant.slug,
            "email": user["email"],
            "role": user["role"],
            "name": (
                f"{user.get('fname','')} "
                f"{user.get('lname','')}"
            ).strip(),
            "login_time": datetime.utcnow().isoformat()
        }

        session_id = create_user_session(
            session_payload
        )

        response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        secure=True,
        samesite="None",
        max_age=28800
        )

        return {
            "status": True,
            "message": "Login successful",
            "user": {
                "id": user["id"],
                "name": session_payload["name"],
                "email": user["email"],
                "role": user["role"]
            }
        }

    except HTTPException:
        raise

    except Exception as e:
        print(
            "LOGIN ERROR:",
            str(e)
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()


@router.post("/logout")
def logout(
    response: Response,
    session_id: Optional[str] = Cookie(
        default=None
    )
):
    if session_id:
        delete_session(
            session_id
        )

    response.delete_cookie(
    key="session_id",
    secure=True,
    samesite="None"
    )

    return {
        "status": True,
        "message": "Logout successful"
    }


@router.get("/me")
def current_user(
    tenant_slug: str = Depends(
        resolve_tenant_slug_from_request
    ),
    session_id: Optional[str] = Cookie(
        default=None
    )
):
    session = get_session_data(
        session_id
    )

    if not session:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )

    if session.get("tenant") != tenant_slug:
        raise HTTPException(
            status_code=403,
            detail="Invalid tenant session"
        )

    return {
        "status": True,
        "user": session
    }