from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.enterprise.auth import EnterpriseContext
from app.models import AuditEvent, AuditEventStatus


async def log_audit_event(
    session: AsyncSession,
    context: EnterpriseContext,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    details: dict[str, Any] | None = None,
    status: AuditEventStatus = AuditEventStatus.SUCCESS,
) -> AuditEvent:
    event = AuditEvent(
        workspace_id=context.workspace.id,
        actor_user_id=context.user.id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        status=status,
        request_id=context.request_id,
        details=details or {},
    )
    session.add(event)
    await session.flush()
    return event
