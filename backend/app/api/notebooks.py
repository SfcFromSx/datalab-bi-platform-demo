"""Notebook CRUD API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.enterprise import EnterpriseContext, log_audit_event, require_role
from app.enterprise.resources import require_workspace_resource
from app.models import Cell, Folder, Notebook
from app.models.membership import WorkspaceRole
from app.schemas import NotebookCreate, NotebookListResponse, NotebookResponse, NotebookUpdate

router = APIRouter(tags=["notebooks"])


@router.get("/notebooks", response_model=list[NotebookListResponse])
async def list_notebooks(
    context: EnterpriseContext = Depends(require_role(WorkspaceRole.VIEWER)),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Notebook)
        .where(Notebook.workspace_id == context.workspace.id)
        .order_by(Notebook.updated_at.desc())
    )
    notebooks = result.scalars().all()
    response = []
    for nb in notebooks:
        count_result = await session.execute(
            select(func.count()).where(Cell.notebook_id == nb.id)
        )
        cell_count = count_result.scalar() or 0
        response.append(
            NotebookListResponse(
                id=nb.id,
                workspace_id=nb.workspace_id,
                title=nb.title,
                description=nb.description,
                folder_id=nb.folder_id,
                created_at=nb.created_at,
                updated_at=nb.updated_at,
                cell_count=cell_count,
            )
        )
    return response


@router.post("/notebooks", response_model=NotebookResponse, status_code=201)
async def create_notebook(
    data: NotebookCreate,
    context: EnterpriseContext = Depends(require_role(WorkspaceRole.ANALYST)),
    session: AsyncSession = Depends(get_session),
):
    folder_id = None
    if data.folder_id:
        folder = await require_workspace_resource(
            session,
            Folder,
            data.folder_id,
            context.workspace.id,
            "Folder not found",
        )
        folder_id = folder.id

    notebook = Notebook(
        workspace_id=context.workspace.id,
        title=data.title,
        description=data.description,
        folder_id=folder_id,
    )
    session.add(notebook)
    await session.flush()
    await session.refresh(notebook)
    await log_audit_event(
        session,
        context,
        action="notebook.create",
        resource_type="notebook",
        resource_id=notebook.id,
        details={"title": notebook.title, "folder_id": notebook.folder_id},
    )
    return notebook


@router.get("/notebooks/{notebook_id}", response_model=NotebookResponse)
async def get_notebook(
    notebook_id: str,
    context: EnterpriseContext = Depends(require_role(WorkspaceRole.VIEWER)),
    session: AsyncSession = Depends(get_session),
):
    notebook = await require_workspace_resource(
        session,
        Notebook,
        notebook_id,
        context.workspace.id,
        "Notebook not found",
    )
    return notebook


@router.put("/notebooks/{notebook_id}", response_model=NotebookResponse)
async def update_notebook(
    notebook_id: str,
    data: NotebookUpdate,
    context: EnterpriseContext = Depends(require_role(WorkspaceRole.ANALYST)),
    session: AsyncSession = Depends(get_session),
):
    notebook = await require_workspace_resource(
        session,
        Notebook,
        notebook_id,
        context.workspace.id,
        "Notebook not found",
    )

    if data.title is not None:
        notebook.title = data.title
    if data.description is not None:
        notebook.description = data.description
    if data.folder_id is not None:
        if data.folder_id == "":
            notebook.folder_id = None
        else:
            folder = await require_workspace_resource(
                session,
                Folder,
                data.folder_id,
                context.workspace.id,
                "Folder not found",
            )
            notebook.folder_id = folder.id

    await session.flush()
    await session.refresh(notebook)
    await log_audit_event(
        session,
        context,
        action="notebook.update",
        resource_type="notebook",
        resource_id=notebook.id,
        details={"title": notebook.title, "folder_id": notebook.folder_id},
    )
    return notebook


@router.delete("/notebooks/{notebook_id}", status_code=204)
async def delete_notebook(
    notebook_id: str,
    context: EnterpriseContext = Depends(require_role(WorkspaceRole.ANALYST)),
    session: AsyncSession = Depends(get_session),
):
    notebook = await require_workspace_resource(
        session,
        Notebook,
        notebook_id,
        context.workspace.id,
        "Notebook not found",
    )
    await log_audit_event(
        session,
        context,
        action="notebook.delete",
        resource_type="notebook",
        resource_id=notebook.id,
        details={"title": notebook.title},
    )
    await session.delete(notebook)
