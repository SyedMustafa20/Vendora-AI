from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from models.conversation import Conversation
from core.cache import cache_get, cache_set, cache_delete, conversation_key

CONVERSATION_CACHE_TTL = 1800


def _serialize(c: Conversation) -> dict:
    return {"id": c.id, "user_id": c.user_id, "intent": c.intent}


def get_or_create_conversation(db: Session, user_id: int) -> Conversation:
    """
    Each user has one active conversation (simple model).
    Cached so the hot path is a single Redis GET + PK load.
    """
    key = conversation_key(user_id)
    cached = cache_get(key)
    if cached and cached.get("id"):
        conv = db.get(Conversation, cached["id"])
        if conv:
            return conv
        cache_delete(key)

    conv = db.query(Conversation).filter(Conversation.user_id == user_id).first()
    if conv:
        cache_set(key, _serialize(conv), ttl=CONVERSATION_CACHE_TTL)
        return conv

    conv = Conversation(user_id=user_id)
    db.add(conv)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        conv = db.query(Conversation).filter(Conversation.user_id == user_id).first()
    db.refresh(conv)
    cache_set(key, _serialize(conv), ttl=CONVERSATION_CACHE_TTL)
    return conv


def invalidate_conversation_cache(user_id: int) -> None:
    cache_delete(conversation_key(user_id))
