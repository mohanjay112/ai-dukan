import hashlib
import hmac
import structlog
from fastapi import APIRouter, HTTPException, Query, Request, Response  # add Query
from app.infrastructure.config import settings

log = structlog.get_logger()
router = APIRouter()


def _verify_signature(raw_body: bytes, signature_header: str | None) -> bool:
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(
        settings.meta_app_secret.encode(),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    received = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, received)


@router.get("/webhook/whatsapp")
async def verify_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
) -> Response:
    if hub_mode == "subscribe" and hub_verify_token == settings.meta_webhook_verify_token:
        log.info("whatsapp_webhook_verified")
        return Response(content=hub_challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification failed")

@router.post("/webhook/whatsapp")
async def receive_webhook(request: Request) -> dict:
    """All incoming WhatsApp events arrive here."""
    raw_body = await request.body()

    # Signature check — skip in dev if secret is placeholder
    if settings.meta_app_secret != "placeholder-until-meta-ready":
        sig = request.headers.get("X-Hub-Signature-256")
        if not _verify_signature(raw_body, sig):
            log.warning("whatsapp_webhook_bad_signature")
            raise HTTPException(status_code=401, detail="Bad signature")

    payload = await request.json()
    log.info("whatsapp_webhook_received", payload=payload)

    # Walk the payload structure Meta sends
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            messages = value.get("messages", [])
            for msg in messages:
                await _handle_message(msg, value)

    # Meta requires a 200 OK immediately — always return this
    return {"status": "ok"}


async def _handle_message(msg: dict, value: dict) -> None:
    msg_type = msg.get("type")
    from_phone = msg.get("from")
    wa_msg_id = msg.get("id")

    log.info("whatsapp_message_received",
             type=msg_type, from_phone=from_phone, wa_msg_id=wa_msg_id)

    if msg_type == "audio":
        media_id = msg.get("audio", {}).get("id")
        log.info("voice_note_received", media_id=media_id, from_phone=from_phone)
        # TODO Day 5: download audio → R2 → queue transcription
    elif msg_type == "text":
        text = msg.get("text", {}).get("body", "")
        log.info("text_message_received", text=text, from_phone=from_phone)
        # TODO Day 8: handle text commands
    else:
        log.info("unhandled_message_type", msg_type=msg_type)
