from __future__ import annotations

"""End-to-end persistence coverage on the SQLAlchemy backend (Sprint 8.2)."""

from backend.repositories.registry import reset_repositories
from tests.repositories_sqlalchemy._helpers import teardown_sqlite, use_sqlite_memory


def setup_function():
    use_sqlite_memory()
    reset_repositories(backend="postgres")


def teardown_function():
    teardown_sqlite()
    reset_repositories(backend="memory")


def test_organization_and_workspace_persistence():
    from backend.services import organization_service, workspace_service

    org = organization_service.create_organization(name="Persist Co", owner_id="owner_1")
    ws = workspace_service.create_workspace(
        organization_id=org.organization_id, name="Persisted WS", created_by="owner_1"
    )

    # Reload through a brand-new registry bound to the same database.
    reset_repositories(backend="postgres")
    reloaded_org = organization_service.get_organization(org.organization_id)
    reloaded_ws = workspace_service.get_workspace(ws.workspace_id)
    assert reloaded_org is not None and reloaded_org.name == "Persist Co"
    assert reloaded_ws is not None and reloaded_ws.name == "Persisted WS"


def test_rbac_and_membership_persistence():
    from backend.services import organization_service, rbac_service

    org = organization_service.create_organization(name="RBAC Co", owner_id="owner_2")
    invite = organization_service.invite_member(
        organization_id=org.organization_id, email="m@x.com", role_id="admin", invited_by="owner_2"
    )
    organization_service.accept_invitation(token=invite["invitation_token"], user_id="user_3")

    reset_repositories(backend="postgres")
    # Membership persisted.
    assert organization_service.get_member(org.organization_id, "user_3") is not None
    # Role assignment persisted -> permission still evaluates.
    assert rbac_service.has_permission("user_3", "member:remove", organization_id=org.organization_id)


def test_audit_persistence():
    from backend.repositories.registry import get_repositories
    from backend.services import organization_service

    organization_service.create_organization(name="Audit Co", owner_id="owner_4")
    reset_repositories(backend="postgres")
    events = get_repositories().audit.list()
    assert any(e.event_type == "organization_created" for e in events)


def test_authentication_and_session_orm_persistence():
    """ORM-level persistence for auth entities (User, UserSession, RefreshToken)."""
    from backend.database.mappers.audit import audit_event_to_orm  # noqa: F401 (ensures mappers import)
    from backend.database.models.auth import RefreshTokenORM, UserORM, UserSessionORM
    from backend.database.session import new_session

    session = new_session()
    session.add(
        UserORM(
            user_id="u_persist",
            email="p@x.com",
            status="active",
            hashed_password="pbkdf2_sha256$1$aa$bb",
            data={"user_id": "u_persist", "email": "p@x.com"},
        )
    )
    session.add(
        UserSessionORM(
            session_id="s_persist", user_id="u_persist", revoked=False, data={"session_id": "s_persist", "user_id": "u_persist"}
        )
    )
    session.add(
        RefreshTokenORM(
            token_id="rt_persist", user_id="u_persist", session_id="s_persist", token_hash="h", data={"token_id": "rt_persist"}
        )
    )
    session.commit()
    session.close()

    verify = new_session()
    assert verify.get(UserORM, "u_persist").email == "p@x.com"
    assert verify.get(UserSessionORM, "s_persist").user_id == "u_persist"
    assert verify.get(RefreshTokenORM, "rt_persist").session_id == "s_persist"
    verify.close()


def test_repository_interface_compatibility():
    """SQLAlchemy repositories satisfy the exact interface types."""
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
    from backend.repositories.registry import get_repositories

    repos = get_repositories()
    assert isinstance(repos.organizations, OrganizationRepository)
    assert isinstance(repos.workspaces, WorkspaceRepository)
    assert isinstance(repos.memberships, MembershipRepository)
    assert isinstance(repos.roles, RoleRepository)
    assert isinstance(repos.permissions, PermissionRepository)
    assert isinstance(repos.role_assignments, RoleAssignmentRepository)
    assert isinstance(repos.invitations, InvitationRepository)
    assert isinstance(repos.audit, AuditRepository)
