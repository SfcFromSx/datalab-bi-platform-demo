from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class EnterpriseWorkspaceResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: str
    role: str


class EnterpriseUserResponse(BaseModel):
    id: str
    email: str
    display_name: str


class EnterpriseContextResponse(BaseModel):
    request_id: str
    workspace: EnterpriseWorkspaceResponse
    user: EnterpriseUserResponse
    available_workspaces: list[EnterpriseWorkspaceResponse]


class AuditEventResponse(BaseModel):
    id: str
    action: str
    resource_type: str
    resource_id: str | None = None
    status: str
    request_id: str
    actor_email: str | None = None
    details: dict | None = None
    created_at: datetime
