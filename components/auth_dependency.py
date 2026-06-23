from typing import Optional

from fastapi import Cookie, Depends, HTTPException, Request

from components.auth import (
    get_session_data,
    refresh_session,
)
from components.tenant_resolver import (
    resolve_tenant_slug_from_request,
)


def get_current_user(
    request: Request,
    tenant_slug: str = Depends(
        resolve_tenant_slug_from_request
    ),
    session_id: Optional[str] = Cookie(
        default=None
    ),
):
    """
    Validate Redis session and tenant.

    Returns:
        dict -> session payload

    Raises:
        401 -> not authenticated
        403 -> tenant mismatch
    """

    if not session_id:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )

    session = get_session_data(
        session_id
    )

    if not session:
        raise HTTPException(
            status_code=401,
            detail="Session expired or invalid"
        )

    session_tenant = (
        str(
            session.get(
                "tenant",
                ""
            )
        )
        .strip()
        .lower()
    )

    current_tenant = (
        str(tenant_slug)
        .strip()
        .lower()
    )

    if session_tenant != current_tenant:
        raise HTTPException(
            status_code=403,
            detail="Invalid tenant session"
        )

    # Sliding session expiry
    refresh_session(
        session_id
    )

    return session


def get_current_user_optional(
    request: Request,
    tenant_slug: str = Depends(
        resolve_tenant_slug_from_request
    ),
    session_id: Optional[str] = Cookie(
        default=None
    ),
):
    """
    Optional version.

    Returns:
        dict | None
    """

    if not session_id:
        return None

    session = get_session_data(
        session_id
    )

    if not session:
        return None

    session_tenant = (
        str(
            session.get(
                "tenant",
                ""
            )
        )
        .strip()
        .lower()
    )

    current_tenant = (
        str(tenant_slug)
        .strip()
        .lower()
    )

    if session_tenant != current_tenant:
        return None

    refresh_session(
        session_id
    )

    return session