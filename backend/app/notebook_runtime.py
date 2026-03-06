from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable

from app.context.dag import CellDependencyDAG
from app.context.retrieval import ContextRetriever
from app.context.tracker import variable_tracker

CELL_TASK_TYPES = {
    "sql": "nl2sql",
    "python": "nl2dscode",
    "chart": "nl2vis",
    "markdown": "report",
}


@dataclass
class NotebookRuntimeBundle:
    dag: CellDependencyDAG
    cells_by_id: dict[str, dict[str, Any]]
    ordered_cells: list[dict[str, Any]]
    retriever: ContextRetriever


def build_runtime_bundle(cells: Iterable[Any]) -> NotebookRuntimeBundle:
    ordered_cells = sorted(
        [_to_cell_dict(cell) for cell in cells],
        key=lambda item: item["position"],
    )
    dag = CellDependencyDAG()
    dag.build(ordered_cells)
    cells_by_id = {cell["id"]: cell for cell in ordered_cells}
    retriever = ContextRetriever(dag)
    return NotebookRuntimeBundle(
        dag=dag,
        cells_by_id=cells_by_id,
        ordered_cells=ordered_cells,
        retriever=retriever,
    )


def build_cell_context(
    bundle: NotebookRuntimeBundle,
    cell_id: str,
    task_type: str | None = None,
) -> list[dict[str, Any]]:
    task = task_type or CELL_TASK_TYPES.get(
        bundle.cells_by_id.get(cell_id, {}).get("cell_type", ""),
        "general",
    )
    return bundle.retriever.retrieve_cell_context(
        cell_id,
        task_type=task,
        cells_data=bundle.cells_by_id,
    )


def build_query_context(
    bundle: NotebookRuntimeBundle,
    query: str,
    focus_cell_id: str | None = None,
    task_type: str = "general",
    limit: int = 8,
) -> dict[str, Any]:
    relevant_cells = bundle.retriever.retrieve_query_context(
        query,
        focus_cell_id=focus_cell_id,
        task_type=task_type,
        cells_data=bundle.cells_by_id,
        limit=limit,
    )
    return {
        "cells": relevant_cells,
        "notebook_context": format_cells_for_llm(relevant_cells),
        "table_context": json.dumps(build_table_catalog(relevant_cells), default=str, indent=2),
    }


def build_python_bootstrap(
    bundle: NotebookRuntimeBundle,
    cell_id: str,
) -> tuple[str, dict[str, dict[str, Any]]]:
    ancestor_ids = bundle.dag.get_ancestors(cell_id)
    bootstrap_cells = [
        bundle.cells_by_id[ancestor_id]
        for ancestor_id in ancestor_ids
        if ancestor_id in bundle.cells_by_id
    ]
    bootstrap_cells.sort(key=lambda cell: cell["position"])

    bootstrap_code_parts: list[str] = []
    bootstrap_tables = build_table_catalog(bootstrap_cells)

    for cell in bootstrap_cells:
        if cell["cell_type"] == "python" and cell.get("source"):
            bootstrap_code_parts.append(cell["source"])

    return "\n\n".join(bootstrap_code_parts), bootstrap_tables


def build_sql_bootstrap_tables(
    bundle: NotebookRuntimeBundle,
    cell_id: str,
) -> dict[str, dict[str, Any]]:
    ancestor_ids = bundle.dag.get_ancestors(cell_id)
    bootstrap_cells = [
        bundle.cells_by_id[ancestor_id]
        for ancestor_id in ancestor_ids
        if ancestor_id in bundle.cells_by_id
    ]
    bootstrap_cells.sort(key=lambda cell: cell["position"])
    return build_table_catalog(bootstrap_cells)


