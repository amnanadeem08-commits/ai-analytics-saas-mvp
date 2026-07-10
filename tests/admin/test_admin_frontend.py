from __future__ import annotations

import ast
from pathlib import Path

FRONTEND_FILES = [
    "frontend/api/admin_client.py",
    "frontend/app_pages/admin_dashboard_page.py",
    "frontend/app_pages/system_analytics_page.py",
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


def test_admin_frontend_no_backend_imports():
    for rel in FRONTEND_FILES:
        assert _imports_backend(Path(rel)) == []
