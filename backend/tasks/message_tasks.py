import os
import logging

from dotenv import load_dotenv
from twilio.rest import Client as TwilioClient

from core.celery_app import celery_app
from core.cache import redis_client, processing_lock_key
from db.database import SessionLocal
from services.ai_service import handle_message

load_dotenv()
logger = logging.getLogger(__name__)

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM = os.getenv("TWILIO_WHATSAPP_FROM")  # e.g. "whatsapp:+14155238886"

PROCESSING_LOCK_TTL = 60  # seconds; one in-flight task per phone

FALLBACK_REPLY = (
    "Sorry, I'm having trouble right now. Please try again in a moment."
)


def _twilio_send(to: str, body: str) -> None:
    if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN):
        raise RuntimeError("Twilio credentials not configured in environment")
    if not TWILIO_FROM:
        raise RuntimeError("TWILIO_WHATSAPP_FROM not configured in environment")
    client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    client.messages.create(from_=TWILIO_FROM, to=to, body=body)
    logger.info("Sent reply to %s", to)


# Do NOT auto-retry on every Exception — AI timeouts should not spam the user.
# Only retry on connection/infra errors, not on application errors.
@celery_app.task(
    name="tasks.process_whatsapp_message",
    bind=True,
    max_retries=2,
    default_retry_delay=5,
)
def process_whatsapp_message(self, sender_phone: str, user_message: str) -> str:
    """
    Heavy path: DB writes, intent detection, summary update, AI generation,
    and the outbound Twilio send. Runs in a Celery worker so the webhook
    returns inside Twilio's 15s window.
    """
    lock_key = processing_lock_key(sender_phone)
    if not redis_client.set(lock_key, "1", nx=True, ex=PROCESSING_LOCK_TTL):
        logger.info("Dropping duplicate task for %s — already in-flight", sender_phone)
        return "skipped:in-flight"

    reply = FALLBACK_REPLY
    db = SessionLocal()
    try:
        reply = handle_message(db, sender_phone, user_message)
        logger.info("Generated reply for %s: %s", sender_phone, reply[:80])
    except Exception as exc:
        logger.exception("handle_message failed for %s: %s", sender_phone, exc)
        # reply stays as FALLBACK_REPLY — user gets a message instead of silence
    finally:
        db.close()
        redis_client.delete(lock_key)

    try:
        _twilio_send(sender_phone, reply)
    except Exception as exc:
        logger.exception("Twilio send failed for %s: %s", sender_phone, exc)
        # Retry the whole task so we attempt to deliver the reply again.
        raise self.retry(exc=exc)

    return reply
