"""Agent query API endpoints."""

from __future__ import annotations

import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import proxy_agent
from app.database import get_session
from app.models import Cell, CellType, Notebook
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

    result = await session.execute(
        select(Cell)
        .where(
            Cell.notebook_id == data.notebook_id,
        )
        .order_by(Cell.position)
    )
    existing_cells = result.scalars().all()

    agent_context = {
        "notebook_id": data.notebook_id,
        "cell_id": data.cell_id,
        "datasource_id": data.datasource_id,
        "notebook_cells": existing_cells,
        "notebook_context": _build_notebook_context(existing_cells),
    }

    if data.datasource_id:
        from app.execution import sql_executor

        tables = sql_executor.get_tables(data.datasource_id)
        schemas = []
        for table in tables:
            cols = sql_executor.get_schema(table, data.datasource_id)
            col_strs = [f"  {c['column_name']} ({c['column_type']})" for c in cols]
            schemas.append(f"Table: {table}\n" + "\n".join(col_strs))
        agent_context["schema"] = "\n\n".join(schemas) if schemas else "No schema available"

    try:
        agent_result = await proxy_agent.execute(data.query, agent_context)
    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        return AgentQueryResponse(
            task_id=str(uuid.uuid4()),
            status="error",
            message=str(e),
        )

    content = agent_result.content
    cells_created = []

    if isinstance(content, dict) and "results" in content:
        max_pos_result = await session.execute(
            select(Cell.position)
            .where(Cell.notebook_id == data.notebook_id)
            .order_by(Cell.position.desc())
            .limit(1)
        )
        max_pos_row = max_pos_result.first()
        next_pos = (max_pos_row[0] + 1) if max_pos_row else 0

        for result_item in content["results"]:
            cell_type_str = result_item.get("cell_type", "python")
            try:
                cell_type = CellType(cell_type_str)
            except ValueError:
                cell_type = CellType.PYTHON

            cell_content = result_item.get("content", "")
            if isinstance(cell_content, dict):
                if cell_type == CellType.CHART:
                    cell_source = json.dumps(cell_content)
                elif cell_type == CellType.SQL and "query" in cell_content:
                    cell_source = str(cell_content.get("query", ""))
                else:
                    cell_source = json.dumps(cell_content, indent=2)
            else:
                cell_source = str(cell_content)

            cell_output = result_item.get("output")

            new_cell = Cell(
                notebook_id=data.notebook_id,
                cell_type=cell_type,
                source=cell_source,
                output=cell_output,
                position=next_pos,
            )
            session.add(new_cell)
            await session.flush()
            await session.refresh(new_cell)

            cells_created.append({
                "id": new_cell.id,
                "cell_type": cell_type.value,
                "source": cell_source,
                "position": next_pos,
            })
            next_pos += 1

    # Extract the conversational message if available
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
        cells_created=cells_created,
    )


def _build_notebook_context(cells: list[Cell]) -> str:
    parts = []
    for cell in cells[-10:]:
        source_preview = cell.source[:300] if cell.source else ""
        output_summary = ""
        if isinstance(cell.output, dict):
            if cell.output.get("data") and isinstance(cell.output["data"], dict):
                output_summary = f" output={cell.output['data'].get('variable', 'dataframe')}"
            elif cell.output.get("columns"):
                output_summary = f" output=columns:{cell.output.get('columns')}"
        parts.append(f"[{cell.cell_type.value} cell]{output_summary} {source_preview}")
    return "\n---\n".join(parts)
