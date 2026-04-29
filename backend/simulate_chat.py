"""
WhatsApp Chat Simulator
=======================
Run from backend/:  venv\\Scripts\\python simulate_chat.py [OPTIONS]

Two modes
---------
  direct   (default) — calls handle_message() in-process.
                        No Celery / Redis needed. Instant responses.
                        Best for testing AI quality.

  webhook  --webhook  — POSTs form data to the running uvicorn server
                        exactly as Twilio would, then polls the DB for
                        the agent reply. Tests the full async pipeline
                        (uvicorn + Celery + Redis must all be running).

Options
-------
  --phone  PHONE   Sender phone to simulate  (default: whatsapp:+923300000000)
  --url    URL     Webhook base URL           (default: http://127.0.0.1:8000)
  --webhook        Use webhook mode instead of direct mode
  --timeout N      Seconds to wait for async reply in webhook mode (default: 30)
"""

import argparse
import sys
import time
from datetime import datetime

# ── colour helpers ────────────────────────────────────────────────────────────
def _c(code, text): return f"\033[{code}m{text}\033[0m"
GREEN  = lambda t: _c("92", t)
CYAN   = lambda t: _c("96", t)
YELLOW = lambda t: _c("93", t)
RED    = lambda t: _c("91", t)
GREY   = lambda t: _c("90", t)
BOLD   = lambda t: _c("1",  t)

SEPARATOR = GREY("─" * 60)


def _ts():
    return GREY(datetime.now().strftime("%H:%M:%S"))


def _print_user(msg):
    print(f"\n  {_ts()}  {BOLD('You')}  {CYAN(msg)}")


def _print_bot(msg):
    print(f"  {_ts()}  {BOLD(GREEN('Bot'))}  {msg}")


def _print_info(msg):
    print(YELLOW(f"  ℹ  {msg}"))


def _print_err(msg):
    print(RED(f"  ✗  {msg}"))


# ── direct mode ───────────────────────────────────────────────────────────────

def run_direct(phone: str):
    from dotenv import load_dotenv
    load_dotenv()

    from db.database import SessionLocal
    from services.ai_service import handle_message

    print(SEPARATOR)
    _print_info(f"Direct mode  |  phone: {phone}")
    _print_info("Calls handle_message() in-process — no Celery/Redis needed.")
    _print_info("Type 'quit' or press Ctrl-C to exit.")
    print(SEPARATOR)

    db = SessionLocal()
    try:
        while True:
            try:
                user_input = input(f"\n  {BOLD('You')} > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n")
                break

            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                break

            _print_user(user_input)
            print(GREY("  … thinking"))

            try:
                reply = handle_message(db, phone, user_input)
                _print_bot(reply)
            except Exception as exc:
                _print_err(f"Pipeline error: {exc}")
    finally:
        db.close()


# ── webhook mode ──────────────────────────────────────────────────────────────

def _latest_agent_reply_after(db, phone: str, since_id: int) -> str | None:
    """Poll for an agent message with id > since_id for this phone's conversation."""
    from models.users import User
    from models.conversation import Conversation
    from models.message import Message

    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        return None
    conv = (db.query(Conversation)
              .filter(Conversation.user_id == user.id)
              .first())
    if not conv:
        return None
    msg = (db.query(Message)
             .filter(
                 Message.conversation_id == conv.id,
                 Message.sender_type == "agent",
                 Message.id > since_id,
             )
             .order_by(Message.id.desc())
             .first())
    return msg.content if msg else None


def _last_message_id(db, phone: str) -> int:
    """Return the highest message id currently in the DB for this phone."""
    from models.users import User
    from models.conversation import Conversation
    from models.message import Message

    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        return 0
    conv = (db.query(Conversation)
              .filter(Conversation.user_id == user.id)
              .first())
    if not conv:
        return 0
    msg = (db.query(Message)
             .filter(Message.conversation_id == conv.id)
             .order_by(Message.id.desc())
             .first())
    return msg.id if msg else 0


def run_webhook(phone: str, base_url: str, timeout: int):
    import requests
    from dotenv import load_dotenv
    load_dotenv()
    from db.database import SessionLocal

    webhook_url = f"{base_url.rstrip('/')}/webhook/whatsapp"

    print(SEPARATOR)
    _print_info(f"Webhook mode  |  phone: {phone}")
    _print_info(f"POSTing to:   {webhook_url}")
    _print_info(f"Reply timeout: {timeout}s  (uvicorn + Celery + Redis must be running)")
    _print_info("Type 'quit' or press Ctrl-C to exit.")
    print(SEPARATOR)

    # Verify the server is reachable before entering the loop.
    try:
        requests.get(base_url, timeout=3)
    except Exception:
        _print_err(f"Cannot reach {base_url} — is uvicorn running?")
        sys.exit(1)

    db = SessionLocal()
    try:
        while True:
            try:
                user_input = input(f"\n  {BOLD('You')} > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n")
                break

            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                break

            _print_user(user_input)

            # Snapshot highest message id before sending so we can detect the new reply.
            before_id = _last_message_id(db, phone)

            # POST exactly as Twilio would.
            try:
                resp = requests.post(
                    webhook_url,
                    data={"From": phone, "Body": user_input},
                    timeout=10,
                )
                if resp.status_code != 200:
                    _print_err(f"Webhook returned {resp.status_code}: {resp.text}")
                    continue
            except Exception as exc:
                _print_err(f"Request failed: {exc}")
                continue

            # Poll DB for the Celery worker's reply.
            print(GREY(f"  … waiting for worker reply (max {timeout}s)"))
            deadline = time.time() + timeout
            reply = None
            while time.time() < deadline:
                db.expire_all()  # force re-query
                reply = _latest_agent_reply_after(db, phone, before_id)
                if reply:
                    break
                time.sleep(0.8)

            if reply:
                _print_bot(reply)
            else:
                _print_err(
                    f"No reply received within {timeout}s. "
                    "Check Celery worker logs for errors."
                )
    finally:
        db.close()


# ── entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Simulate WhatsApp messages through the bot pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--phone", default="whatsapp:+923305926891",
        help="Sender phone number (default: whatsapp:+923305926891)",
    )
    parser.add_argument(
        "--webhook", action="store_true",
        help="Use webhook mode (requires uvicorn + Celery + Redis running)",
    )
    parser.add_argument(
        "--url", default="http://127.0.0.1:8000",
        help="Base URL of the running server (webhook mode only)",
    )
    parser.add_argument(
        "--timeout", type=int, default=30,
        help="Seconds to wait for a reply in webhook mode (default: 30)",
    )
    args = parser.parse_args()

    print(f"\n{BOLD('WhatsApp Chat Simulator')}")

    if args.webhook:
        run_webhook(args.phone, args.url, args.timeout)
    else:
        run_direct(args.phone)

    print(GREY("Session ended."))


if __name__ == "__main__":
    main()
