from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import MagicMock, patch

from frontend.api.base import ApiClient
from frontend.api.billing_client import BillingClient

FRONTEND_FILES = [
    "frontend/api/billing_client.py",
    "frontend/app_pages/billing_dashboard_page.py",
    "frontend/app_pages/subscription_management_page.py",
]


def _imports_backend(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod == "backend" or mod.startswith("backend."):
                hits.append(mod)
    return hits


def test_billing_frontend_no_backend_imports():
    for rel in FRONTEND_FILES:
        assert _imports_backend(Path(rel)) == [], f"{rel} imports backend"


@patch("frontend.api.base.requests.request")
def test_billing_client_paths(mock_request):
    response = MagicMock()
    response.status_code = 200
    response.content = b'{"success": true}'
    response.json.return_value = {"success": True}
    mock_request.return_value = response

    api = ApiClient(base_url="http://example.test")
    billing = BillingClient(api)
    billing.list_plans("tok")
    billing.assign_plan("tok", "org_1", plan_id="pro")
    paths = [c.args[1] for c in mock_request.call_args_list]
    assert any("/api/v1/billing/plans" in p for p in paths)
