"""LLM call log model – records every LLM request for debugging & optimisation."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class LLMLog(Base):
    __tablename__ = "llm_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    feature: Mapped[str] = mapped_column(String(40), default="unknown")
    model: Mapped[str] = mapped_column(String(120), default="")
    messages: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)
    response: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    tokens_prompt: Mapped[int] = mapped_column(Integer, default=0)
    tokens_completion: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="success")
    error: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    cell_id: Mapped[str | None] = mapped_column(String(36), nullable=True, default=None)
    notebook_id: Mapped[str | None] = mapped_column(String(36), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    def __repr__(self) -> str:
        return f"<LLMLog {self.id[:8]} feature={self.feature} status={self.status}>"
