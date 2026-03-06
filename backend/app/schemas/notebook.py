from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class NotebookCreate(BaseModel):
    title: str = "Untitled Notebook"
    description: str = ""
    folder_id: Optional[str] = None


class NotebookUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    folder_id: Optional[str] = None


class CellResponse(BaseModel):
    id: str
    notebook_id: str
    cell_type: str
    source: str
    output: Optional[dict] = None
    position: int
    metadata: Optional[dict] = Field(None, alias="metadata_")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class NotebookResponse(BaseModel):
    id: str
    title: str
    description: str
    folder_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    cells: list[CellResponse] = []

    model_config = {"from_attributes": True}


class NotebookListResponse(BaseModel):
    id: str
    title: str
    description: str
    folder_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    cell_count: int = 0

    model_config = {"from_attributes": True}
