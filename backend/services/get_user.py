from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from models.users import User
from core.cache import cache_get, cache_set, cache_delete, user_key

USER_CACHE_TTL = 3600


def _serialize(user: User) -> dict:
    return {
        "id": user.id,
        "phone": user.phone,
        "user_type": user.user_type,
        "is_active": user.is_active,
    }


def get_or_create_user(db: Session, phone: str) -> User:
    """
    Fetch user by phone. Cached in Redis (id + phone + type).
    On cache hit we still hydrate the ORM object via primary-key load, so
    callers get a session-attached instance and we don't trust stale data.
    """
    key = user_key(phone)
    cached = cache_get(key)
    if cached and cached.get("id"):
        user = db.get(User, cached["id"])
        if user:
            return user
        # cache referred to a deleted row — fall through and rebuild
        cache_delete(key)

    user = db.query(User).filter(User.phone == phone).first()
    if user:
        cache_set(key, _serialize(user), ttl=USER_CACHE_TTL)
        return user

    user = User(phone=phone)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # Race: another worker inserted the same phone between query and commit.
        db.rollback()
        user = db.query(User).filter(User.phone == phone).first()
    db.refresh(user)
    cache_set(key, _serialize(user), ttl=USER_CACHE_TTL)
    return user


def invalidate_user_cache(phone: str) -> None:
    cache_delete(user_key(phone))
