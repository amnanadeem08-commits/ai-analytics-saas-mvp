#!/usr/bin/env python3
"""Refresh pios/05_status/PROJECT_STATUS.md from repository facts."""

from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import (
    PIOS,
    ROOT,
    count_files,
    get_api_version,
    list_route_modules,
    read_text,
    write_text,
)


def main() -> None:
    version = get_api_version()
    test_files = count_files("test_*.py", ROOT / "tests")
    services = count_files("*_service.py", ROOT / "backend" / "services")
    routes = list_route_modules()
    sprint = _current_sprint_title()
    known_count = _count_known_issues()
    debt_count = _count_debt_items()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    next_rec = (
        "Finish Phase 0.3 (AI Business Column Suggestions), then prioritize "
        "persistent commercial stores (TD-001/KI-002) or billing gateway (TD-002/KI-001)."
    )

    content = f"""# PROJECT_STATUS

> Auto-maintained by `python pios/tools/refresh_status.py`. Last refresh: {now}

## Snapshot

| Field | Value |
|-------|-------|
| Product | Data Bot AI (AI Analytics SaaS MVP) |
| Current version | `{version}` (from `backend/core/config.py`) |
| Current sprint | {sprint} |
| Git tag | `v1.0.0` |
| Test files (`test_*.py`) | **{test_files}** |
| Route modules | **{len(routes)}** |
| Service modules (`*_service.py`) | **{services}** |
| Known issues | **{known_count}** (see `KNOWN_ISSUES.md`) |
| Technical debt items | **{debt_count}** (see `TECHNICAL_DEBT.md`) |

## Route modules

{chr(10).join(f"- `{name}`" for name in routes) if routes else "- None found"}

## Completed features (v1.0)

- Dataset upload/cleaning/profiling/analytics dashboards
- Charts, pivot, visual builder, SQL Lab, DAX Studio
- Reports (PDF/PPT), storyboard, geospatial insights
- AI Analyst (`/api/v1`), workflows, evaluation, knowledge ingestion
- Auth (JWT), orgs, workspaces, RBAC
- Jobs/queue/workers, object storage lifecycle
- Monitoring, metrics, release validation
- Billing plans/usage/API keys/admin (in-memory commercial stores)

## Remaining roadmap

See [`../01_vision/ROADMAP.md`](../01_vision/ROADMAP.md)

## Next sprint recommendation

{next_rec}

Run `python pios/tools/recommend_sprint.py` for ranked detail.
"""
    out = PIOS / "05_status" / "PROJECT_STATUS.md"
    write_text(out, content)
    print(f"Updated {out.relative_to(ROOT)}")
    print(f"version={version} tests={test_files} routes={len(routes)} services={services}")


def _current_sprint_title() -> str:
    path = PIOS / "04_sprints" / "CURRENT_SPRINT.md"
    if not path.exists():
        return "Unknown"
    first = read_text(path).splitlines()[0]
    return first.lstrip("# ").strip()


def _count_known_issues() -> int:
    text = read_text(PIOS / "05_status" / "KNOWN_ISSUES.md")
    return len(re.findall(r"\|\s*KI-\d+", text))


def _count_debt_items() -> int:
    text = read_text(PIOS / "05_status" / "TECHNICAL_DEBT.md")
    return len(re.findall(r"\|\s*TD-\d+", text))


if __name__ == "__main__":
    main()
