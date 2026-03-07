from __future__ import annotations

import json
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Cell, DataSource
from app.notebook_runtime import (
    build_cell_context,
    build_query_context,
    build_runtime_bundle,
)


def build_notebook_query_context(
    cells: Iterable[Any],
    query: str,
    focus_cell_id: str | None = None,
    datasource: DataSource | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    context = {
        "notebook_context": "",
        "table_context": "{}",
        "value_context": "{}",
        "cell_context": [],
        "datasource_context": _format_datasource_context(datasource),
        "available_bindings": [],
    }

    cell_list = list(cells)
    if not cell_list:
        return context

    bundle = build_runtime_bundle(cell_list)
    query_context = build_query_context(
        bundle,
        query,
        focus_cell_id=focus_cell_id,
        task_type="general",
        limit=limit,
    )
    cell_context = []
    if focus_cell_id and focus_cell_id in bundle.cells_by_id:
        cell_context = build_cell_context(bundle, focus_cell_id, task_type="general")

    bindings = sorted(
        set(json.loads(query_context["table_context"]))
        | set(json.loads(query_context["value_context"]))
    )
    return {
        "notebook_context": query_context["notebook_context"],
        "table_context": query_context["table_context"],
        "value_context": query_context["value_context"],
        "cell_context": cell_context,
        "datasource_context": _format_datasource_context(datasource),
        "available_bindings": bindings,
    }


async def load_notebook_query_context(
    session: AsyncSession,
    notebook_id: str,
    query: str,
    focus_cell_id: str | None = None,
    datasource_id: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    cells_result = await session.execute(
        select(Cell)
        .where(Cell.notebook_id == notebook_id)
        .order_by(Cell.position)
    )
    cells = cells_result.scalars().all()
    datasource = await session.get(DataSource, datasource_id) if datasource_id else None
    return build_notebook_query_context(
        cells,
        query,
        focus_cell_id=focus_cell_id,
        datasource=datasource,
        limit=limit,
    )


def _format_datasource_context(datasource: DataSource | None) -> str:
    if not datasource:
        return ""

    parts = [f"Data source: {datasource.name} ({datasource.ds_type.value})"]
    if datasource.metadata_:
        parts.append(json.dumps(datasource.metadata_, default=str, indent=2))
    return "\n".join(parts)
