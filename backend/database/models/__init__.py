from __future__ import annotations

"""SQLAlchemy ORM models (Sprint 8.2).

Design: each table carries indexed identity/filter columns for querying plus a
portable JSON ``data`` payload holding the full domain object. This guarantees
exact round-trip fidelity with the Pydantic domain models (which remain the
source of truth) while keeping key fields queryable.

ORM models are intentionally separate from the Pydantic domain models and are
never imported by services.
"""

from backend.database.models.auth import (
    EmailVerificationORM,
    PasswordResetRequestORM,
    RefreshTokenORM,
    UserORM,
    UserProfileORM,
    UserSessionORM,
)
from backend.database.models.audit import AuthAuditEventORM
from backend.database.models.knowledge import KnowledgeChunkORM, KnowledgeDocumentORM
from backend.database.models.organization import (
    InvitationORM,
    OrganizationMemberORM,
    OrganizationORM,
    WorkspaceORM,
)
from backend.database.models.rbac import PermissionORM, RoleAssignmentORM, RoleORM
from backend.database.models.runtime import (
    AnalystSessionORM,
    EvaluationRunORM,
    WorkflowExecutionORM,
)

__all__ = [
    "UserORM",
    "UserProfileORM",
    "UserSessionORM",
    "RefreshTokenORM",
    "PasswordResetRequestORM",
    "EmailVerificationORM",
    "OrganizationORM",
    "WorkspaceORM",
    "OrganizationMemberORM",
    "InvitationORM",
    "RoleORM",
    "PermissionORM",
    "RoleAssignmentORM",
    "AuthAuditEventORM",
    "WorkflowExecutionORM",
    "EvaluationRunORM",
    "AnalystSessionORM",
    "KnowledgeDocumentORM",
    "KnowledgeChunkORM",
]
