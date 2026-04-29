import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Literal

import jwt
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY is not set in .env")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))


class TokenError(Exception):
    """Raised when a token is missing, expired, or tampered with."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(admin_id: int, user_id: int, username: str, user_type: str) -> str:
    """
    Short-lived token (default 30 min).
    Carries the account data the dashboard needs on every request.
    """
    now = _now()
    payload = {
        "sub": str(admin_id),
        "admin_id": admin_id,
        "user_id": user_id,
        "username": username,
        "user_type": user_type,
        "type": "access",
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(admin_id: int) -> tuple[str, str]:
    """
    Long-lived token (default 7 days).
    Returns (encoded_token, jti) — the jti is what gets stored in Redis.
    Carries minimal data; account details come from the DB on refresh.
    """
    now = _now()
    jti = str(uuid.uuid4())
    payload = {
        "sub": str(admin_id),
        "admin_id": admin_id,
        "type": "refresh",
        "jti": jti,
        "iat": now,
        "exp": now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM), jti


def decode_access_token(token: str) -> dict:
    """
    Decode and validate an access token.
    Raises TokenError on any problem (expired, tampered, wrong type).
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise TokenError("Access token has expired")
    except jwt.InvalidTokenError as exc:
        raise TokenError(f"Invalid access token: {exc}")

    if payload.get("type") != "access":
        raise TokenError("Token is not an access token")
    return payload


def decode_refresh_token(token: str) -> dict:
    """
    Decode and validate a refresh token structure only.
    The caller must still verify the jti exists in Redis.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise TokenError("Refresh token has expired")
    except jwt.InvalidTokenError as exc:
        raise TokenError(f"Invalid refresh token: {exc}")

    if payload.get("type") != "refresh":
        raise TokenError("Token is not a refresh token")
    return payload
