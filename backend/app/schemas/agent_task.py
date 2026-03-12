from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class AgentTaskCreate(BaseModel):
    query: str
    notebook_id: Optional[str] = None
    datasource_id: Optional[str] = None


class AgentTaskPlanStep(BaseModel):
    index: int
    description: str
    status: str = "pending"
    cell_id: Optional[str] = None


class AgentTaskResponse(BaseModel):
    id: str
    notebook_id: Optional[str]
    datasource_id: Optional[str]
    query: str
    status: str
    plan: Optional[list[AgentTaskPlanStep]]
    progress: float
    result: Optional[dict[str, Any]]
    error: Optional[str]
    tokens_used: int
    queries_executed: int
    cells_created: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentTaskListResponse(BaseModel):
    tasks: list[AgentTaskResponse]
    total: int