def build_table_catalog(cells: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    tables: dict[str, dict[str, Any]] = {}
    for cell in cells:
        table = extract_output_table(cell)
        if not table:
            continue
        for variable_name in extract_variable_names(cell):
            tables[variable_name] = table
    return tables


def extract_variable_names(cell: dict[str, Any]) -> list[str]:
    cell_id = cell.get("id") or cell.get("cell_id")
    cell_type = cell.get("cell_type", "")
    source = cell.get("source", "")

    if not cell_id:
        return []

    output = cell.get("output") or {}
    data = output.get("data") if isinstance(output, dict) else None
    variable = data.get("variable") if isinstance(data, dict) else None
    if cell_type == "python":
        return [variable] if isinstance(variable, str) and variable else []

    analyzed = variable_tracker.analyze_cell(
        cell_id,
        cell_type,
        source,
    )
    if analyzed.defined:
        return sorted(analyzed.defined)

    return [variable] if isinstance(variable, str) and variable else []


def extract_output_table(cell: dict[str, Any]) -> dict[str, Any] | None:
    output = cell.get("output")
    if not isinstance(output, dict):
        return None

    if isinstance(output.get("data"), dict):
        data = output["data"]
        columns = data.get("columns") or []
        rows = data.get("rows") or []
        if columns:
            return {"columns": columns, "rows": rows}

    columns = output.get("columns") or []
    rows = output.get("rows") or []
    if columns:
        return {"columns": columns, "rows": rows}

    return None


def format_cells_for_llm(cells: Iterable[dict[str, Any]]) -> str:
    parts: list[str] = []
    for cell in cells:
        source = (cell.get("source") or "").strip()
        if len(source) > 800:
            source = source[:800] + "\n..."
        output_summary = summarize_output(cell.get("output"))
        defined = ", ".join(cell.get("variables_defined", []))
        referenced = ", ".join(cell.get("variables_referenced", []))
        parts.append(
            "\n".join(
                [
                    f"Cell {cell['cell_id']} ({cell['cell_type']})",
                    f"Defines: {defined or 'n/a'}",
                    f"References: {referenced or 'n/a'}",
                    f"Source:\n{source or '(empty)'}",
                    f"Output Summary: {output_summary or 'n/a'}",
                ]
            )
        )
    return "\n\n---\n\n".join(parts)


def summarize_output(output: Any) -> str:
    if not isinstance(output, dict):
        return ""
    if output.get("error"):
        return str(output["error"])
    if output.get("data") and isinstance(output["data"], dict):
        data = output["data"]
        return (
            f"DataFrame {data.get('variable', 'result')} "
            f"with columns {data.get('columns', [])} and {len(data.get('rows', []))} rows"
        )
    if output.get("columns"):
        return f"Columns {output['columns']} with {len(output.get('rows', []))} rows"
    if output.get("stdout"):
        return str(output["stdout"])[:400]
    if output.get("html"):
        return "Rendered markdown/html output"
    return ""


def _to_cell_dict(cell: Any) -> dict[str, Any]:
    if isinstance(cell, dict):
        cell_type = cell.get("cell_type", "")
        output = cell.get("output")
        return {
            "id": cell.get("id"),
            "workspace_id": cell.get("workspace_id"),
            "workspace_key": cell.get("workspace_key"),
            "notebook_id": cell.get("notebook_id"),
            "cell_type": cell_type.value if hasattr(cell_type, "value") else cell_type,
            "source": cell.get("source", ""),
            "output": output,
            "position": cell.get("position", 0),
            "metadata": cell.get("metadata") or cell.get("metadata_"),
        }

    cell_type = getattr(cell, "cell_type", "")
    if hasattr(cell_type, "value"):
        cell_type = cell_type.value
    return {
        "id": getattr(cell, "id"),
        "workspace_id": getattr(cell, "workspace_id", None),
        "workspace_key": getattr(cell, "workspace_key", None),
        "notebook_id": getattr(cell, "notebook_id", None),
        "cell_type": cell_type,
        "source": getattr(cell, "source", ""),
        "output": getattr(cell, "output", None),
        "position": getattr(cell, "position", 0),
        "metadata": getattr(cell, "metadata_", None),
    }
