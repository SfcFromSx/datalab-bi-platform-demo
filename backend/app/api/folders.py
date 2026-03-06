"""Folder CRUD API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Folder, Notebook
from app.schemas.folder import FolderCreate, FolderResponse, FolderUpdate

router = APIRouter(tags=["folders"])


@router.get("/folders", response_model=list[FolderResponse])
async def list_folders(
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Folder)
        .order_by(Folder.position, Folder.created_at)
    )
    return result.scalars().all()


@router.post("/folders", response_model=FolderResponse, status_code=201)
async def create_folder(
    data: FolderCreate,
    session: AsyncSession = Depends(get_session),
):
    folder = Folder(name=data.name)
    session.add(folder)
    await session.flush()
    await session.refresh(folder)
    return folder


@router.put("/folders/{folder_id}", response_model=FolderResponse)
async def update_folder(
    folder_id: str,
    data: FolderUpdate,
    session: AsyncSession = Depends(get_session),
):
    folder = await session.get(Folder, folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    if data.name is not None:
        folder.name = data.name
    if data.position is not None:
        folder.position = data.position

    await session.flush()
    await session.refresh(folder)
    return folder


@router.delete("/folders/{folder_id}", status_code=204)
async def delete_folder(
    folder_id: str,
    session: AsyncSession = Depends(get_session),
):
    folder = await session.get(Folder, folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    # Unlink all notebooks in this folder (move them to uncategorized)
    nb_result = await session.execute(
        select(Notebook).where(
            Notebook.folder_id == folder_id,
        )
    )
    for nb in nb_result.scalars().all():
        nb.folder_id = None

    await session.delete(folder)
