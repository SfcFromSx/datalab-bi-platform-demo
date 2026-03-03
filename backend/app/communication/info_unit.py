"""Structured Information Unit for inter-agent communication.

Each information unit comprises six fields:
- data_source: Dataset identifier
- role: Agent identity
- action: Behavior performed
- description: Action summary
- content: Agent output
- timestamp: Completion time
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class InformationUnit:
    """Structured information format for inter-agent communication.

    Replaces unstructured natural language with a standardized 6-field structure
    to reduce ambiguity and improve communication efficiency.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    data_source: str = ""
    role: str = ""
    action: str = ""
    description: str = ""
    content: Any = None
    timestamp: float = field(default_factory=time.time)
    cell_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "data_source": self.data_source,
            "role": self.role,
            "action": self.action,
            "description": self.description,
            "content": self.content if not callable(self.content) else str(self.content),
            "timestamp": self.timestamp,
            "cell_id": self.cell_id,
        }

    def to_context_string(self) -> str:
        """Format the info unit as a concise context string for LLM prompts."""
        parts = [
            f"[{self.role}] {self.action}",
            f"Description: {self.description}",
        ]
        if self.data_source:
            parts.append(f"Data Source: {self.data_source}")

        content_str = str(self.content) if self.content else ""
        if len(content_str) > 500:
            content_str = content_str[:500] + "..."
        if content_str:
            parts.append(f"Content: {content_str}")

        return "\n".join(parts)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InformationUnit:
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            data_source=data.get("data_source", ""),
            role=data.get("role", ""),
            action=data.get("action", ""),
            description=data.get("description", ""),
            content=data.get("content"),
            timestamp=data.get("timestamp", time.time()),
            cell_id=data.get("cell_id"),
        )
