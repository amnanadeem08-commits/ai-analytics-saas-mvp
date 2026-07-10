from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import MagicMock, patch

from frontend.api.base import ApiClient, ApiError
from frontend.api.organization_client import OrganizationClient
from frontend.api.rbac_client import RBACClient
from frontend.api.workspace_client import WorkspaceClient

FRONTEND_FILES = [
    "frontend/api/organization_client.py",
    "frontend/api/workspace_client.py",
    "frontend/api/rbac_client.py",
    "frontend/app_pages/rbac_pages.py",
]


def _imports_backend(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "backend" or alias.name.startswith("backend."):
                    hits.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod == "backend" or mod.startswith("backend."):
                hits.append(mod)
    return hits


def test_frontend_rbac_files_have_no_backend_imports():
    root = Path(".")
    for rel in FRONTEND_FILES:
        path = root / rel
        assert path.exists(), f"Missing {rel}"
        assert _imports_backend(path) == [], f"{rel} imports backend modules"


@patch("frontend.api.base.requests.request")
def test_organization_client_paths_and_bearer(mock_request):
    response = MagicMock()
    response.status_code = 200
    response.content = b'{"success": true}'
    response.json.return_value = {"success": True}
    mock_request.return_value = response

    api = ApiClient(base_url="http://example.test")
    OrganizationClient(api).create("tok", "Acme")
    WorkspaceClient(api).create("tok", "org_1", "WS")
    RBACClient(api).assign_role("tok", user_id="u1", role_id="member", organization_id="org_1")

    calls = mock_request.call_args_list
    paths = [c.args[1] for c in calls]
    assert any(p.endswith("/api/v1/organizations") for p in paths)
    assert any(p.endswith("/api/v1/workspaces") for p in paths)
    assert any(p.endswith("/api/v1/roles/assign") for p in paths)
    # All carry the bearer header
    for c in calls:
        assert c.kwargs["headers"]["Authorization"] == "Bearer tok"


@patch("frontend.api.base.requests.request")
def test_rbac_client_check_access_uses_query(mock_request):
    response = MagicMock()
    response.status_code = 200
    response.content = b'{"success": true, "evaluation": {"allowed": true}}'
    response.json.return_value = {"success": True, "evaluation": {"allowed": True}}
    mock_request.return_value = response

    api = ApiClient(base_url="http://example.test")
    RBACClient(api).check_access("tok", permission="workspace:create", organization_id="org_1")
    _args, kwargs = mock_request.call_args
    assert kwargs["params"]["permission"] == "workspace:create"


@patch("frontend.api.base.requests.request")
def test_client_surfaces_structured_error(mock_request):
    response = MagicMock()
    response.status_code = 403
    response.content = b'{"success": false, "error": "Permission denied: workspace:create"}'
    response.json.return_value = {"success": False, "error": "Permission denied: workspace:create"}
    mock_request.return_value = response

    api = ApiClient(base_url="http://example.test")
    try:
        WorkspaceClient(api).create("tok", "org_1", "WS")
        assert False, "expected ApiError"
    except ApiError as exc:
        assert exc.status_code == 403
        assert "Permission denied" in str(exc)
