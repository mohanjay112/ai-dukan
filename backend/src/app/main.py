from fastapi import FastAPI
from app.infrastructure.config import settings
from app.infrastructure.logging import setup_logging

setup_logging()
app = FastAPI(title="AI Profit Assistant", version="0.0.1")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env}