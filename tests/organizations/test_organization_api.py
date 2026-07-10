from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app
from backend.repositories.registry import reset_repositories
from backend.security.security_config import reset_security_config
from backend.services.auth_service import reset_auth_store

STRONG = "Str0ngPass"
client = TestClient(app)


def setup_function():
    reset_security_config()
    reset_auth_store()
    reset_repositories()


def _user(email: str) -> dict[str, str]:
    client.post("/api/v1/auth/register", json={"email": email, "password": STRONG})
    token = client.post("/api/v1/auth/login", json={"email": email, "password": STRONG}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_organization_endpoints_require_auth():
    resp = client.post("/api/v1/organizations", json={"name": "Acme"})
    assert resp.status_code == 401


def test_full_org_workspace_rbac_flow():
    owner = _user("owner@x.com")
    created = client.post("/api/v1/organizations", json={"name": "Acme"}, headers=owner)
    assert created.status_code == 201
    org_id = created.json()["organization"]["organization_id"]

    # Owner lists and reads.
    listed = client.get("/api/v1/organizations", headers=owner)
    assert listed.status_code == 200
    assert listed.json()["count"] == 1
    got = client.get(f"/api/v1/organizations/{org_id}", headers=owner)
    assert got.status_code == 200

    # Owner creates a workspace.
    ws = client.post(
        "/api/v1/workspaces", json={"organization_id": org_id, "name": "WS1"}, headers=owner
    )
    assert ws.status_code == 201

    # Roles + permissions listing.
    assert client.get("/api/v1/roles", headers=owner).json()["count"] >= 4
    assert client.get("/api/v1/permissions", headers=owner).json()["count"] >= 5

    # Owner access check passes.
    check = client.get(
        "/api/v1/access/check",
        params={"permission": "workspace:create", "organization_id": org_id},
        headers=owner,
    )
    assert check.json()["evaluation"]["allowed"] is True


def test_permission_denied_for_viewer():
    owner = _user("owner2@x.com")
    org_id = client.post("/api/v1/organizations", json={"name": "Acme2"}, headers=owner).json()["organization"]["organization_id"]

    invite = client.post(
        f"/api/v1/organizations/{org_id}/invite",
        json={"email": "viewer@x.com", "role_id": "viewer"},
        headers=owner,
    )
    invite_token = invite.json()["invitation_token"]

    viewer = _user("viewer@x.com")
    accept = client.post("/api/v1/organizations/invitations/accept", json={"token": invite_token}, headers=viewer)
    assert accept.status_code == 200

    # Viewer cannot create workspaces (403).
    denied = client.post(
        "/api/v1/workspaces", json={"organization_id": org_id, "name": "WS-x"}, headers=viewer
    )
    assert denied.status_code == 403
    assert denied.json()["success"] is False

    # Viewer cannot invite members (403).
    denied_invite = client.post(
        f"/api/v1/organizations/{org_id}/invite",
        json={"email": "z@x.com", "role_id": "member"},
        headers=viewer,
    )
    assert denied_invite.status_code == 403


def test_workspace_isolation_between_orgs():
    owner_a = _user("a@x.com")
    owner_b = _user("b@x.com")
    org_a = client.post("/api/v1/organizations", json={"name": "OrgA"}, headers=owner_a).json()["organization"]["organization_id"]
    org_b = client.post("/api/v1/organizations", json={"name": "OrgB"}, headers=owner_b).json()["organization"]["organization_id"]
    client.post("/api/v1/workspaces", json={"organization_id": org_a, "name": "WA"}, headers=owner_a)

    # Owner B cannot read workspaces in Org A (no permission there → 403).
    resp = client.get("/api/v1/workspaces", params={"organization_id": org_a}, headers=owner_b)
    assert resp.status_code == 403

    # Owner A only sees their own org's workspaces.
    own = client.get("/api/v1/workspaces", params={"organization_id": org_a}, headers=owner_a)
    assert own.status_code == 200
    assert own.json()["count"] == 1


def test_role_assignment_via_api():
    owner = _user("owner3@x.com")
    org_id = client.post("/api/v1/organizations", json={"name": "Acme3"}, headers=owner).json()["organization"]["organization_id"]
    # Invite + accept a member.
    invite = client.post(
        f"/api/v1/organizations/{org_id}/invite", json={"email": "m3@x.com", "role_id": "viewer"}, headers=owner
    )
    member = _user("m3@x.com")
    client.post("/api/v1/organizations/invitations/accept", json={"token": invite.json()["invitation_token"]}, headers=member)

    me = client.get("/api/v1/auth/me", headers=member).json()["user"]["user_id"]
    # Owner promotes the member to admin.
    assign = client.post(
        "/api/v1/roles/assign",
        json={"user_id": me, "role_id": "admin", "scope": "organization", "organization_id": org_id},
        headers=owner,
    )
    assert assign.status_code == 200
    # Member now has admin permission.
    check = client.get(
        "/api/v1/access/check",
        params={"permission": "member:remove", "organization_id": org_id},
        headers=member,
    )
    assert check.json()["evaluation"]["allowed"] is True


def test_openapi_includes_new_routes():
    schema = client.get("/openapi.json").json()
    paths = schema.get("paths") or {}
    assert "/api/v1/organizations" in paths
    assert "/api/v1/workspaces" in paths
    assert "/api/v1/roles" in paths
    assert "/api/v1/access/check" in paths
