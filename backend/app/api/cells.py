"""Cell CRUD and execution API endpoints."""

from __future__ import annotations

import ast
import json
import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.execution.cell_runtime import CellRuntime
from app.database import get_session
from app.llm.client import llm_client
from app.models import Cell, DataSource, Notebook
from app.models.cell import CellType
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
cell_runtime = CellRuntime()


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
    notebook = await session.get(Notebook, notebook_id)
    if not notebook:
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
    cell_id: str,
    session: AsyncSession = Depends(get_session),
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
    if data and data.source is not None:
        cell.source = data.source

    notebook_cells = await _load_notebook_cells(
        session,
        cell.notebook_id,
    )
    executed_cells: list[dict] = []
    datasource_result = await session.execute(
        select(DataSource)
    )
    workspace_datasources = datasource_result.scalars().all()
    try:
        execution_result = await cell_runtime.execute_target(
            notebook_cells,
            cell.id,
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
    session: AsyncSession = Depends(get_session),
):
    cell = await session.get(Cell, cell_id)
    if not cell:
        raise HTTPException(status_code=404, detail="Cell not found")

    async def stream_generator():
        # Start immediately so the client knows we are alive
        yield _sse_event(
            "progress",
            {
                "stage": "context",
                "message": "Initializing AI rewrite engine",
                "progress": 0.05,
            },
        )

        try:
            notebook_cells = await _load_notebook_cells(session, cell.notebook_id)
            runtime_bundle = build_runtime_bundle(notebook_cells)
            
            yield _sse_event(
                "progress",
                {
                    "stage": "context",
                    "message": "Analyzing notebook context and dependencies",
                    "progress": 0.15,
                },
            )

            query_context = build_query_context(
                runtime_bundle,
                data.prompt,
                focus_cell_id=cell.id,
                task_type=CELL_TASK_TYPES.get(cell.cell_type.value, "general"),
                limit=10,
            )
            cell_context = build_cell_context(runtime_bundle, cell.id)
            
            runtime_info = cell_runtime.write_edit_task(
                notebook_cells,
                cell.id,
                data.prompt,
                source_overrides={cell.id: cell.source},
            )

            yield _sse_event(
                "progress",
                {
                    "stage": "dag",
                    "message": f"Prepared execution plan with {len(runtime_info['plan'])} steps",
                    "progress": 0.25,
                    "details": runtime_info,
                },
            )

            messages = _build_ai_edit_messages(
                cell_type=cell.cell_type,
                current_source=cell.source,
                user_request=data.prompt,
                notebook_context=query_context["notebook_context"],
                table_context=query_context["table_context"],
                cell_context=cell_context,
            )

            yield _sse_event(
                "progress",
                {
                    "stage": "generate",
                    "message": "Invoking AI model",
                    "progress": 0.4,
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
                        "progress": min(0.85, 0.4 + chunk_count * 0.01),
                        "details": runtime_info,
                    },
                )

            yield _sse_event(
                "progress",
                {
                    "stage": "validate",
                    "message": "Validating finalized source",
                    "progress": 0.9,
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
                    "message": "Cell rewrite successful",
                    "details": runtime_info,
                },
            )

        except Exception as e:
            yield _sse_event(
                "error",
                {
                    "message": str(e),
                    "progress": 1.0,
                },
            )

    return StreamingResponse(stream_generator(), media_type="text/event-stream")


async def _load_notebook_cells(
    session: AsyncSession,
    notebook_id: str,
) -> list[Cell]:
    result = await session.execute(
        select(Cell)
        .where(Cell.notebook_id == notebook_id)
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
        "You are an expert AI notebook editor. Your goal is to rewrite the provided cell source code based on the user's request.\n\n"
        "RULES:\n"
        "1. Return ONLY the final rewritten cell source code. Do not include markdown fences, comments outside the code, or explanations.\n"
        "2. You MUST restate the ENTIRE source code of the cell, including the parts that you did not change. Never return just a diff or a partial snippet.\n"
        "3. Preserve the existing functionality, variable names, and logic unless the user explicitly asks to change them.\n"
        "4. If you cannot fulfill the request, return the original source code as-is rather than an empty response."
    )
    if cell_type == CellType.CHART:
        system_prompt += (
            "\n\nCHART CELL RULE: The output must be valid JSON. Prefer using the `data_source` field to link to upstream variables."
        )
    elif cell_type == CellType.PYTHON:
        system_prompt += (
            "\n\nPYTHON CELL RULE: Ensure the code is valid Python 3. The cell will be executed in a notebook environment where upstream variables are already available."
        )
    
    contract_guidance = _build_cell_contract_guidance(cell_type, current_source)
    if contract_guidance:
        system_prompt += f"\n\nGUIDANCE: {contract_guidance}"

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
    # Try to extract code from markdown fences anywhere in the response
    pattern = r"```(?:\w+)?\n?(.*?)\n?```"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        cleaned = match.group(1).strip()
    else:
        cleaned = content.strip()

    if not cleaned:
        # Fallback to current source if AI returns nothing or we can't parse it
        # This prevents "deleting" the code on failure
        return current_source

    if cell_type == CellType.SQL:
        return _normalize_sql_output(cleaned, current_source)
    
    if cell_type == CellType.PYTHON:
        try:
            ast.parse(cleaned)
            return cleaned
        except SyntaxError:
            # If AI returned invalid Python, we might have accidentally captured commentary
            # Let's try to be conservative and not overwrite with garbage
            return cleaned 

    if cell_type == CellType.CHART:
        try:
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
        except json.JSONDecodeError:
            return cleaned

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
