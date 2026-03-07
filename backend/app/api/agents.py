"""Agent query API endpoints."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import proxy_agent
from app.agents.context_builder import load_notebook_query_context
from app.database import get_session
from app.models import Notebook
from app.schemas import AgentQueryRequest, AgentQueryResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["agents"])


@router.post("/agents/query", response_model=AgentQueryResponse)
async def agent_query(
    data: AgentQueryRequest,
    session: AsyncSession = Depends(get_session),
):
    nb = await session.get(Notebook, data.notebook_id)
    if not nb:
        raise HTTPException(status_code=404, detail="Notebook not found")

    try:
        agent_context = await load_notebook_query_context(
            session,
            data.notebook_id,
            data.query,
            focus_cell_id=data.cell_id,
            datasource_id=data.datasource_id,
        )
        agent_result = await proxy_agent.execute(data.query, agent_context)
    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        return AgentQueryResponse(
            task_id=str(uuid.uuid4()),
            status="error",
            message=str(e),
        )

    content = agent_result.content
    agent_msg = "Agent task completed successfully"
    if isinstance(content, dict) and "message" in content:
        agent_msg = content["message"]

    return AgentQueryResponse(
        task_id=(
            content.get("task_id", str(uuid.uuid4()))
            if isinstance(content, dict)
            else str(uuid.uuid4())
        ),
        status="completed",
        message=agent_msg,
        cells_created=[],
    )
