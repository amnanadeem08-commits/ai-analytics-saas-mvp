from __future__ import annotations

from types import SimpleNamespace

from backend.api import auth_dependencies


def _fake_request(*, path_params=None, query_params=None, headers=None):
    return SimpleNamespace(
        path_params=path_params or {},
        query_params=query_params or {},
        headers=headers or {},
    )


def test_current_organization_resolution_order():
    # explicit arg wins
    req = _fake_request(query_params={"organization_id": "q"}, headers={"x-organization-id": "h"})
    assert auth_dependencies.current_organization(req, "explicit") == "explicit"
    # path param next
    req2 = _fake_request(path_params={"organization_id": "p"}, query_params={"organization_id": "q"})
    assert auth_dependencies.current_organization(req2) == "p"
    # query next
    req3 = _fake_request(query_params={"organization_id": "q"})
    assert auth_dependencies.current_organization(req3) == "q"
    # header fallback
    req4 = _fake_request(headers={"x-organization-id": "h"})
    assert auth_dependencies.current_organization(req4) == "h"
    # empty
    assert auth_dependencies.current_organization(_fake_request()) == ""


def test_current_workspace_resolution_order():
    req = _fake_request(path_params={"workspace_id": "p"}, headers={"x-workspace-id": "h"})
    assert auth_dependencies.current_workspace(req) == "p"
    req2 = _fake_request(headers={"x-workspace-id": "h"})
    assert auth_dependencies.current_workspace(req2) == "h"
    assert auth_dependencies.current_workspace(_fake_request()) == ""


def test_require_permission_and_require_role_are_dependency_factories():
    dep = auth_dependencies.require_permission("workspace:create")
    role_dep = auth_dependencies.require_role("admin")
    assert callable(dep)
    assert callable(role_dep)
