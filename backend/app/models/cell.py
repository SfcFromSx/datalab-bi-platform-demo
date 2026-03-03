from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CellType(str, PyEnum):
    SQL = "sql"
    PYTHON = "python"
    CHART = "chart"
    MARKDOWN = "markdown"


class Cell(Base):
    __tablename__ = "cells"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    notebook_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("notebooks.id", ondelete="CASCADE")
    )
    cell_type: Mapped[CellType] = mapped_column(Enum(CellType), default=CellType.PYTHON)
    source: Mapped[str] = mapped_column(Text, default="")
    output: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    notebook: Mapped["Notebook"] = relationship("Notebook", back_populates="cells")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Cell {self.id[:8]} type={self.cell_type.value}>"
