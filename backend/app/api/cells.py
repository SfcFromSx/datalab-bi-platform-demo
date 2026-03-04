"""Cell CRUD and execution API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.execution import execution_sandbox
from app.models import Cell, Notebook
from app.schemas import (
    CellCreate,
    CellExecuteRequest,
    CellExecuteResponse,
    CellMoveRequest,
    CellUpdate,
)
from pydantic import BaseModel

class CellEditRequest(BaseModel):
    prompt: str

from app.schemas.notebook import CellResponse

router = APIRouter(tags=["cells"])


@router.post(
    "/notebooks/{notebook_id}/cells",
    response_model=CellResponse,
    status_code=201,
)
async def create_cell(
    notebook_id: str,
    data: CellCreate,
    session: AsyncSession = Depends(get_session),
):
    nb = await session.get(Notebook, notebook_id)
    if not nb:
        raise HTTPException(status_code=404, detail="Notebook not found")

    if data.position is not None:
        position = data.position
    else:
        result = await session.execute(
            select(func.coalesce(func.max(Cell.position), -1)).where(
                Cell.notebook_id == notebook_id
            )
        )
        max_pos = result.scalar() or -1
        position = max_pos + 1

    cell = Cell(
        notebook_id=notebook_id,
        cell_type=data.cell_type,
        source=data.source,
        position=position,
        metadata_=data.metadata,
    )
    session.add(cell)
    await session.flush()
    await session.refresh(cell)
    return cell


@router.put("/cells/{cell_id}", response_model=CellResponse)
async def update_cell(
    cell_id: str,
    data: CellUpdate,
    session: AsyncSession = Depends(get_session),
):
    cell = await session.get(Cell, cell_id)
    if not cell:
        raise HTTPException(status_code=404, detail="Cell not found")

    if data.source is not None:
        cell.source = data.source
    if data.metadata is not None:
        cell.metadata_ = data.metadata

    await session.flush()
    await session.refresh(cell)
    return cell


@router.delete("/cells/{cell_id}", status_code=204)
async def delete_cell(
    cell_id: str, session: AsyncSession = Depends(get_session)
):
    cell = await session.get(Cell, cell_id)
    if not cell:
        raise HTTPException(status_code=404, detail="Cell not found")
    await session.delete(cell)


@router.put("/cells/{cell_id}/move", response_model=CellResponse)
async def move_cell(
    cell_id: str,
    data: CellMoveRequest,
    session: AsyncSession = Depends(get_session),
):
    cell = await session.get(Cell, cell_id)
    if not cell:
        raise HTTPException(status_code=404, detail="Cell not found")

    cell.position = data.position
    await session.flush()
    await session.refresh(cell)
    return cell


@router.post("/cells/{cell_id}/execute", response_model=CellExecuteResponse)
async def execute_cell(
    cell_id: str,
    data: CellExecuteRequest | None = None,
    session: AsyncSession = Depends(get_session),
):
    cell = await session.get(Cell, cell_id)
    if not cell:
        raise HTTPException(status_code=404, detail="Cell not found")

    source = data.source if data and data.source else cell.source

    output = await execution_sandbox.execute(cell.cell_type, source)

    cell.output = output
    if data and data.source:
        cell.source = data.source

    await session.flush()

    return CellExecuteResponse(
        cell_id=cell.id,
        status=output.get("status", "error"),
        output=output,
    )

from fastapi.responses import StreamingResponse
from app.llm.client import llm_client

@router.post("/cells/{cell_id}/edit-with-ai")
async def edit_cell_with_ai(
    cell_id: str,
    data: CellEditRequest,
    session: AsyncSession = Depends(get_session),
):
    cell = await session.get(Cell, cell_id)
    if not cell:
        raise HTTPException(status_code=404, detail="Cell not found")

    sys_prompt = f"You are an expert AI assistant that edits {cell.cell_type} code within a data notebook. Provide ONLY the modified raw {cell.cell_type} code. Do NOT wrap the output in markdown code blocks like ```sql or ```python. Do NOT provide any conversational text or explanations. Your entire response must be the exact raw code to replace the cell's contents."
    
    user_prompt = f"Current code:\n{cell.source}\n\nUser request: {data.prompt}"

    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_prompt},
    ]

    async def stream_generator():
        try:
            async for chunk in llm_client.stream(messages=messages, temperature=0.1, max_tokens=4096):
                yield chunk
        except Exception as e:
            yield str(e)

    return StreamingResponse(stream_generator(), media_type="text/event-stream")
