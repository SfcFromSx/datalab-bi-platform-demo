from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class AgentQueryRequest(BaseModel):
    query: str
    notebook_id: str
    cell_id: Optional[str] = None
    datasource_id: Optional[str] = None


class AgentQueryResponse(BaseModel):
    task_id: str
    status: str  # "processing" | "completed" | "error"
    message: str = ""
    cells_created: list[dict] = []
    cells_modified: list[dict] = []
    data: Optional[dict] = None
    chart: Optional[dict] = None
    sections: list[dict] = []


class AgentProgressMessage(BaseModel):
    task_id: str
    status: str
    agent: str = ""
    message: str = ""
    progress: float = 0.0  # 0.0 to 1.0
    data: Optional[dict] = None
    chart: Optional[dict] = None
    sections: list[dict] = []
