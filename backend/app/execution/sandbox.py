"""Unified execution sandbox that delegates to Python or SQL executors."""

from __future__ import annotations

from typing import Any

from app.execution.python_executor import python_executor
from app.execution.sql_executor import sql_executor
from app.models.cell import CellType


class ExecutionSandbox:
    """Routes cell execution to the appropriate engine."""

    async def execute(
        self,
        cell_type: CellType,
        source: str,
        datasource_id: str | None = None,
    ) -> dict[str, Any]:
        if cell_type == CellType.PYTHON:
            return await python_executor.execute(source)
        elif cell_type == CellType.SQL:
            return sql_executor.execute(source, datasource_id)
        elif cell_type == CellType.MARKDOWN:
            return {"status": "success", "html": source, "error": None}
        elif cell_type == CellType.CHART:
            return {"status": "success", "error": None}
        else:
            return {"status": "error", "error": f"Unknown cell type: {cell_type}"}


execution_sandbox = ExecutionSandbox()
