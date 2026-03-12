"""Agent task management and SSE streaming endpoints."""

from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.auto_agent import auto_agent
from app.database import get_session
from app.models.agent_task import AgentTask, AgentTaskStatus
from app.schemas.agent_task import (
    AgentTaskCreate,
    AgentTaskListResponse,
    AgentTaskResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["agent-tasks"])


@router.post("/agent-tasks")
async def create_agent_task(
    data: AgentTaskCreate,
    session: AsyncSession = Depends(get_session),
):
    task = AgentTask(
        query=data.query,
        notebook_id=data.notebook_id,
        datasource_id=data.datasource_id,
        status=AgentTaskStatus.PENDING.value,
    )
    session.add(task)
    await session.flush()
    await session.refresh(task)

    async def event_generator():
        try:
            async for step in auto_agent.run_task(task, session):
                yield _sse("step", step)
            yield _sse("done", {"task_id": task.id})
        except Exception as e:
            logger.error(f"Agent task stream error: {e}")
            task.status = AgentTaskStatus.FAILED.value
            task.error = str(e)
            await session.flush()
            yield _sse("error", {"message": str(e)})

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/agent-tasks", response_model=AgentTaskListResponse)
async def list_agent_tasks(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
):
    query = select(AgentTask)
    count_query = select(func.count()).select_from(AgentTask)

    if status:
        query = query.where(AgentTask.status == status)
        count_query = count_query.where(AgentTask.status == status)

    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    result = await session.execute(
        query.order_by(desc(AgentTask.created_at)).offset(offset).limit(limit)
    )
    tasks = result.scalars().all()

    return AgentTaskListResponse(
        tasks=[AgentTaskResponse.model_validate(t) for t in tasks],
        total=total,
    )


@router.get("/agent-tasks/{task_id}", response_model=AgentTaskResponse)
async def get_agent_task(
    task_id: str,
    session: AsyncSession = Depends(get_session),
):
    task = await session.get(AgentTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Agent task not found")
    return AgentTaskResponse.model_validate(task)


@router.post("/agent-tasks/{task_id}/cancel", response_model=AgentTaskResponse)
async def cancel_agent_task(
    task_id: str,
    session: AsyncSession = Depends(get_session),
):
    task = await session.get(AgentTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Agent task not found")

    if task.status in (AgentTaskStatus.COMPLETED.value, AgentTaskStatus.FAILED.value, AgentTaskStatus.CANCELLED.value):
        raise HTTPException(status_code=400, detail=f"Cannot cancel task in {task.status} state")

    task.status = AgentTaskStatus.CANCELLED.value
    await session.flush()
    await session.refresh(task)
    return AgentTaskResponse.model_validate(task)


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, default=str)}\n\n"
