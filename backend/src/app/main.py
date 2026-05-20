from fastapi import FastAPI
from app.infrastructure.config import settings
from app.infrastructure.logging import setup_logging
from app.api.webhooks.whatsapp import router as wa_router

setup_logging()
app = FastAPI(title="AI Profit Assistant", version="0.0.1")
app.include_router(wa_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env}
