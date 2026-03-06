from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.knowledge import KnowledgeNodeType


class KnowledgeNodeCreate(BaseModel):
    node_type: KnowledgeNodeType
    name: str
    parent_id: Optional[str] = None
    components: Optional[dict] = None
    datasource_id: Optional[str] = None


class KnowledgeNodeResponse(BaseModel):
    id: str
    workspace_id: str
    node_type: str
    name: str
    parent_id: Optional[str] = None
    components: Optional[dict] = None
    datasource_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    children: list[KnowledgeNodeResponse] = []

    model_config = {"from_attributes": True}


class KnowledgeSearchRequest(BaseModel):
    query: str
    datasource_id: Optional[str] = None
    top_k: int = 10


class KnowledgeSearchResponse(BaseModel):
    nodes: list[KnowledgeNodeResponse]
    scores: list[float] = []


class KnowledgeGenerateRequest(BaseModel):
    datasource_id: str
    scripts: list[str] = []
    score_threshold: float = 3.0
