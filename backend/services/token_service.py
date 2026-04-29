"""
Token service — issues, rotates, and revokes access+refresh token pairs.

Storage layout in Redis:
  Key  : refresh:{jti}
  Value: JSON {"admin_id": int, "username": str, "user_type": str}
  TTL  : REFRESH_TOKEN_EXPIRE_DAYS * 86400 seconds

On every /refresh call the old JTI is deleted and a brand-new one is stored
(token rotation). If the same refresh token is presented twice, the second
call finds no JTI in Redis and is rejected — this detects token theft.
"""
import json
from sqlalchemy.orm import Session

from core.jwt import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    REFRESH_TOKEN_EXPIRE_DAYS,
    TokenError,
)
from core.cache import redis_client
from models.admins import Admin

REFRESH_TTL = REFRESH_TOKEN_EXPIRE_DAYS * 86_400


def _redis_key(jti: str) -> str:
    return f"refresh:{jti}"


def _store_refresh(jti: str, admin: Admin) -> None:
    payload = json.dumps({
        "admin_id": admin.id,
        "username": admin.username,
        "user_type": "admin",
    })
    redis_client.set(_redis_key(jti), payload, ex=REFRESH_TTL)


def issue_token_pair(admin: Admin) -> dict:
    """
    Called after successful login.
    Returns both tokens and the expiry hint for the frontend.
    """
    access_token = create_access_token(
        admin_id=admin.id,
        user_id=admin.user_id,
        username=admin.username,
        user_type="admin",
    )
    refresh_token, jti = create_refresh_token(admin_id=admin.id)
    _store_refresh(jti, admin)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 30 * 60,  # seconds, matches ACCESS_TOKEN_EXPIRE_MINUTES
    }


def refresh_token_pair(refresh_token: str, db: Session) -> dict:
    """
    Validate the refresh token, rotate it, and return a fresh pair.
    Raises TokenError on any problem.
    """
    payload = decode_refresh_token(refresh_token)
    jti = payload["jti"]
    admin_id = payload["admin_id"]

    stored = redis_client.get(_redis_key(jti))
    if not stored:
        # Token already used or revoked — potential theft, reject hard.
        raise TokenError("Refresh token is invalid or has already been used")

    # Invalidate the old token immediately (rotation).
    redis_client.delete(_redis_key(jti))

    admin = db.get(Admin, admin_id)
    if not admin or not admin.is_active:
        raise TokenError("Account not found or is disabled")

    new_access = create_access_token(
        admin_id=admin.id,
        user_id=admin.user_id,
        username=admin.username,
        user_type="admin",
    )
    new_refresh, new_jti = create_refresh_token(admin_id=admin.id)
    _store_refresh(new_jti, admin)

    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer",
        "expires_in": 30 * 60,
    }


def revoke_refresh_token(refresh_token: str) -> None:
    """
    Logout — delete the JTI from Redis so the token is immediately dead.
    Fails silently if the token is already gone (idempotent logout).
    """
    try:
        payload = decode_refresh_token(refresh_token)
        redis_client.delete(_redis_key(payload["jti"]))
    except TokenError:
        pass  # already expired or invalid — nothing to revoke
