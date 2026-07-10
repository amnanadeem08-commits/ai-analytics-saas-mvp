from __future__ import annotations

from backend.models.organization_models import (
    Invitation,
    Organization,
    OrganizationMember,
    Workspace,
)
from backend.models.rbac_models import Permission, Role, RoleAssignment
from backend.models.user_models import AuthAuditEvent
from backend.repositories.sqlalchemy import (
    SQLAlchemyAuditRepository,
    SQLAlchemyInvitationRepository,
    SQLAlchemyMembershipRepository,
    SQLAlchemyOrganizationRepository,
    SQLAlchemyPermissionRepository,
    SQLAlchemyRoleAssignmentRepository,
    SQLAlchemyRoleRepository,
    SQLAlchemyWorkspaceRepository,
)
from tests.repositories_sqlalchemy._helpers import teardown_sqlite, use_sqlite_memory


def setup_function():
    use_sqlite_memory()


def teardown_function():
    teardown_sqlite()


def test_organization_repository_crud_and_slug():
    repo = SQLAlchemyOrganizationRepository()
    repo.add(Organization(organization_id="o1", name="Acme", slug="acme", owner_id="u1", created_at="t"))
    assert repo.get("o1").name == "Acme"
    assert repo.get_by_slug("acme").organization_id == "o1"
    org = repo.get("o1")
    org.name = "Acme2"
    repo.update(org)
    assert repo.get("o1").name == "Acme2"
    assert len(repo.list(owner_id="u1")) == 1
    assert repo.delete("o1") is True
    assert repo.get("o1") is None


def test_workspace_repository_isolation_and_archive_filter():
    repo = SQLAlchemyWorkspaceRepository()
    repo.add(Workspace(workspace_id="w1", organization_id="o1", name="W1", status="active", created_at="t"))
    repo.add(Workspace(workspace_id="w2", organization_id="o2", name="W2", status="archived", created_at="t"))
    assert len(repo.list(organization_id="o1")) == 1
    assert len(repo.list(include_archived=False)) == 1


def test_membership_repository_find():
    repo = SQLAlchemyMembershipRepository()
    repo.add(OrganizationMember(member_id="m1", organization_id="o1", user_id="u1", created_at="t"))
    assert repo.find(organization_id="o1", user_id="u1").member_id == "m1"
    assert repo.find(organization_id="o1", user_id="nope") is None


def test_role_and_permission_repositories():
    roles = SQLAlchemyRoleRepository()
    roles.add(Role(role_id="r1", name="Role1"))
    assert roles.get("r1").name == "Role1"
    perms = SQLAlchemyPermissionRepository()
    perms.add(Permission(permission_id="p:read", name="p:read"))
    assert perms.get("p:read") is not None
    assert len(perms.list()) == 1


def test_role_assignment_repository_filters():
    repo = SQLAlchemyRoleAssignmentRepository()
    repo.add(RoleAssignment(assignment_id="a1", user_id="u1", role_id="member", organization_id="o1"))
    repo.add(RoleAssignment(assignment_id="a2", user_id="u1", role_id="viewer", workspace_id="w1"))
    assert len(repo.list(user_id="u1")) == 2
    assert len(repo.list(organization_id="o1")) == 1
    assert len(repo.list(workspace_id="w1")) == 1
    assert repo.delete("a1") is True
    assert len(repo.list(user_id="u1")) == 1


def test_invitation_token_lookup():
    repo = SQLAlchemyInvitationRepository()
    repo.add(Invitation(invitation_id="i1", organization_id="o1", email="a@b.com", token_hash="h1", created_at="t"))
    assert repo.find_by_token_hash("h1").invitation_id == "i1"
    assert repo.find_by_token_hash("missing") is None


def test_audit_repository_filters_and_limit():
    repo = SQLAlchemyAuditRepository()
    for i in range(5):
        repo.add(AuthAuditEvent(event_id=f"e{i}", event_type="login" if i % 2 == 0 else "logout", timestamp=f"t{i}"))
    assert len(repo.list(event_type="login")) == 3
    assert len(repo.list(limit=2)) == 2


def test_round_trip_preserves_full_domain_object():
    repo = SQLAlchemyOrganizationRepository()
    org = Organization(
        organization_id="o_full",
        name="Full",
        slug="full",
        owner_id="u1",
        created_at="t",
        metadata={"tier": "pro", "nested": {"a": 1}},
    )
    repo.add(org)
    loaded = repo.get("o_full")
    assert loaded.metadata == {"tier": "pro", "nested": {"a": 1}}
    assert loaded.settings.default_role_id == org.settings.default_role_id
