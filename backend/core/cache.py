import json
import os
from typing import Any, Optional

import redis
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# decode_responses=True so we get str instead of bytes
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

DEFAULT_TTL = int(os.getenv("CACHE_DEFAULT_TTL", "3600"))


def cache_get(key: str) -> Optional[Any]:
    raw = redis_client.get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return raw


def cache_set(key: str, value: Any, ttl: int = DEFAULT_TTL) -> None:
    payload = value if isinstance(value, str) else json.dumps(value, default=str)
    redis_client.set(key, payload, ex=ttl)


def cache_delete(*keys: str) -> None:
    if keys:
        redis_client.delete(*keys)


# ---- key builders (single source of truth, avoids typos across modules) ----

def user_key(phone: str) -> str:
    return f"user:phone:{phone}"


def conversation_key(user_id: int) -> str:
    return f"conversation:user:{user_id}"


def summary_key(conversation_id: int) -> str:
    return f"conversation:summary:{conversation_id}"


def processing_lock_key(phone: str) -> str:
    return f"lock:processing:{phone}"
