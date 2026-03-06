"""Folder CRUD API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.enterprise import EnterpriseContext, log_audit_event, require_role
from app.enterprise.resources import require_workspace_resource
from app.models import Folder, Notebook
from app.models.membership import WorkspaceRole
from app.schemas.folder import FolderCreate, FolderResponse, FolderUpdate

router = APIRouter(tags=["folders"])


@router.get("/folders", response_model=list[FolderResponse])
async def list_folders(
    context: EnterpriseContext = Depends(require_role(WorkspaceRole.VIEWER)),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Folder)
        .where(Folder.workspace_id == context.workspace.id)
        .order_by(Folder.position, Folder.created_at)
    )
    return result.scalars().all()


@router.post("/folders", response_model=FolderResponse, status_code=201)
async def create_folder(
    data: FolderCreate,
    context: EnterpriseContext = Depends(require_role(WorkspaceRole.ANALYST)),
    session: AsyncSession = Depends(get_session),
):
    folder = Folder(workspace_id=context.workspace.id, name=data.name)
    session.add(folder)
    await session.flush()
    await session.refresh(folder)
    await log_audit_event(
        session,
        context,
        action="folder.create",
        resource_type="folder",
        resource_id=folder.id,
        details={"name": folder.name},
    )
    return folder


@router.put("/folders/{folder_id}", response_model=FolderResponse)
async def update_folder(
    folder_id: str,
    data: FolderUpdate,
    context: EnterpriseContext = Depends(require_role(WorkspaceRole.ANALYST)),
    session: AsyncSession = Depends(get_session),
):
    folder = await require_workspace_resource(
        session,
        Folder,
        folder_id,
        context.workspace.id,
        "Folder not found",
    )

    if data.name is not None:
        folder.name = data.name
    if data.position is not None:
        folder.position = data.position

    await session.flush()
    await session.refresh(folder)
    await log_audit_event(
        session,
        context,
        action="folder.update",
        resource_type="folder",
        resource_id=folder.id,
        details={"name": folder.name, "position": folder.position},
    )
    return folder


@router.delete("/folders/{folder_id}", status_code=204)
async def delete_folder(
    folder_id: str,
    context: EnterpriseContext = Depends(require_role(WorkspaceRole.ANALYST)),
    session: AsyncSession = Depends(get_session),
):
    folder = await require_workspace_resource(
        session,
        Folder,
        folder_id,
        context.workspace.id,
        "Folder not found",
    )

    # Unlink all notebooks in this folder (move them to uncategorized)
    nb_result = await session.execute(
        select(Notebook).where(
            Notebook.folder_id == folder_id,
            Notebook.workspace_id == context.workspace.id,
        )
    )
    for nb in nb_result.scalars().all():
        nb.folder_id = None

    await log_audit_event(
        session,
        context,
        action="folder.delete",
        resource_type="folder",
        resource_id=folder.id,
        details={"name": folder.name},
    )
    await session.delete(folder)
