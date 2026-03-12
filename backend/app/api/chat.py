"""ChatBI SSE streaming endpoints: chat and design modes."""

from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import chatbi_agent
from app.agents.context_builder import load_notebook_query_context
from app.agents.design_agent import design_agent
from app.database import get_session
from app.models import Cell, Notebook

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    query: str
    notebook_id: Optional[str] = None
    datasource_id: Optional[str] = None


@router.post("/chat")
async def chat_stream(
    data: ChatRequest,
    session: AsyncSession = Depends(get_session),
):
    context: dict = {}
    if data.notebook_id:
        context = await load_notebook_query_context(
            session,
            data.notebook_id,
            data.query,
            datasource_id=data.datasource_id,
        )

    async def event_generator():
        try:
            async for step in chatbi_agent.stream_query(data.query, context):
                yield _sse("step", step)
            yield _sse("done", {})
        except Exception as e:
            logger.error(f"Chat stream error: {e}")
            yield _sse("error", {"message": str(e)})

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/chat/design")
async def design_stream(
    data: ChatRequest,
    session: AsyncSession = Depends(get_session),
):
    if not data.notebook_id:
        raise HTTPException(status_code=400, detail="notebook_id is required for design mode")

    notebook = await session.get(Notebook, data.notebook_id)
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")

    context = await load_notebook_query_context(
        session,
        data.notebook_id,
        data.query,
        datasource_id=data.datasource_id,
    )

    cells_result = await session.execute(
        select(Cell)
        .where(Cell.notebook_id == data.notebook_id)
        .order_by(Cell.position)
    )
    cells = cells_result.scalars().all()
    cells_summary = "\n".join(
        f"[{c.id}] pos={c.position} type={c.cell_type.value} source={c.source[:120]!r}"
        for c in cells
    ) or "(empty notebook)"
    context["cells_summary"] = cells_summary

    async def event_generator():
        try:
            async for step in design_agent.stream_design(data.query, context):
                yield _sse("step", step)
            yield _sse("done", {})
        except Exception as e:
            logger.error(f"Design stream error: {e}")
            yield _sse("error", {"message": str(e)})

    return StreamingResponse(event_generator(), media_type="text/event-stream")


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, default=str)}\n\n"
