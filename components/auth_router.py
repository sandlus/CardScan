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

class SSOLoginRequest(BaseModel):
    token: str


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

# ----------------------------------------
# Check app_user
# ----------------------------------------

        cursor.execute("""
            SELECT
                id,
                fname,
                lname,
                email,
                password,
                role,
                is_active,
                'app_user' AS source_table
            FROM app_user
            WHERE email=%s
            LIMIT 1
        """, (payload.email,))

        app_user = cursor.fetchone()

        # ----------------------------------------
        # Check bay_users
        # ----------------------------------------

        cursor.execute("""
            SELECT
                id,
                fname,
                lname,
                email,
                password,
                role,
                is_active,
                'bay_users' AS source_table
            FROM bay_users
            WHERE email=%s
            LIMIT 1
        """, (payload.email,))

        bay_user = cursor.fetchone()

        entered_password_hash = hashlib.sha1(
            payload.password.encode()
        ).hexdigest()

        user = None

        # Match app_user
        if (
            app_user
            and int(app_user.get("is_active", 0)) == 0
            and app_user["password"] == entered_password_hash
        ):
            user = app_user

        # Match bay_users
        if (
            user is None
            and bay_user
            and int(bay_user.get("is_active", 0)) == 0
            and bay_user["password"] == entered_password_hash
        ):
            user = bay_user

        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )


        # ------------------------------------------------
        # CURRENT PASSWORD CHECK
        # ------------------------------------------------
        # Replace later with bcrypt check
        # ------------------------------------------------

        session_payload = {
            "user_id": user["id"],
            "tenant": tenant.slug,
            "email": user["email"],
            "role": user["role"],
            "source_table": user["source_table"],
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


@router.post("/sso-login")
def sso_login(
    request: Request,
    response: Response,
    data: SSOLoginRequest,
    tenant_slug: str = Depends(resolve_tenant_slug_from_request)
):
    conn = None
    cursor = None

    try:

        token = data.token.strip()

        

        if not token:
            raise HTTPException(
                status_code=400,
                detail="SSO token is required"
            )
        incoming_hash = hashlib.sha256(
            token.encode()
        ).hexdigest()

        tenant = get_tenant_by_slug(
            tenant_slug
        )

        conn = get_connection(
            tenant.db
        )

        cursor = conn.cursor(
            pymysql.cursors.DictCursor
        )

        cursor.execute("""
            SELECT
                id,
                user_id,
                role,
                sso_token,
                expires_at,
                login_time
            FROM logins
            WHERE sso_token=%s
            LIMIT 1
        """, (incoming_hash,))

        login_record = cursor.fetchone()

        if not login_record:
            raise HTTPException(
                status_code=401,
                detail="Invalid SSO token"
            )

        if (
            login_record["expires_at"] is not None
            and login_record["expires_at"] < datetime.utcnow()
        ):
            raise HTTPException(
                status_code=401,
                detail="SSO token has expired"
            )

        # ----------------------------------------
        # Fetch bay_users
        # ----------------------------------------

        cursor.execute("""
            SELECT
                id,
                fname,
                lname,
                email,
                role,
                is_active
            FROM bay_users
            WHERE id=%s
            LIMIT 1
        """, (login_record["user_id"],))

        user = cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=401,
                detail="User not found"
            )

        if int(user.get("is_active", 0)) != 0:
            raise HTTPException(
                status_code=403,
                detail="User account is inactive"
            )
        
        session_payload = {
            "user_id": user["id"],
            "tenant": tenant.slug,
            "email": user["email"],
            "role": user["role"],
            "source_table": "bay_users",
            "name": (
                f"{user.get('fname', '')} "
                f"{user.get('lname', '')}"
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
        "message": "SSO Login successful",
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
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()


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