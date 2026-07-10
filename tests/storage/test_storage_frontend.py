from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import MagicMock, patch

from frontend.api.base import ApiClient, ApiError
from frontend.api.storage_client import StorageClient

FRONTEND_FILES = [
    "frontend/api/storage_client.py",
    "frontend/app_pages/storage_manager_page.py",
    "frontend/app_pages/dataset_versions_page.py",
    "frontend/app_pages/artifact_browser_page.py",
    "frontend/app_pages/storage_statistics_page.py",
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


def test_storage_frontend_has_no_backend_imports():
    root = Path(".")
    for rel in FRONTEND_FILES:
        path = root / rel
        assert path.exists(), f"Missing {rel}"
        assert _imports_backend(path) == [], f"{rel} imports backend modules"


@patch("frontend.api.base.requests.request")
def test_storage_client_paths_and_bearer(mock_request):
    response = MagicMock()
    response.status_code = 200
    response.content = b'{"success": true}'
    response.json.return_value = {"success": True}
    mock_request.return_value = response

    api = ApiClient(base_url="http://example.test")
    storage = StorageClient(api)
    storage.upload("tok", filename="a.txt", content=b"x")
    storage.list_files("tok")
    storage.get("tok", "obj_1")
    storage.statistics("tok")
    storage.archive("tok", "obj_1")
    storage.restore("tok", "obj_1")
    storage.delete("tok", "obj_1")
    storage.rollback("tok", "obj_1", version_number=1)

    paths = [c.args[1] for c in mock_request.call_args_list]
    assert any(p.endswith("/api/v1/storage/upload") for p in paths)
    assert any(p.endswith("/api/v1/storage/files") for p in paths)
    assert any(p.endswith("/api/v1/storage/statistics") for p in paths)
    for c in mock_request.call_args_list:
        assert c.kwargs["headers"]["Authorization"] == "Bearer tok"


@patch("frontend.api.base.requests.request")
def test_storage_client_surfaces_structured_error(mock_request):
    response = MagicMock()
    response.status_code = 409
    response.content = b'{"success": false, "error": "Duplicate content detected"}'
    response.json.return_value = {"success": False, "error": "Duplicate content detected"}
    mock_request.return_value = response

    api = ApiClient(base_url="http://example.test")
    try:
        StorageClient(api).upload("tok", filename="a.txt", content=b"x", allow_duplicate=False)
        assert False, "expected ApiError"
    except ApiError as exc:
        assert exc.status_code == 409
        assert "Duplicate" in str(exc)
