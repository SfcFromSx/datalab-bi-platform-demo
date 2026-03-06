from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class FolderCreate(BaseModel):
    name: str = "New Folder"


class FolderUpdate(BaseModel):
    name: Optional[str] = None
    position: Optional[int] = None


class FolderResponse(BaseModel):
    id: str
    name: str
    position: int
    created_at: datetime

    model_config = {"from_attributes": True}
