from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.enterprise import EnterpriseContext, require_role
from app.models import AuditEvent, WorkspaceMembership, WorkspaceRole
from app.schemas import AuditEventResponse, EnterpriseContextResponse

router = APIRouter(tags=["enterprise"])


@router.get(
    "/enterprise/context",
    response_model=EnterpriseContextResponse,
)
async def get_context(
    context: EnterpriseContext = Depends(require_role(WorkspaceRole.VIEWER)),
    session: AsyncSession = Depends(get_session),
):
    memberships = (
        await session.execute(
            select(WorkspaceMembership)
            .where(WorkspaceMembership.user_id == context.user.id)
            .order_by(WorkspaceMembership.created_at)
        )
    ).scalars().all()

    available_workspaces = [
        {
            "id": membership.workspace.id,
            "name": membership.workspace.name,
            "slug": membership.workspace.slug,
            "description": membership.workspace.description,
            "role": membership.role.value,
        }
        for membership in memberships
    ]

    return EnterpriseContextResponse(
        request_id=context.request_id,
        workspace={
            "id": context.workspace.id,
            "name": context.workspace.name,
            "slug": context.workspace.slug,
            "description": context.workspace.description,
            "role": context.membership.role.value,
        },
        user={
            "id": context.user.id,
            "email": context.user.email,
            "display_name": context.user.display_name,
        },
        available_workspaces=available_workspaces,
    )


@router.get(
    "/enterprise/audit-events",
    response_model=list[AuditEventResponse],
)
async def list_audit_events(
    limit: int = 50,
    context: EnterpriseContext = Depends(require_role(WorkspaceRole.ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(AuditEvent)
        .where(AuditEvent.workspace_id == context.workspace.id)
        .order_by(AuditEvent.created_at.desc())
        .limit(min(limit, 200))
    )
    events = result.scalars().all()
    return [
        AuditEventResponse(
            id=event.id,
            action=event.action,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
            status=event.status.value,
            request_id=event.request_id,
            actor_email=event.actor.email if event.actor else None,
            details=event.details,
            created_at=event.created_at,
        )
        for event in events
    ]
