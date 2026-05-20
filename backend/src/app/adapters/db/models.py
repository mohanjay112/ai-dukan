from __future__ import annotations
from uuid import UUID, uuid4
from sqlalchemy import String, Text, BigInteger, ForeignKey, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.adapters.db.base import Base, TimestampMixin


class Shop(Base, TimestampMixin):
    __tablename__ = "shops"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    owner_phone: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    wa_phone_number_id: Mapped[str | None] = mapped_column(String(50))
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Kolkata")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    settings: Mapped[dict] = mapped_column(JSON, default=dict)

    voice_notes: Mapped[list[VoiceNote]] = relationship(back_populates="shop")
    whatsapp_messages: Mapped[list[WhatsAppMessage]] = relationship(back_populates="shop")


class VoiceNote(Base, TimestampMixin):
    __tablename__ = "voice_notes"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(ForeignKey("shops.id"), nullable=False, index=True)
    wa_media_id: Mapped[str | None] = mapped_column(String(200))   # Meta's media ID
    r2_key: Mapped[str | None] = mapped_column(String(500))        # Cloudflare R2 path
    duration_seconds: Mapped[int | None] = mapped_column()
    transcript_raw: Mapped[str | None] = mapped_column(Text)
    transcript_language: Mapped[str | None] = mapped_column(String(10))
    asr_provider: Mapped[str | None] = mapped_column(String(30))   # sarvam | groq
    processing_status: Mapped[str] = mapped_column(String(30), default="pending")
    # pending → transcribing → done → failed

    shop: Mapped[Shop] = relationship(back_populates="voice_notes")
    ai_interactions: Mapped[list[AIInteraction]] = relationship(back_populates="voice_note")


class WhatsAppMessage(Base, TimestampMixin):
    __tablename__ = "whatsapp_messages"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(ForeignKey("shops.id"), nullable=False, index=True)
    wa_message_id: Mapped[str | None] = mapped_column(String(200), unique=True)
    direction: Mapped[str] = mapped_column(String(10))     # inbound | outbound
    message_type: Mapped[str] = mapped_column(String(20))  # text | audio | template
    from_phone: Mapped[str | None] = mapped_column(String(20))
    to_phone: Mapped[str | None] = mapped_column(String(20))
    body: Mapped[str | None] = mapped_column(Text)
    template_name: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="received")
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)

    shop: Mapped[Shop] = relationship(back_populates="whatsapp_messages")


class AIInteraction(Base, TimestampMixin):
    __tablename__ = "ai_interactions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(ForeignKey("shops.id"), nullable=False, index=True)
    voice_note_id: Mapped[UUID | None] = mapped_column(ForeignKey("voice_notes.id"))
    provider: Mapped[str] = mapped_column(String(30))       # anthropic | groq | sarvam
    model: Mapped[str] = mapped_column(String(60))
    intent: Mapped[str | None] = mapped_column(String(50))  # repair_intake | unknown | …
    prompt_tokens: Mapped[int] = mapped_column(default=0)
    completion_tokens: Mapped[int] = mapped_column(default=0)
    cost_p: Mapped[int] = mapped_column(BigInteger, default=0)  # paise (1/100 rupee)
    latency_ms: Mapped[int | None] = mapped_column()
    success: Mapped[bool] = mapped_column(default=True)

    voice_note: Mapped[VoiceNote | None] = relationship(back_populates="ai_interactions")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(ForeignKey("shops.id"), nullable=False, index=True)
    actor_type: Mapped[str] = mapped_column(String(20))     # owner | system | customer
    action: Mapped[str] = mapped_column(String(60))         # ticket.created, status.updated…
    entity_type: Mapped[str | None] = mapped_column(String(50))
    entity_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    before: Mapped[dict | None] = mapped_column(JSON)
    after: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(
        __import__("sqlalchemy").DateTime(timezone=True),
        server_default=__import__("sqlalchemy").sql.func.now(), nullable=False
    )
