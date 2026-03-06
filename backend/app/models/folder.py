from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Folder(Base):
    __tablename__ = "folders"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(256), default="New Folder")
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    workspace = relationship("Workspace", back_populates="folders")

    notebooks: Mapped[list["Notebook"]] = relationship(  # noqa: F821
        "Notebook",
        back_populates="folder",
        order_by="Notebook.updated_at.desc()",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Folder {self.id[:8]} '{self.name}'>"
