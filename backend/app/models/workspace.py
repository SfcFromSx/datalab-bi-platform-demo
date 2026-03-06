from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class WorkspaceStatus(str, PyEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(256))
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[WorkspaceStatus] = mapped_column(
        Enum(WorkspaceStatus), default=WorkspaceStatus.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    memberships = relationship(
        "WorkspaceMembership",
        back_populates="workspace",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    folders = relationship("Folder", back_populates="workspace", lazy="selectin")
    notebooks = relationship("Notebook", back_populates="workspace", lazy="selectin")
    cells = relationship("Cell", back_populates="workspace", lazy="selectin")
    datasources = relationship("DataSource", back_populates="workspace", lazy="selectin")
    knowledge_nodes = relationship("KnowledgeNode", back_populates="workspace", lazy="selectin")
    audit_events = relationship("AuditEvent", back_populates="workspace", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Workspace {self.slug}>"
