from __future__ import annotations

from typing import TypeVar

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


async def get_workspace_resource(
    session: AsyncSession,
    model: type[T],
    resource_id: str,
    workspace_id: str,
) -> T | None:
    result = await session.execute(
        select(model).where(  # type: ignore[arg-type]
            model.id == resource_id,  # type: ignore[attr-defined]
            model.workspace_id == workspace_id,  # type: ignore[attr-defined]
        )
    )
    return result.scalar_one_or_none()


async def require_workspace_resource(
    session: AsyncSession,
    model: type[T],
    resource_id: str,
    workspace_id: str,
    detail: str,
) -> T:
    resource = await get_workspace_resource(session, model, resource_id, workspace_id)
    if not resource:
        raise HTTPException(status_code=404, detail=detail)
    return resource
