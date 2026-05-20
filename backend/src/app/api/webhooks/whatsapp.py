import hashlib
import hmac
import structlog
from fastapi import APIRouter, HTTPException, Query, Request, Response  # add Query
from app.infrastructure.config import settings
from uuid import UUID
from app.adapters.db.session import session_scope
from app.adapters.db.models import Shop, WhatsAppMessage
from app.core.repair.voice_intake import ingest_voice_note
from sqlalchemy import select



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

    async with session_scope() as session:
        # Look up the shop by owner phone
        result = await session.execute(
            select(Shop).where(Shop.owner_phone == from_phone, Shop.is_active == True)
        )
        shop = result.scalar_one_or_none()

        # Persist the inbound message
        session.add(WhatsAppMessage(
            shop_id=shop.id if shop else None,
            wa_message_id=wa_msg_id,
            direction="inbound",
            message_type=msg_type,
            from_phone=from_phone,
            body=msg.get("text", {}).get("body") if msg_type == "text" else None,
            raw_payload=msg,
            status="received",
        ))

        if not shop:
            log.warning("unknown_sender", from_phone=from_phone)
            return

        if msg_type == "audio":
            media_id = msg.get("audio", {}).get("id")
            await ingest_voice_note(session, shop.id, media_id, from_phone)
        elif msg_type == "text":
            text = msg.get("text", {}).get("body", "")
            log.info("text_message_received", text=text)
        else:
            log.info("unhandled_message_type", msg_type=msg_type)
