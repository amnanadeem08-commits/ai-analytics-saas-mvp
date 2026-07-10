from __future__ import annotations

"""SQLAlchemy repository implementations (Sprint 8.2).

Each implementation satisfies the corresponding repository interface exactly,
so services (which depend only on the interfaces) are unaffected.
"""

from typing import Callable

from sqlalchemy.orm import Session

from backend.repositories.sqlalchemy.audit_repository import SQLAlchemyAuditRepository
from backend.repositories.sqlalchemy.organization_repositories import (
    SQLAlchemyInvitationRepository,
    SQLAlchemyMembershipRepository,
    SQLAlchemyOrganizationRepository,
    SQLAlchemyWorkspaceRepository,
)
from backend.repositories.sqlalchemy.rbac_repositories import (
    SQLAlchemyPermissionRepository,
    SQLAlchemyRoleAssignmentRepository,
    SQLAlchemyRoleRepository,
)

__all__ = [
    "SQLAlchemyOrganizationRepository",
    "SQLAlchemyWorkspaceRepository",
    "SQLAlchemyMembershipRepository",
    "SQLAlchemyRoleRepository",
    "SQLAlchemyPermissionRepository",
    "SQLAlchemyRoleAssignmentRepository",
    "SQLAlchemyInvitationRepository",
    "SQLAlchemyAuditRepository",
    "build_sqlalchemy_repositories",
]


def build_sqlalchemy_repositories(*, session_factory: Callable[[], Session] | None = None):
    """Build a set of SQLAlchemy repositories.

    When ``session_factory`` yields a shared session, all repositories operate on
    that single session (atomic scope). Otherwise each repository manages its own
    session per operation.
    """
    shared: Session | None = session_factory() if session_factory is not None else None
    return {
        "organizations": SQLAlchemyOrganizationRepository(session=shared),
        "workspaces": SQLAlchemyWorkspaceRepository(session=shared),
        "memberships": SQLAlchemyMembershipRepository(session=shared),
        "roles": SQLAlchemyRoleRepository(session=shared),
        "permissions": SQLAlchemyPermissionRepository(session=shared),
        "role_assignments": SQLAlchemyRoleAssignmentRepository(session=shared),
        "invitations": SQLAlchemyInvitationRepository(session=shared),
        "audit": SQLAlchemyAuditRepository(session=shared),
    }
