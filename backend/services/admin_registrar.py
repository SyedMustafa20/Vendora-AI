import argparse
import getpass
import sys
import hashlib

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv
import os

from models.users import User
from models.admins import Admin
from core.security import pwd_context
from services.agent_service import create_default_agent


class AdminAlreadyExistsError(Exception):
    pass

load_dotenv()

# 🔐 Safe password hashing (fixes bcrypt 72-byte issue)
def secure_hash_password(password: str) -> str:
    password = password.strip()

    # Pre-hash to avoid bcrypt 72-byte limit
    password = hashlib.sha256(password.encode()).hexdigest()

    return pwd_context.hash(password)


def register_admin(db: Session, username: str, password: str) -> Admin:
    """
    Creates:
    - User (user_type='admin')
    - Admin (credentials)

    Fully atomic transaction.
    """

    username = username.strip().lower()

    # 🔍 Check existing username
    if db.query(Admin).filter(Admin.username == username).first():
        raise AdminAlreadyExistsError(f"username '{username}' is taken")

    try:
        # 👤 Create base user
        user = User(user_type="admin", phone="+14155238886")
        db.add(user)
        db.flush()  # get user.id

        # 🔑 Create admin credentials
        admin = Admin(
            user_id=user.id,
            username=username,
            password_hash=secure_hash_password(password),
        )
        db.add(admin)
        db.flush()  # get admin.id

        # 🤖 Create default agent config for this admin
        create_default_agent(db, admin.id)

        db.commit()

    except IntegrityError as exc:
        db.rollback()
        raise AdminAlreadyExistsError(str(exc.orig)) from exc

    except Exception:
        db.rollback()
        raise

    db.refresh(admin)
    return admin


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

MIN_USERNAME_LEN = 3
MIN_PASSWORD_LEN = 8


def _prompt_username(provided: str | None) -> str:
    if provided:
        return provided.strip().lower()

    while True:
        value = input("Username: ").strip().lower()
        if len(value) >= MIN_USERNAME_LEN:
            return value
        print(f"  username must be at least {MIN_USERNAME_LEN} characters")


def _prompt_password(provided: str | None) -> str:
    if provided:
        return provided

    while True:
        first = getpass.getpass("Password: ")

        if len(first) < MIN_PASSWORD_LEN:
            print(f"  password must be at least {MIN_PASSWORD_LEN} characters")
            continue

        second = getpass.getpass("Confirm password: ")

        if first != second:
            print("  passwords do not match, try again")
            continue

        return first


def _cli() -> int:
    parser = argparse.ArgumentParser(
        description="Register a new admin user"
    )
    parser.add_argument("--username", "-u")
    parser.add_argument("--password", "-p")

    args = parser.parse_args()

    from db.database import SessionLocal

    username = _prompt_username(args.username)
    password = _prompt_password(args.password)

    db = SessionLocal()

    try:
        admin = register_admin(db, username, password)

    except AdminAlreadyExistsError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    except Exception as exc:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 2

    finally:
        db.close()

    print(
        f"✅ Admin registered: id={admin.id}, "
        f"user_id={admin.user_id}, username={admin.username}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())