from __future__ import annotations

from backend.models.organization_models import (
    Invitation,
    Organization,
    OrganizationMember,
    Workspace,
)
from backend.models.rbac_models import Permission, Role, RoleAssignment
from backend.models.user_models import AuthAuditEvent
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


def test_organization_repository_crud():
    repo = InMemoryOrganizationRepository()
    org = Organization(organization_id="org_1", name="Acme", owner_id="u1", slug="acme", created_at="t")
    repo.add(org)
    assert repo.get("org_1").name == "Acme"
    assert repo.get_by_slug("acme").organization_id == "org_1"
    org.name = "Acme2"
    repo.update(org)
    assert repo.get("org_1").name == "Acme2"
    assert len(repo.list()) == 1
    assert repo.delete("org_1") is True
    assert repo.get("org_1") is None


def test_repository_returns_copies_not_references():
    repo = InMemoryOrganizationRepository()
    org = Organization(organization_id="org_1", name="Acme", owner_id="u1", created_at="t")
    repo.add(org)
    fetched = repo.get("org_1")
    fetched.name = "Mutated"
    # Mutating the returned copy must not affect stored state.
    assert repo.get("org_1").name == "Acme"


def test_workspace_repository_filters_by_org():
    repo = InMemoryWorkspaceRepository()
    repo.add(Workspace(workspace_id="w1", organization_id="org_1", name="W1", created_at="t"))
    repo.add(Workspace(workspace_id="w2", organization_id="org_2", name="W2", created_at="t"))
    assert len(repo.list(organization_id="org_1")) == 1


def test_membership_find():
    repo = InMemoryMembershipRepository()
    repo.add(OrganizationMember(member_id="m1", organization_id="org_1", user_id="u1", created_at="t"))
    assert repo.find(organization_id="org_1", user_id="u1").member_id == "m1"
    assert repo.find(organization_id="org_1", user_id="nope") is None


def test_role_and_permission_repositories():
    roles = InMemoryRoleRepository()
    roles.add(Role(role_id="r1", name="Role1"))
    assert roles.get("r1").name == "Role1"
    perms = InMemoryPermissionRepository()
    perms.add(Permission(permission_id="p:read"))
    assert perms.get("p:read") is not None


def test_role_assignment_repository_filters():
    repo = InMemoryRoleAssignmentRepository()
    repo.add(RoleAssignment(assignment_id="a1", user_id="u1", role_id="member", organization_id="org_1"))
    repo.add(RoleAssignment(assignment_id="a2", user_id="u1", role_id="viewer", workspace_id="w1"))
    assert len(repo.list(user_id="u1")) == 2
    assert len(repo.list(user_id="u1", organization_id="org_1")) == 1
    assert len(repo.list(workspace_id="w1")) == 1


def test_invitation_token_lookup():
    repo = InMemoryInvitationRepository()
    repo.add(Invitation(invitation_id="i1", organization_id="org_1", email="a@b.com", token_hash="hash1", created_at="t"))
    assert repo.find_by_token_hash("hash1").invitation_id == "i1"
    assert repo.find_by_token_hash("missing") is None


def test_audit_repository_filters_and_limit():
    repo = InMemoryAuditRepository()
    for i in range(5):
        repo.add(AuthAuditEvent(event_id=f"e{i}", event_type="login" if i % 2 == 0 else "logout"))
    assert len(repo.list(event_type="login")) == 3
    assert len(repo.list(limit=2)) == 2
