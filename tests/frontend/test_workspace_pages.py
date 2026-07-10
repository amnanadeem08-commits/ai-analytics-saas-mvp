from __future__ import annotations

import ast
from pathlib import Path

WORKSPACE_PAGES = [
    "frontend/app_pages/ai_analyst_workspace_page.py",
    "frontend/app_pages/dataset_manager_page.py",
    "frontend/app_pages/workflow_monitor_page.py",
    "frontend/app_pages/knowledge_center_page.py",
    "frontend/app_pages/evaluation_dashboard_page.py",
    "frontend/app_pages/session_history_page.py",
]

API_CLIENT_DIR = Path("frontend/api")


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


def test_workspace_pages_do_not_import_backend_services():
    root = Path(".")
    for rel in WORKSPACE_PAGES:
        path = root / rel
        assert path.exists(), f"Missing page: {rel}"
        hits = _imports_backend(path)
        assert hits == [], f"{rel} imports backend modules: {hits}"


def test_frontend_api_clients_do_not_import_backend_services():
    for path in API_CLIENT_DIR.rglob("*.py"):
        hits = _imports_backend(path)
        assert hits == [], f"{path} imports backend modules: {hits}"


def test_workspace_pages_are_importable():
    from frontend.app_pages.ai_analyst_workspace_page import render_ai_analyst_workspace
    from frontend.app_pages.dataset_manager_page import render_dataset_manager
    from frontend.app_pages.evaluation_dashboard_page import render_evaluation_dashboard
    from frontend.app_pages.knowledge_center_page import render_knowledge_center
    from frontend.app_pages.session_history_page import render_session_history
    from frontend.app_pages.workflow_monitor_page import render_workflow_monitor

    assert callable(render_ai_analyst_workspace)
    assert callable(render_dataset_manager)
    assert callable(render_workflow_monitor)
    assert callable(render_knowledge_center)
    assert callable(render_evaluation_dashboard)
    assert callable(render_session_history)
