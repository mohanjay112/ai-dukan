from uuid import uuid4, UUID
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from app.adapters.db.models import VoiceNote, Shop
from app.adapters.storage.r2 import upload_bytes
from app.adapters.whatsapp.media import fetch_voice_note_bytes
from sqlalchemy import select

log = structlog.get_logger()


async def ingest_voice_note(
    session: AsyncSession,
    shop_id: UUID,
    wa_media_id: str,
    from_phone: str,
) -> VoiceNote:
    """
    Download voice note from Meta, upload to R2, persist VoiceNote row.
    Returns the saved VoiceNote (status = 'transcribing' queued).
    """
    log.info("voice_note_ingesting", shop_id=str(shop_id), media_id=wa_media_id)

    # 1. Download from Meta
    audio_bytes = await fetch_voice_note_bytes(wa_media_id)
    log.info("voice_note_downloaded", bytes=len(audio_bytes))

    # 2. Upload to R2
    r2_key = f"shops/{shop_id}/voice/{uuid4()}.ogg"
    upload_bytes(r2_key, audio_bytes, content_type="audio/ogg")
    log.info("voice_note_uploaded_r2", key=r2_key)

    # 3. Persist VoiceNote row
    vn = VoiceNote(
        id=uuid4(),
        shop_id=shop_id,
        wa_media_id=wa_media_id,
        r2_key=r2_key,
        processing_status="uploaded",
    )
    session.add(vn)
    await session.flush()  # get the ID without committing yet

    log.info("voice_note_persisted", voice_note_id=str(vn.id))
    return vn
