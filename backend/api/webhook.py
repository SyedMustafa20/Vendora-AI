from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
from twilio.twiml.messaging_response import MessagingResponse

from tasks.message_tasks import process_whatsapp_message

router = APIRouter()


@router.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    """
    Twilio webhook. Pushes work to Celery and returns an empty TwiML
    immediately so we always answer inside Twilio's 15s timeout. The reply
    is sent back to the user from the worker via Twilio's REST API.
    """
    form = await request.form()
    sender = form.get("From")
    message = form.get("Body")

    if not sender or not message:
        return PlainTextResponse("Missing data", status_code=400)

    process_whatsapp_message.delay(sender, message)

    response = MessagingResponse()
    return PlainTextResponse(str(response), media_type="application/xml")
