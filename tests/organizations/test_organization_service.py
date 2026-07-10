from __future__ import annotations

import pytest

from backend.repositories.registry import get_repositories, reset_repositories
from backend.services import organization_service, rbac_service, workspace_service
from backend.services.organization_service import OrganizationError
from backend.services.workspace_service import WorkspaceError


def setup_function():
    reset_repositories()


def _org(owner="owner_1", name="Acme"):
    return organization_service.create_organization(name=name, owner_id=owner)


def test_create_organization_grants_owner_role():
    org = _org()
    assert org.owner_id == "owner_1"
    assert org.status.value == "active"
    # Owner implicitly has all permissions.
    assert rbac_service.has_permission("owner_1", "organization:delete", organization_id=org.organization_id)
    members = organization_service.list_members(org.organization_id)
    assert any(m.user_id == "owner_1" and m.role_id == "owner" for m in members)


def test_update_archive_restore_organization():
    org = _org()
    organization_service.update_organization(org.organization_id, name="Acme Corp", actor_id="owner_1")
    assert organization_service.get_organization(org.organization_id).name == "Acme Corp"
    organization_service.archive_organization(org.organization_id, actor_id="owner_1")
    assert organization_service.get_organization(org.organization_id).status.value == "archived"
    organization_service.restore_organization(org.organization_id, actor_id="owner_1")
    assert organization_service.get_organization(org.organization_id).status.value == "active"


def test_invitation_accept_flow_creates_member():
    org = _org()
    result = organization_service.invite_member(
        organization_id=org.organization_id, email="new@x.com", role_id="member", invited_by="owner_1"
    )
    token = result["invitation_token"]
    member = organization_service.accept_invitation(token=token, user_id="user_2", email="new@x.com")
    assert member.user_id == "user_2"
    assert member.status.value == "active"
    assert rbac_service.has_permission("user_2", "workspace:create", organization_id=org.organization_id)


def test_invitation_decline():
    org = _org()
    result = organization_service.invite_member(
        organization_id=org.organization_id, email="d@x.com", invited_by="owner_1"
    )
    out = organization_service.decline_invitation(token=result["invitation_token"], user_id="user_3")
    assert out["declined"] is True
    # Cannot accept a declined invitation.
    with pytest.raises(OrganizationError):
        organization_service.accept_invitation(token=result["invitation_token"], user_id="user_3")


def test_remove_member_revokes_roles():
    org = _org()
    result = organization_service.invite_member(
        organization_id=org.organization_id, email="m@x.com", role_id="admin", invited_by="owner_1"
    )
    organization_service.accept_invitation(token=result["invitation_token"], user_id="user_4")
    assert rbac_service.has_permission("user_4", "member:remove", organization_id=org.organization_id)
    organization_service.remove_member(organization_id=org.organization_id, user_id="user_4", actor_id="owner_1")
    assert rbac_service.has_permission("user_4", "member:remove", organization_id=org.organization_id) is False


def test_cannot_remove_owner():
    org = _org()
    with pytest.raises(OrganizationError) as exc:
        organization_service.remove_member(organization_id=org.organization_id, user_id="owner_1", actor_id="owner_1")
    assert exc.value.status_code == 409


def test_transfer_ownership():
    org = _org()
    result = organization_service.invite_member(
        organization_id=org.organization_id, email="n@x.com", role_id="member", invited_by="owner_1"
    )
    organization_service.accept_invitation(token=result["invitation_token"], user_id="user_5")
    organization_service.transfer_ownership(
        organization_id=org.organization_id, new_owner_id="user_5", actor_id="owner_1"
    )
    updated = organization_service.get_organization(org.organization_id)
    assert updated.owner_id == "user_5"
    assert rbac_service.has_permission("user_5", "organization:delete", organization_id=org.organization_id)


def test_workspace_crud_and_isolation():
    org1 = _org(owner="owner_a", name="OrgA")
    org2 = _org(owner="owner_b", name="OrgB")
    ws1 = workspace_service.create_workspace(organization_id=org1.organization_id, name="WS1", created_by="owner_a")
    workspace_service.create_workspace(organization_id=org2.organization_id, name="WS2", created_by="owner_b")

    # Workspace listing is isolated per organization.
    org1_workspaces = workspace_service.list_workspaces(org1.organization_id)
    assert len(org1_workspaces) == 1
    assert org1_workspaces[0].workspace_id == ws1.workspace_id

    workspace_service.rename_workspace(ws1.workspace_id, name="Renamed", actor_id="owner_a")
    assert workspace_service.get_workspace(ws1.workspace_id).name == "Renamed"
    workspace_service.archive_workspace(ws1.workspace_id, actor_id="owner_a")
    assert workspace_service.get_workspace(ws1.workspace_id).status.value == "archived"
    workspace_service.restore_workspace(ws1.workspace_id, actor_id="owner_a")
    assert workspace_service.get_workspace(ws1.workspace_id).status.value == "active"


def test_workspace_summary_and_members():
    org = _org()
    ws = workspace_service.create_workspace(organization_id=org.organization_id, name="WS", created_by="owner_1")
    summary = workspace_service.workspace_summary(ws.workspace_id)
    assert summary["organization_id"] == org.organization_id
    members = workspace_service.list_workspace_members(ws.workspace_id)
    assert any(m["user_id"] == "owner_1" for m in members)


def test_audit_events_generated():
    org = _org()
    workspace_service.create_workspace(organization_id=org.organization_id, name="WS", created_by="owner_1")
    result = organization_service.invite_member(
        organization_id=org.organization_id, email="a@x.com", invited_by="owner_1"
    )
    organization_service.accept_invitation(token=result["invitation_token"], user_id="user_9")
    events = {e.event_type for e in get_repositories().audit.list()}
    assert "organization_created" in events
    assert "workspace_created" in events
    assert "member_invited" in events
    assert "invitation_accepted" in events
    assert "role_assigned" in events


def test_organization_summary():
    org = _org()
    workspace_service.create_workspace(organization_id=org.organization_id, name="WS", created_by="owner_1")
    summary = organization_service.organization_summary(org.organization_id)
    assert summary["member_count"] == 1
    assert summary["workspace_count"] == 1
