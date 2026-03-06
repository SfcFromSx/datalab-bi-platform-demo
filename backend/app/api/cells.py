"""Cell CRUD and execution API endpoints."""

from __future__ import annotations

import ast
import json
import re

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cell_agents import cell_agent_runtime
from app.database import get_session
from app.enterprise import EnterpriseContext, log_audit_event, require_role
from app.enterprise.resources import require_workspace_resource
from app.llm.client import llm_client
from app.models import Cell, DataSource, Notebook
from app.models.cell import CellType
from app.models.membership import WorkspaceRole
from app.notebook_runtime import (
    CELL_TASK_TYPES,
    build_cell_context,
    build_query_context,
    build_runtime_bundle,
)
from app.schemas import (
    CellCreate,
    CellExecuteRequest,
    CellExecuteResponse,
    CellMoveRequest,
    CellUpdate,
)
from app.schemas.notebook import CellResponse


class CellEditRequest(BaseModel):
    prompt: str


router = APIRouter(tags=["cells"])


@router.post(
    "/notebooks/{notebook_id}/cells",
    response_model=CellResponse,
    status_code=201,
)
async def create_cell(
    notebook_id: str,
    data: CellCreate,
    context: EnterpriseContext = Depends(require_role(WorkspaceRole.ANALYST)),
    session: AsyncSession = Depends(get_session),
):
    await require_workspace_resource(
        session,
        Notebook,
        notebook_id,
        context.workspace.id,
        "Notebook not found",
    )

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
        workspace_id=context.workspace.id,
        notebook_id=notebook_id,
        cell_type=data.cell_type,
        source=data.source,
        position=position,
        metadata_=data.metadata,
    )
    session.add(cell)
    await session.flush()
    await session.refresh(cell)
    await log_audit_event(
        session,
        context,
        action="cell.create",
        resource_type="cell",
        resource_id=cell.id,
        details={"cell_type": cell.cell_type.value, "position": cell.position},
    )
    return cell


@router.put("/cells/{cell_id}", response_model=CellResponse)
async def update_cell(
    cell_id: str,
    data: CellUpdate,
    context: EnterpriseContext = Depends(require_role(WorkspaceRole.ANALYST)),
    session: AsyncSession = Depends(get_session),
):
    cell = await require_workspace_resource(
        session,
        Cell,
        cell_id,
        context.workspace.id,
        "Cell not found",
    )

    if data.source is not None:
        cell.source = data.source
    if data.metadata is not None:
        cell.metadata_ = data.metadata

    await session.flush()
    await session.refresh(cell)
    await log_audit_event(
        session,
        context,
        action="cell.update",
        resource_type="cell",
        resource_id=cell.id,
        details={"cell_type": cell.cell_type.value},
    )
    return cell


@router.delete("/cells/{cell_id}", status_code=204)
async def delete_cell(
    cell_id: str,
    context: EnterpriseContext = Depends(require_role(WorkspaceRole.ANALYST)),
    session: AsyncSession = Depends(get_session),
):
    cell = await require_workspace_resource(
        session,
        Cell,
        cell_id,
        context.workspace.id,
        "Cell not found",
    )
    await log_audit_event(
        session,
        context,
        action="cell.delete",
        resource_type="cell",
        resource_id=cell.id,
        details={"cell_type": cell.cell_type.value},
    )
    await session.delete(cell)


@router.put("/cells/{cell_id}/move", response_model=CellResponse)
async def move_cell(
    cell_id: str,
    data: CellMoveRequest,
    context: EnterpriseContext = Depends(require_role(WorkspaceRole.ANALYST)),
    session: AsyncSession = Depends(get_session),
):
    cell = await require_workspace_resource(
        session,
        Cell,
        cell_id,
        context.workspace.id,
        "Cell not found",
    )

    cell.position = data.position
    await session.flush()
    await session.refresh(cell)
    await log_audit_event(
        session,
        context,
        action="cell.move",
        resource_type="cell",
        resource_id=cell.id,
        details={"position": cell.position},
    )
    return cell


