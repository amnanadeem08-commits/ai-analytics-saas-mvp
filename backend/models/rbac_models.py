from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

RBAC_SCHEMA_VERSION = "1.0.0"


class PermissionScope(str, Enum):
    system = "system"
    organization = "organization"
    workspace = "workspace"


class PermissionEffect(str, Enum):
    allow = "allow"
    deny = "deny"


class Permission(BaseModel):
    """A single named permission, e.g. ``workspace:create``."""

    model_config = ConfigDict(extra="allow")

    permission_id: str
    name: str = ""
    description: str = ""
    scope: PermissionScope = PermissionScope.organization
    category: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class Role(BaseModel):
    """A role groups permissions and may inherit other roles.

    ``denied_permissions`` provides explicit deny that overrides grants within
    the same scope evaluation.
    """

    model_config = ConfigDict(extra="allow")

    role_id: str
    name: str = ""
    description: str = ""
    scope: PermissionScope = PermissionScope.organization
    permissions: list[str] = Field(default_factory=list)
    denied_permissions: list[str] = Field(default_factory=list)
    inherits: list[str] = Field(default_factory=list)
    is_system: bool = False
    priority: int = 0
    created_at: str = ""
    updated_at: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class RoleAssignment(BaseModel):
    """Binds a user to a role within a scope (system/org/workspace)."""

    model_config = ConfigDict(extra="allow")

    assignment_id: str
    user_id: str
    role_id: str
    scope: PermissionScope = PermissionScope.organization
    organization_id: str = ""
    workspace_id: str = ""
    granted_by: str = ""
    created_at: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class AccessDecision(BaseModel):
    """Result of a permission evaluation."""

    model_config = ConfigDict(extra="allow")

    allowed: bool = False
    permission: str = ""
    user_id: str = ""
    scope: PermissionScope = PermissionScope.organization
    organization_id: str = ""
    workspace_id: str = ""
    reason: str = ""
    matched_role: str = ""
    decisive_scope: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class PermissionEvaluation(BaseModel):
    """Detailed trace of how a decision was reached (for debugging/audit)."""

    model_config = ConfigDict(extra="allow")

    permission: str
    user_id: str = ""
    allowed: bool = False
    reason: str = ""
    workspace_decision: str = "none"  # allow | deny | none
    organization_decision: str = "none"
    system_decision: str = "none"
    roles_considered: list[str] = Field(default_factory=list)
    allowed_permissions: list[str] = Field(default_factory=list)
    denied_permissions: list[str] = Field(default_factory=list)
    decision: AccessDecision | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
