from __future__ import annotations

"""Repository layer (Sprint 8.1).

Storage-agnostic interfaces with in-memory implementations. Services depend
only on the interfaces so Sprint 8.2 can swap persistence without changing
business logic. A registry provides the active repository set.
"""

from backend.repositories.interfaces import (
    AuditRepository,
    InvitationRepository,
    MembershipRepository,
    OrganizationRepository,
    PermissionRepository,
    RoleAssignmentRepository,
    RoleRepository,
    WorkspaceRepository,
)
from backend.repositories.registry import (
    RepositoryRegistry,
    get_repositories,
    reset_repositories,
    set_repositories,
)

__all__ = [
    "OrganizationRepository",
    "WorkspaceRepository",
    "MembershipRepository",
    "RoleRepository",
    "PermissionRepository",
    "RoleAssignmentRepository",
    "InvitationRepository",
    "AuditRepository",
    "RepositoryRegistry",
    "get_repositories",
    "set_repositories",
    "reset_repositories",
]
