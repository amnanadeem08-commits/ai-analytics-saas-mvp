from __future__ import annotations

import pytest

from backend.repositories.registry import reset_repositories
from backend.services import rbac_service
from backend.services.rbac_service import RBACError


def setup_function():
    reset_repositories()


def test_default_roles_and_permissions_seeded():
    roles = {r.role_id for r in rbac_service.list_roles()}
    assert {"viewer", "member", "admin", "owner"}.issubset(roles)
    perms = {p.permission_id for p in rbac_service.list_permissions()}
    assert "workspace:create" in perms
    assert "organization:delete" in perms


def test_role_inheritance_expands_permissions():
    # admin inherits member -> viewer
    granted, denied, considered = rbac_service._expand_role_permissions("admin")
    assert "workspace:create" in granted  # from member
    assert "organization:read" in granted  # from viewer
    assert "member:remove" in granted  # from admin
    assert "viewer" in considered and "member" in considered


def test_assign_and_evaluate_permission():
    rbac_service.assign_role(
        user_id="u1", role_id="member", scope="organization", organization_id="org_1"
    )
    assert rbac_service.has_permission("u1", "workspace:create", organization_id="org_1") is True
    # member does not have admin-only perms
    assert rbac_service.has_permission("u1", "member:remove", organization_id="org_1") is False


def test_least_privilege_default_deny():
    evaluation = rbac_service.evaluate_access(
        user_id="nobody", permission="workspace:create", organization_id="org_1"
    )
    assert evaluation.allowed is False
    assert "least privilege" in evaluation.reason.lower()


def test_workspace_override_beats_organization():
    # Org grants member (workspace:create); workspace-scope viewer does NOT grant it,
    # but an explicit workspace deny role should override the org grant.
    deny_role = rbac_service.get_role("viewer")
    # Build a custom deny role at workspace scope.
    from backend.models.rbac_models import PermissionScope, Role
    from backend.repositories.registry import get_repositories

    repos = get_repositories()
    repos.roles.add(
        Role(
            role_id="ws_denier",
            name="WS Denier",
            scope=PermissionScope.workspace,
            denied_permissions=["analyst:run"],
        )
    )
    rbac_service.assign_role(user_id="u2", role_id="member", scope="organization", organization_id="org_1")
    assert rbac_service.has_permission("u2", "analyst:run", organization_id="org_1", workspace_id="w1") is True
    rbac_service.assign_role(user_id="u2", role_id="ws_denier", scope="workspace", workspace_id="w1")
    # Workspace-scope explicit deny overrides org allow.
    assert rbac_service.has_permission("u2", "analyst:run", organization_id="org_1", workspace_id="w1") is False


def test_authorize_raises_on_denied():
    with pytest.raises(RBACError) as exc:
        rbac_service.authorize("u3", "organization:delete", organization_id="org_1")
    assert exc.value.status_code == 403


def test_remove_role_revokes_permission():
    assignment = rbac_service.assign_role(
        user_id="u4", role_id="admin", scope="organization", organization_id="org_1"
    )
    assert rbac_service.has_permission("u4", "member:remove", organization_id="org_1") is True
    rbac_service.remove_role(assignment.assignment_id)
    assert rbac_service.has_permission("u4", "member:remove", organization_id="org_1") is False
