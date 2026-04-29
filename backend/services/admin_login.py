from sqlalchemy.orm import Session

from models.admins import Admin
from core.security import verify_password
import hashlib


class AdminNotFoundError(Exception):
    pass


class InvalidPasswordError(Exception):
    pass


def login_admin(db: Session, username: str, password: str) -> Admin:
    admin = db.query(Admin).filter(Admin.username == username.strip().lower()).first()

    # Deliberately same error for missing user and wrong password to avoid
    # leaking whether a username exists (user enumeration attack).
    if not admin:
        raise InvalidPasswordError("Invalid username or password")

    # Mirror the SHA-256 pre-hash applied during registration.
    pre_hashed = hashlib.sha256(password.encode()).hexdigest()
    if not verify_password(pre_hashed, admin.password_hash):
        raise InvalidPasswordError("Invalid username or password")

    if not admin.is_active:
        raise InvalidPasswordError("Account is disabled")

    return admin
