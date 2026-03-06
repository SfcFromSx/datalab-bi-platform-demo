from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Notebook(Base):
    __tablename__ = "notebooks"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(256), default="Untitled Notebook")
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )
    folder_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("folders.id"), nullable=True, default=None
    )

    workspace = relationship("Workspace", back_populates="notebooks")
    folder = relationship("Folder", back_populates="notebooks")

    cells: Mapped[list["Cell"]] = relationship(  # noqa: F821
        "Cell",
        back_populates="notebook",
        cascade="all, delete-orphan",
        order_by="Cell.position",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Notebook {self.id[:8]} '{self.title}'>"
