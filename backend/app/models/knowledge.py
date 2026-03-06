from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class KnowledgeNodeType(str, PyEnum):
    DATABASE = "database"
    TABLE = "table"
    COLUMN = "column"
    VALUE = "value"
    JARGON = "jargon"
    ALIAS = "alias"


class KnowledgeNode(Base):
    __tablename__ = "knowledge_nodes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    node_type: Mapped[KnowledgeNodeType] = mapped_column(Enum(KnowledgeNodeType))
    name: Mapped[str] = mapped_column(String(256))
    parent_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("knowledge_nodes.id", ondelete="SET NULL"), nullable=True
    )
    components: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    embedding_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    datasource_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("datasources.id", ondelete="SET NULL"), nullable=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    parent: Mapped[KnowledgeNode | None] = relationship(
        "KnowledgeNode", remote_side=[id], backref="children"
    )
    workspace = relationship("Workspace", back_populates="knowledge_nodes")

    def __repr__(self) -> str:
        return f"<KnowledgeNode {self.id[:8]} {self.node_type.value}:'{self.name}'>"
