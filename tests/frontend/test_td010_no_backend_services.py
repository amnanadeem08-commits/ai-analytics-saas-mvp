from __future__ import annotations

"""TD-010 — frontend must not import backend.services."""

from pathlib import Path

from pios.tools.arch_check import main as arch_check_main


def test_ai_insights_page_has_no_backend_services_import():
    path = Path("frontend/app_pages/ai_insights_page.py")
    text = path.read_text(encoding="utf-8")
    assert "backend.services" not in text
    assert "backend.analytics" in text


def test_arch_check_passes_fe_no_backend_services(monkeypatch, capsys):
    # Ensure the previously failing rule is green for the whole frontend tree.
    code = arch_check_main()
    captured = capsys.readouterr().out
    assert "FAIL FE_NO_BACKEND_SERVICES" not in captured
    # Other rules may still warn; FE_NO_BACKEND_SERVICES must pass.
    assert "PASS FE_NO_BACKEND_SERVICES" in captured or code == 0
