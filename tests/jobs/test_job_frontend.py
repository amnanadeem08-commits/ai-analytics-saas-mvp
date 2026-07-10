from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import MagicMock, patch

from frontend.api.base import ApiClient, ApiError
from frontend.api.job_client import JobClient

FRONTEND_FILES = [
    "frontend/api/job_client.py",
    "frontend/app_pages/job_monitor_page.py",
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


def test_job_frontend_has_no_backend_imports():
    root = Path(".")
    for rel in FRONTEND_FILES:
        path = root / rel
        assert path.exists(), f"Missing {rel}"
        assert _imports_backend(path) == [], f"{rel} imports backend modules"


@patch("frontend.api.base.requests.request")
def test_job_client_paths_and_bearer(mock_request):
    response = MagicMock()
    response.status_code = 200
    response.content = b'{"success": true}'
    response.json.return_value = {"success": True}
    mock_request.return_value = response

    api = ApiClient(base_url="http://example.test")
    jobs = JobClient(api)
    jobs.submit("tok", job_type="generic", payload={"echo": "x"}, inline=True)
    jobs.statistics("tok")
    jobs.get("tok", "job_1")
    jobs.cancel("tok", "job_1")
    jobs.retry("tok", "job_1", inline=True)

    paths = [c.args[1] for c in mock_request.call_args_list]
    assert any(p.endswith("/api/v1/jobs") for p in paths)
    assert any(p.endswith("/api/v1/jobs/statistics") for p in paths)
    assert any(p.endswith("/api/v1/jobs/job_1") for p in paths)
    assert any(p.endswith("/api/v1/jobs/job_1/retry") for p in paths)
    for c in mock_request.call_args_list:
        assert c.kwargs["headers"]["Authorization"] == "Bearer tok"


@patch("frontend.api.base.requests.request")
def test_job_client_surfaces_structured_error(mock_request):
    response = MagicMock()
    response.status_code = 409
    response.content = b'{"success": false, "error": "Job already succeeded; cannot cancel"}'
    response.json.return_value = {"success": False, "error": "Job already succeeded; cannot cancel"}
    mock_request.return_value = response

    api = ApiClient(base_url="http://example.test")
    try:
        JobClient(api).cancel("tok", "job_1")
        assert False, "expected ApiError"
    except ApiError as exc:
        assert exc.status_code == 409
        assert "cannot cancel" in str(exc)
