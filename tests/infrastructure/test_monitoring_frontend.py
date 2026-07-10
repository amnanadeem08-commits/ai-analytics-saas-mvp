from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import MagicMock, patch

from frontend.api.base import ApiClient
from frontend.api.monitoring_client import MonitoringClient

FRONTEND_FILES = [
    "frontend/api/monitoring_client.py",
    "frontend/app_pages/system_health_page.py",
    "frontend/app_pages/metrics_dashboard_page.py",
    "frontend/app_pages/application_status_page.py",
    "frontend/app_pages/dependency_status_page.py",
    "frontend/app_pages/configuration_viewer_page.py",
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


def test_monitoring_frontend_has_no_backend_imports():
    root = Path(".")
    for rel in FRONTEND_FILES:
        path = root / rel
        assert path.exists(), f"Missing {rel}"
        assert _imports_backend(path) == [], f"{rel} imports backend modules"


@patch("frontend.api.base.requests.request")
def test_monitoring_client_paths(mock_request):
    response = MagicMock()
    response.status_code = 200
    response.content = b'{"success": true}'
    response.json.return_value = {"success": True}
    mock_request.return_value = response

    api = ApiClient(base_url="http://example.test")
    mon = MonitoringClient(api)
    mon.live()
    mon.ready()
    mon.health()
    mon.metrics()
    mon.system_status()
    mon.system_config()
    mon.dependencies()

    paths = [c.args[1] for c in mock_request.call_args_list]
    assert any(p.endswith("/api/v1/live") for p in paths)
    assert any(p.endswith("/api/v1/metrics") for p in paths)
    assert any(p.endswith("/api/v1/system/config") for p in paths)
