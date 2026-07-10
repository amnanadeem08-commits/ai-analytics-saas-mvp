from __future__ import annotations

"""Repository registry — the single seam services use to obtain repositories.

Sprint 8.2 adds configuration-driven backend selection (``STORAGE_BACKEND``):
memory (default) or a SQLAlchemy-backed persistent store. Services are
unaffected because both backends implement the same repository interfaces.
"""

from dataclasses import dataclass, field

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
from backend.repositories.memory import (
    InMemoryAuditRepository,
    InMemoryInvitationRepository,
    InMemoryMembershipRepository,
    InMemoryOrganizationRepository,
    InMemoryPermissionRepository,
    InMemoryRoleAssignmentRepository,
    InMemoryRoleRepository,
    InMemoryWorkspaceRepository,
)


@dataclass
class RepositoryRegistry:
    organizations: OrganizationRepository = field(default_factory=InMemoryOrganizationRepository)
    workspaces: WorkspaceRepository = field(default_factory=InMemoryWorkspaceRepository)
    memberships: MembershipRepository = field(default_factory=InMemoryMembershipRepository)
    roles: RoleRepository = field(default_factory=InMemoryRoleRepository)
    permissions: PermissionRepository = field(default_factory=InMemoryPermissionRepository)
    role_assignments: RoleAssignmentRepository = field(default_factory=InMemoryRoleAssignmentRepository)
    invitations: InvitationRepository = field(default_factory=InMemoryInvitationRepository)
    audit: AuditRepository = field(default_factory=InMemoryAuditRepository)
    backend: str = "memory"


_REGISTRY: RepositoryRegistry | None = None


def build_memory_registry() -> RepositoryRegistry:
    registry = RepositoryRegistry(backend="memory")
    _seed_rbac_defaults(registry)
    return registry


def build_sqlalchemy_registry() -> RepositoryRegistry:
    """Build a persistent registry backed by SQLAlchemy repositories."""
    from backend.database.database import init_database
    from backend.repositories.sqlalchemy import build_sqlalchemy_repositories

    init_database()
    repos = build_sqlalchemy_repositories()
    registry = RepositoryRegistry(
        organizations=repos["organizations"],
        workspaces=repos["workspaces"],
        memberships=repos["memberships"],
        roles=repos["roles"],
        permissions=repos["permissions"],
        role_assignments=repos["role_assignments"],
        invitations=repos["invitations"],
        audit=repos["audit"],
        backend="postgres",
    )
    _seed_rbac_defaults(registry)
    return registry


def _build_from_config() -> RepositoryRegistry:
    from backend.database.config import get_database_config

    config = get_database_config()
    if config.uses_database:
        return build_sqlalchemy_registry()
    return build_memory_registry()


def get_repositories() -> RepositoryRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _build_from_config()
    return _REGISTRY


def set_repositories(registry: RepositoryRegistry) -> RepositoryRegistry:
    global _REGISTRY
    _REGISTRY = registry
    return _REGISTRY


def reset_repositories(*, backend: str | None = None) -> RepositoryRegistry:
    """Test helper — fresh registry seeded with default RBAC.

    ``backend`` overrides the configured backend ("memory" or "postgres").
    """
    global _REGISTRY
    if backend == "memory":
        _REGISTRY = build_memory_registry()
    elif backend in {"postgres", "postgresql", "sqlite", "database"}:
        _REGISTRY = build_sqlalchemy_registry()
    else:
        _REGISTRY = _build_from_config()
    return _REGISTRY


def _seed_rbac_defaults(registry: RepositoryRegistry) -> None:
    # Deferred import avoids a cycle (rbac_service imports the registry).
    from backend.services.rbac_service import seed_default_roles_and_permissions

    seed_default_roles_and_permissions(registry)