@router.post("/cells/{cell_id}/execute", response_model=CellExecuteResponse)
async def execute_cell(
    cell_id: str,
    data: CellExecuteRequest | None = None,
    context: EnterpriseContext = Depends(require_role(WorkspaceRole.ANALYST)),
    session: AsyncSession = Depends(get_session),
):
    cell = await require_workspace_resource(
        session,
        Cell,
        cell_id,
        context.workspace.id,
        "Cell not found",
    )

    source = data.source if data and data.source else cell.source
    if data and data.source is not None:
        cell.source = data.source

    notebook_cells = await _load_notebook_cells(
        session,
        cell.notebook_id,
        context.workspace.id,
    )
    executed_cells: list[dict] = []
    datasource_result = await session.execute(
        select(DataSource).where(DataSource.workspace_id == context.workspace.id)
    )
    workspace_datasources = datasource_result.scalars().all()
    try:
        execution_result = await cell_agent_runtime.execute_target(
            notebook_cells,
            cell.id,
            workspace_key=context.workspace.slug,
            source_overrides={cell.id: source},
            datasources=workspace_datasources,
        )
        for notebook_cell in notebook_cells:
            if notebook_cell.id in execution_result.outputs_by_id:
                notebook_cell.output = execution_result.outputs_by_id[notebook_cell.id]
                executed_cells.append(
                    {
                        "cell_id": notebook_cell.id,
                        "output": notebook_cell.output,
                    }
                )
        output = execution_result.outputs_by_id[cell.id]
    except Exception as exc:
        output = {
            "status": "error",
            "error": str(exc),
        }

    cell.output = output

    await session.flush()
    await log_audit_event(
        session,
        context,
        action="cell.execute",
        resource_type="cell",
        resource_id=cell.id,
        details={
            "cell_type": cell.cell_type.value,
            "status": output.get("status", "error"),
        },
    )

    return CellExecuteResponse(
        cell_id=cell.id,
        status=output.get("status", "error"),
        output=output,
        executed_cells=executed_cells,
    )


@router.post("/cells/{cell_id}/edit-with-ai")
async def edit_cell_with_ai(
    cell_id: str,
    data: CellEditRequest,
    context: EnterpriseContext = Depends(require_role(WorkspaceRole.ANALYST)),
    session: AsyncSession = Depends(get_session),
):
    cell = await require_workspace_resource(
        session,
        Cell,
        cell_id,
        context.workspace.id,
        "Cell not found",
    )
    notebook_cells = await _load_notebook_cells(session, cell.notebook_id, context.workspace.id)
    runtime_bundle = build_runtime_bundle(notebook_cells)
    query_context = build_query_context(
        runtime_bundle,
        data.prompt,
        focus_cell_id=cell.id,
        task_type=CELL_TASK_TYPES.get(cell.cell_type.value, "general"),
        limit=10,
    )
    cell_context = build_cell_context(runtime_bundle, cell.id)
    runtime_info = cell_agent_runtime.write_edit_task(
        notebook_cells,
        cell.id,
        data.prompt,
        workspace_key=context.workspace.slug,
        source_overrides={cell.id: cell.source},
    )

    messages = _build_ai_edit_messages(
        cell_type=cell.cell_type,
        current_source=cell.source,
        user_request=data.prompt,
        notebook_context=query_context["notebook_context"],
        table_context=query_context["table_context"],
        cell_context=cell_context,
    )

    await log_audit_event(
        session,
        context,
        action="cell.edit_with_ai",
        resource_type="cell",
        resource_id=cell.id,
        details={"cell_type": cell.cell_type.value, "prompt_length": len(data.prompt)},
    )

    async def stream_generator():
        yield _sse_event(
            "progress",
            {
                "stage": "context",
                "message": "Collecting related notebook cells",
                "progress": 0.1,
                "details": runtime_info,
            },
        )
        yield _sse_event(
            "progress",
            {
                "stage": "dag",
                "message": f"Computed a {len(runtime_info['plan'])}-cell execution plan",
                "progress": 0.18,
                "details": runtime_info,
            },
        )
        yield _sse_event(
            "progress",
            {
                "stage": "ipc",
                "message": f"Prepared {len(runtime_info['dependencies'])} dependency links in the cell workspace",
                "progress": 0.26,
                "details": runtime_info,
            },
        )
        yield _sse_event(
            "progress",
            {
                "stage": "rewrite",
                "message": "Preparing cell-specific rewrite instructions",
                "progress": 0.36,
                "details": runtime_info,
            },
        )
        try:
            yield _sse_event(
                "progress",
                {
                    "stage": "generate",
                    "message": "Waiting for model response",
                    "progress": 0.48,
                    "details": runtime_info,
                },
            )
            chunks: list[str] = []
            chunk_count = 0
            async for chunk in llm_client.stream(
                messages=messages,
                temperature=0.1,
                max_tokens=4096,
            ):
                chunks.append(chunk)
                chunk_count += 1
                yield _sse_event("chunk", {"content": chunk})
                yield _sse_event(
                    "progress",
                    {
                        "stage": "generate",
                        "message": "Streaming updated draft",
                        "progress": min(0.84, 0.48 + chunk_count * 0.02),
                        "details": runtime_info,
                    },
                )
            yield _sse_event(
                "progress",
                {
                    "stage": "validate",
                    "message": "Validating the rewritten cell contract",
                    "progress": 0.92,
                    "details": runtime_info,
                },
            )
            final_content = _normalize_ai_edit_output(
                cell.cell_type,
                cell.source,
                "".join(chunks),
            )
            yield _sse_event(
                "done",
                {
                    "content": final_content,
                    "progress": 1.0,
                    "message": "Cell rewrite complete",
                    "details": runtime_info,
                },
            )
        except Exception as e:
            yield _sse_event(
                "error",
                {
                    "message": str(e),
                    "progress": 1.0,
                    "details": runtime_info,
                },
            )

    return StreamingResponse(stream_generator(), media_type="text/event-stream")


