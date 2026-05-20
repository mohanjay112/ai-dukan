import httpx
import structlog
from app.infrastructure.config import settings

log = structlog.get_logger()

META_BASE = "https://graph.facebook.com/v22.0"


async def get_media_url(media_id: str) -> str:
    """Ask Meta for the temporary download URL of a media file."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{META_BASE}/{media_id}",
            headers={"Authorization": f"Bearer {settings.meta_access_token}"},
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
        log.info("meta_media_url_fetched", media_id=media_id, url=data.get("url"))
        return data["url"]


async def download_media(url: str) -> bytes:
    """Download the actual audio bytes from Meta's CDN."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            url,
            headers={"Authorization": f"Bearer {settings.meta_access_token}"},
            timeout=30.0,
            follow_redirects=True,
        )
        resp.raise_for_status()
        return resp.content


async def fetch_voice_note_bytes(media_id: str) -> bytes:
    """One-shot: media_id → raw audio bytes."""
    url = await get_media_url(media_id)
    return await download_media(url)
