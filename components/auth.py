# components/auth.py

import json
import os
import uuid
from typing import Optional, Dict, Any

from components.redis_manager import get_redis_client


SESSION_PREFIX = os.getenv(
    "SESSION_PREFIX",
    "session"
)

SESSION_TTL_SECONDS = int(
    os.getenv(
        "SESSION_TTL_SECONDS",
        "28800"
    )
)


def build_session_key(
    session_id: str
) -> str:
    return f"{SESSION_PREFIX}:{session_id}"


def create_user_session(
    user_data: Dict[str, Any]
) -> str:
    """
    Create Redis session and return session_id
    """

    redis_client = get_redis_client()

    session_id = str(uuid.uuid4())

    redis_key = build_session_key(
        session_id
    )

    redis_client.setex(
        redis_key,
        SESSION_TTL_SECONDS,
        json.dumps(user_data)
    )

    return session_id


def get_session_data(
    session_id: Optional[str]
) -> Optional[Dict[str, Any]]:
    """
    Get session data from Redis
    """

    if not session_id:
        return None

    redis_client = get_redis_client()

    redis_key = build_session_key(
        session_id
    )

    session_data = redis_client.get(
        redis_key
    )

    if not session_data:
        return None

    try:
        return json.loads(
            session_data
        )
    except Exception:
        return None


def refresh_session(
    session_id: str
) -> bool:
    """
    Refresh session expiry
    """

    if not session_id:
        return False

    redis_client = get_redis_client()

    redis_key = build_session_key(
        session_id
    )

    if not redis_client.exists(
        redis_key
    ):
        return False

    redis_client.expire(
        redis_key,
        SESSION_TTL_SECONDS
    )

    return True


def delete_session(
    session_id: Optional[str]
) -> bool:
    """
    Delete session from Redis
    """

    if not session_id:
        return False

    redis_client = get_redis_client()

    redis_key = build_session_key(
        session_id
    )

    deleted = redis_client.delete(
        redis_key
    )

    return deleted > 0


def session_exists(
    session_id: Optional[str]
) -> bool:
    """
    Check if session exists
    """

    if not session_id:
        return False

    redis_client = get_redis_client()

    redis_key = build_session_key(
        session_id
    )

    return bool(
        redis_client.exists(
            redis_key
        )
    )