async def _load_notebook_cells(
    session: AsyncSession,
    notebook_id: str,
    workspace_id: str,
) -> list[Cell]:
    result = await session.execute(
        select(Cell)
        .where(
            Cell.notebook_id == notebook_id,
            Cell.workspace_id == workspace_id,
        )
        .order_by(Cell.position)
    )
    return result.scalars().all()


def _build_ai_edit_messages(
    cell_type: CellType,
    current_source: str,
    user_request: str,
    notebook_context: str,
    table_context: str,
    cell_context: list[dict],
) -> list[dict[str, str]]:
    cell_type_value = cell_type.value
    system_prompt = (
        "You are an expert AI notebook editor. Return ONLY the final rewritten cell source. "
        "Never include markdown fences or commentary."
    )
    if cell_type == CellType.CHART:
        system_prompt += (
            " The cell must be valid JSON. If the chart depends on another cell's output, "
            "prefer a `data_source` field that names the upstream notebook variable."
        )
    elif cell_type == CellType.MARKDOWN:
        system_prompt += (
            " Markdown cells may use placeholders like `{{ sales_summary.row_count }}` or "
            "`{{ sales_summary.columns }}` when referencing upstream tabular outputs."
        )
    elif cell_type == CellType.SQL:
        system_prompt += (
            " SQL cells may define notebook outputs with comments such as "
            "`-- output: sales_summary`."
        )
    elif cell_type == CellType.PYTHON:
        system_prompt += (
            " Python cells must stay executable as-is in a notebook environment that replays "
            "relevant upstream cells before execution."
        )
    contract_guidance = _build_cell_contract_guidance(cell_type, current_source)
    if contract_guidance:
        system_prompt += f" {contract_guidance}"

    user_prompt = "\n\n".join(
        [
            f"Cell type: {cell_type_value}",
            f"User request:\n{user_request}",
            f"Current cell source:\n{current_source}",
            f"Relevant notebook context:\n{notebook_context or 'No additional context'}",
            f"Available tabular outputs:\n{table_context or '{}'}",
            f"Focused cell neighborhood:\n{json.dumps(cell_context, default=str, indent=2)}",
        ]
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _normalize_ai_edit_output(
    cell_type: CellType,
    current_source: str,
    content: str,
) -> str:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 3:
            cleaned = "\n".join(lines[1:-1]).strip()
    if cell_type == CellType.SQL:
        return _normalize_sql_output(cleaned, current_source)
    if cell_type == CellType.PYTHON:
        ast.parse(cleaned)
        return cleaned
    if cell_type == CellType.CHART:
        parsed = json.loads(cleaned)
        current_spec = _load_json_object(current_source)
        if (
            isinstance(current_spec, dict)
            and isinstance(current_spec.get("data_source"), str)
            and current_spec["data_source"]
            and "data_source" not in parsed
        ):
            parsed["data_source"] = current_spec["data_source"]
        return json.dumps(parsed, indent=2)
    return cleaned


def _normalize_sql_output(content: str, current_source: str) -> str:
    output_match = re.search(r"--\s*output:\s*(\w+)", current_source, re.IGNORECASE)
    if output_match and not re.search(r"--\s*output:\s*\w+", content, re.IGNORECASE):
        return f"-- output: {output_match.group(1)}\n{content.lstrip()}"
    return content


def _load_json_object(raw: str) -> dict | None:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _build_cell_contract_guidance(cell_type: CellType, current_source: str) -> str:
    if cell_type == CellType.SQL:
        output_match = re.search(r"--\s*output:\s*(\w+)", current_source, re.IGNORECASE)
        if output_match:
            return (
                f"Preserve the notebook output alias `{output_match.group(1)}` unless the user "
                "explicitly asks to rename it."
            )
        return (
            "If the SQL result is intended for downstream cells, include a stable "
            "`-- output: variable_name` comment."
        )

    if cell_type == CellType.CHART:
        try:
            spec = json.loads(current_source)
        except json.JSONDecodeError:
            return "Return valid JSON that the chart cell can execute immediately."
        if isinstance(spec, dict) and isinstance(spec.get("data_source"), str):
            return (
                f"Preserve the `data_source` value `{spec['data_source']}` unless the user "
                "explicitly asks to change the upstream dependency."
            )
        return "Prefer a `data_source` field when the chart should stay linked to notebook data."

    if cell_type == CellType.MARKDOWN:
        if "{{" in current_source and "}}" in current_source:
            return (
                "Preserve placeholder syntax like `{{ variable.row_count }}` when the markdown "
                "should stay linked to live notebook outputs."
            )
        return "Use placeholders instead of hard-coded numbers when referencing notebook outputs."

    if cell_type == CellType.PYTHON:
        return (
            "Keep the final notebook-facing variable names stable unless the user explicitly "
            "requests a rename, especially for DataFrame outputs consumed by other cells."
        )

    return ""


def _sse_event(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, default=str)}\n\n"
