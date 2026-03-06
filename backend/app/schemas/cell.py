from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from app.models.cell import CellType


class CellCreate(BaseModel):
    cell_type: CellType = CellType.PYTHON
    source: str = ""
    position: Optional[int] = None
    metadata: Optional[dict] = None


class CellUpdate(BaseModel):
    source: Optional[str] = None
    metadata: Optional[dict] = None


class CellMoveRequest(BaseModel):
    position: int


class CellExecuteRequest(BaseModel):
    source: Optional[str] = None  # override source for execution


class CellExecuteResponse(BaseModel):
    cell_id: str
    status: str  # "success" | "error"
    output: dict
    executed_cells: list[dict] = []
