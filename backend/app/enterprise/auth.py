from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.models import (
    User,
    Workspace,
    WorkspaceMembership,
    WorkspaceRole,
    WorkspaceStatus,
)

ROLE_LEVELS = {
    WorkspaceRole.VIEWER: 0,
    WorkspaceRole.ANALYST: 1,
    WorkspaceRole.ADMIN: 2,
    WorkspaceRole.OWNER: 3,
}


@dataclass(slots=True)
class EnterpriseContext:
    request_id: str
    workspace: Workspace
    user: User
    membership: WorkspaceMembership


async def seed_enterprise_defaults(session: AsyncSession) -> None:
    workspace = await session.scalar(
        select(Workspace).where(Workspace.slug == settings.default_workspace_slug)
    )
    if not workspace:
        workspace = Workspace(
            name=settings.default_workspace_name,
            slug=settings.default_workspace_slug,
            description=settings.default_workspace_description,
        )
        session.add(workspace)
        await session.flush()

    user = await session.scalar(select(User).where(User.email == settings.default_user_email))
    if not user:
        user = User(email=settings.default_user_email, display_name=settings.default_user_name)
        session.add(user)
        await session.flush()

    membership = await session.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace.id,
            WorkspaceMembership.user_id == user.id,
        )
    )
    if not membership:
        session.add(
            WorkspaceMembership(
                workspace_id=workspace.id,
                user_id=user.id,
                role=WorkspaceRole.OWNER,
            )
        )
    await session.commit()


async def resolve_enterprise_context(
    session: AsyncSession,
    workspace_key: str,
    user_email: str,
    request_id: str,
) -> EnterpriseContext:
    workspace_result = await session.execute(
        select(Workspace).where(
            (Workspace.id == workspace_key) | (Workspace.slug == workspace_key)
        )
    )
    workspace = workspace_result.scalar_one_or_none()
    if not workspace or workspace.status != WorkspaceStatus.ACTIVE:
        raise HTTPException(status_code=404, detail="Workspace not found")

    user = await session.scalar(select(User).where(User.email == user_email))
    if not user:
        raise HTTPException(
            status_code=403,
            detail="User is not registered for enterprise access",
        )

    membership = await session.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace.id,
            WorkspaceMembership.user_id == user.id,
        )
    )
    if not membership:
        raise HTTPException(status_code=403, detail="User does not belong to this workspace")

    return EnterpriseContext(
        request_id=request_id,
        workspace=workspace,
        user=user,
        membership=membership,
    )


async def get_enterprise_context(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> EnterpriseContext:
    workspace_key = (
        request.headers.get("X-DataLab-Workspace")
        or request.headers.get("X-DataLab-Workspace-Id")
        or settings.default_workspace_slug
    )
    user_email = request.headers.get("X-DataLab-User-Email") or settings.default_user_email
    request_id = getattr(request.state, "request_id", "unknown")
    return await resolve_enterprise_context(session, workspace_key, user_email, request_id)


def require_role(min_role: WorkspaceRole):
    async def dependency(
        context: EnterpriseContext = Depends(get_enterprise_context),
    ) -> EnterpriseContext:
        if ROLE_LEVELS[context.membership.role] < ROLE_LEVELS[min_role]:
            raise HTTPException(
                status_code=403,
                detail=f"{min_role.value.title()} role or higher is required",
            )
        return context

    return dependency
