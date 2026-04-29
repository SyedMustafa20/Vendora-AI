"""
Run from backend/ with:  venv\\Scripts\\python smoke_test.py
Tests each component in the pipeline and prints PASS / FAIL clearly.
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
WARN = "\033[93mWARN\033[0m"

results = []


def check(name, fn):
    try:
        fn()
        print(f"  [{PASS}] {name}")
        results.append((name, True))
    except Exception as exc:
        print(f"  [{FAIL}] {name}")
        print(f"          {exc}")
        results.append((name, False))


# -- 1. ENV VARS --------------------------------------------------------------?
print("\n-- 1. Environment variables -----------------------------")

def check_env():
    required = [
        "DATABASE_URL",
        "REDIS_URL",
        "OPENROUTER_API_KEY",
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "TWILIO_WHATSAPP_FROM",
    ]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise EnvironmentError(f"Missing env vars: {missing}")

    key = os.getenv("OPENROUTER_API_KEY", "")
    if " " in key:
        raise ValueError(
            "OPENROUTER_API_KEY contains a space ? copy it again from openrouter.ai"
        )

check("All required env vars present and no spaces in API key", check_env)


# -- 2. DATABASE --------------------------------------------------------------?
print("\n-- 2. Database ------------------------------------------")

def check_db():
    from db.database import SessionLocal
    db = SessionLocal()
    try:
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
    finally:
        db.close()

check("PostgreSQL connection", check_db)

def check_tables():
    from db.database import SessionLocal
    import sqlalchemy as sa
    db = SessionLocal()
    try:
        inspector = sa.inspect(db.get_bind())
        tables = inspector.get_table_names()
        for t in ["users", "admins", "conversations", "messages"]:
            if t not in tables:
                raise RuntimeError(f"Table '{t}' not found ? run: python create_db.py")
    finally:
        db.close()

check("Required tables exist", check_tables)


# -- 3. REDIS ------------------------------------------------------------------
print("\n-- 3. Redis ---------------------------------------------")

def check_redis():
    import redis
    r = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    r.ping()

check("Redis ping", check_redis)


# -- 4. CELERY ----------------------------------------------------------------?
print("\n-- 4. Celery worker -------------------------------------")

def check_celery():
    from core.celery_app import celery_app
    i = celery_app.control.inspect(timeout=3)
    active = i.active()
    if not active:
        raise RuntimeError(
            "No Celery workers found ? start one with:\n"
            "          venv\\Scripts\\celery -A core.celery_app.celery_app worker "
            "--loglevel=info --pool=solo"
        )

check("At least one Celery worker online", check_celery)


# -- 5. OPENROUTER ------------------------------------------------------------?
print("\n-- 5. OpenRouter (AI) -----------------------------------")

def check_openrouter():
    """
    1. Verify that the API key authenticates (presence of user_id in any error proves this).
    2. Attempt a real completion — downgrade to WARN if all free models are throttled.
    """
    import json
    from openai import OpenAI, RateLimitError, NotFoundError, BadRequestError, APIStatusError
    key = os.getenv("OPENROUTER_API_KEY", "")
    client = OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1")

    # First, prove auth works by making any call and checking for user_id.
    AUTH_SENTINEL = object()
    auth_ok = AUTH_SENTINEL
    models_to_try = [
        os.getenv("OPENROUTER_CHAT_MODEL", "meta-llama/llama-3.3-70b-instruct:free"),
        "google/gemma-3-27b-it:free",
        "meta-llama/llama-3.2-3b-instruct:free",
        "mistralai/mistral-7b-instruct:free",
    ]
    throttled = []
    for model in models_to_try:
        try:
            res = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Reply with just the word OK"}],
                max_tokens=5,
            )
            content = res.choices[0].message.content or ""
            print(f"          Model: {model} | Reply: {repr(content)}")
            return  # full success
        except (RateLimitError, NotFoundError, BadRequestError) as exc:
            body = getattr(exc, "response", None)
            raw = body.text if body else str(exc)
            if "user_id" in raw:
                auth_ok = True  # credentials are valid, provider just busy
            throttled.append(f"{model}: {exc.status_code}")
            print(f"          [{WARN}] {model} unavailable ({exc.status_code}), trying next...")
        except APIStatusError as exc:
            if "user_id" in str(exc):
                auth_ok = True
            print(f"          [{WARN}] {model} error {exc.status_code}, trying next...")

    if auth_ok is True:
        print(f"          [{WARN}] All free models are currently throttled by providers.")
        print(f"          [{WARN}] Your API key IS valid. Try again in a few minutes.")
        print(f"          [{WARN}] Skipped models: {throttled}")
        # Don't raise — credentials work, this is a capacity issue not a code bug.
        return
    raise RuntimeError(
        "OpenRouter auth failed — check OPENROUTER_API_KEY in your .env"
    )

check("OpenRouter credentials + model availability", check_openrouter)


# -- 6. TWILIO ----------------------------------------------------------------?
print("\n-- 6. Twilio --------------------------------------------")

def check_twilio_creds():
    from twilio.rest import Client
    c = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
    acc = c.api.accounts(os.getenv("TWILIO_ACCOUNT_SID")).fetch()
    if acc.status != "active":
        raise RuntimeError(f"Twilio account status: {acc.status}")

check("Twilio credentials & account active", check_twilio_creds)

def check_twilio_from():
    val = os.getenv("TWILIO_WHATSAPP_FROM", "")
    if not val.startswith("whatsapp:"):
        raise ValueError(
            f"TWILIO_WHATSAPP_FROM must start with 'whatsapp:' ? got: {val!r}"
        )

check("TWILIO_WHATSAPP_FROM format", check_twilio_from)


# -- SUMMARY ------------------------------------------------------------------?
print("\n-- Summary ----------------------------------------------")
passed = sum(1 for _, ok in results if ok)
total = len(results)
print(f"  {passed}/{total} checks passed")
if passed < total:
    print(f"\n  Fix the FAIL items above, then re-run this script.")
    sys.exit(1)
else:
    print("\n  All checks passed ? the pipeline should be working.")
print()
