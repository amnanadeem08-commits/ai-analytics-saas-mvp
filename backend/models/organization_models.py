from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

ORGANIZATION_SCHEMA_VERSION = "1.0.0"

ORGANIZATION_FUTURE_EXTENSION_KEYS: tuple[str, ...] = (
    "persistence",
    "billing",
    "api_keys",
    "sso",
    "multi_database_tenancy",
)


def empty_organization_future_extensions() -> dict[str, dict[str, Any]]:
    return {key: {} for key in ORGANIZATION_FUTURE_EXTENSION_KEYS}


class OrganizationStatus(str, Enum):
    active = "active"
    archived = "archived"
    suspended = "suspended"


class WorkspaceStatus(str, Enum):
    active = "active"
    archived = "archived"


class MembershipStatus(str, Enum):
    active = "active"
    invited = "invited"
    pending = "pending"
    removed = "removed"


class InvitationStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    declined = "declined"
    revoked = "revoked"
    expired = "expired"


class OrganizationSettings(BaseModel):
    model_config = ConfigDict(extra="allow")

    default_role_id: str = "member"
    allow_member_workspace_create: bool = True
    require_email_verification: bool = False
    max_workspaces: int = 100
    max_members: int = 500
    preferences: dict[str, Any] = Field(default_factory=dict)


class WorkspaceMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")

    description: str = ""
    color: str = ""
    icon: str = ""
    tags: list[str] = Field(default_factory=list)
    custom: dict[str, Any] = Field(default_factory=dict)


class Organization(BaseModel):
    model_config = ConfigDict(extra="allow")

    organization_id: str
    name: str
    slug: str = ""
    owner_id: str
    status: OrganizationStatus = OrganizationStatus.active
    settings: OrganizationSettings = Field(default_factory=OrganizationSettings)
    created_at: str = ""
    updated_at: str = ""
    archived_at: str = ""
    schema_version: str = ORGANIZATION_SCHEMA_VERSION
    metadata: dict[str, Any] = Field(default_factory=dict)


class Workspace(BaseModel):
    model_config = ConfigDict(extra="allow")

    workspace_id: str
    organization_id: str
    name: str
    slug: str = ""
    status: WorkspaceStatus = WorkspaceStatus.active
    created_by: str = ""
    workspace_metadata: WorkspaceMetadata = Field(default_factory=WorkspaceMetadata)
    created_at: str = ""
    updated_at: str = ""
    archived_at: str = ""
    schema_version: str = ORGANIZATION_SCHEMA_VERSION
    metadata: dict[str, Any] = Field(default_factory=dict)


class OrganizationMember(BaseModel):
    model_config = ConfigDict(extra="allow")

    member_id: str
    organization_id: str
    user_id: str
    email: str = ""
    role_id: str = "member"
    status: MembershipStatus = MembershipStatus.active
    invited_by: str = ""
    joined_at: str = ""
    created_at: str = ""
    updated_at: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class Invitation(BaseModel):
    model_config = ConfigDict(extra="allow")

    invitation_id: str
    organization_id: str
    email: str
    role_id: str = "member"
    status: InvitationStatus = InvitationStatus.pending
    invited_by: str = ""
    token_hash: str = Field(default="", repr=False)
    created_at: str = ""
    expires_at: str = ""
    responded_at: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
