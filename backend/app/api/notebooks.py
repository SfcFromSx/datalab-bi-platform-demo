"""Notebook CRUD API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Cell, Notebook
from app.schemas import NotebookCreate, NotebookListResponse, NotebookResponse, NotebookUpdate

router = APIRouter(tags=["notebooks"])


@router.get("/notebooks", response_model=list[NotebookListResponse])
async def list_notebooks(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Notebook).order_by(Notebook.updated_at.desc())
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
                title=nb.title,
                description=nb.description,
                created_at=nb.created_at,
                updated_at=nb.updated_at,
                cell_count=cell_count,
            )
        )
    return response


@router.post("/notebooks", response_model=NotebookResponse, status_code=201)
async def create_notebook(
    data: NotebookCreate, session: AsyncSession = Depends(get_session)
):
    notebook = Notebook(title=data.title, description=data.description)
    session.add(notebook)
    await session.flush()
    await session.refresh(notebook)
    return notebook


@router.get("/notebooks/{notebook_id}", response_model=NotebookResponse)
async def get_notebook(
    notebook_id: str, session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(Notebook).where(Notebook.id == notebook_id)
    )
    notebook = result.scalar_one_or_none()
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")
    return notebook


@router.put("/notebooks/{notebook_id}", response_model=NotebookResponse)
async def update_notebook(
    notebook_id: str,
    data: NotebookUpdate,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Notebook).where(Notebook.id == notebook_id)
    )
    notebook = result.scalar_one_or_none()
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")

    if data.title is not None:
        notebook.title = data.title
    if data.description is not None:
        notebook.description = data.description

    await session.flush()
    await session.refresh(notebook)
    return notebook


@router.delete("/notebooks/{notebook_id}", status_code=204)
async def delete_notebook(
    notebook_id: str, session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(Notebook).where(Notebook.id == notebook_id)
    )
    notebook = result.scalar_one_or_none()
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")

    await session.delete(notebook)
