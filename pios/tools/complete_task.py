#!/usr/bin/env python3
"""Complete a task: refresh status, append sprint note, print completion report."""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import PIOS, ROOT, git_output, read_text, write_text


def main() -> int:
    parser = argparse.ArgumentParser(description="PIOS task completion workflow")
    parser.add_argument("--summary", required=True, help="What changed")
    parser.add_argument("--skip-refresh", action="store_true")
    parser.add_argument("--skip-arch-check", action="store_true")
    args = parser.parse_args()

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    arch_rc = 0
    if not args.skip_arch_check:
        arch_rc = subprocess.call([sys.executable, str(ROOT / "pios" / "tools" / "arch_check.py")], cwd=ROOT)

    if not args.skip_refresh:
        subprocess.call([sys.executable, str(ROOT / "pios" / "tools" / "refresh_status.py")], cwd=ROOT)

    _append_sprint_entry(args.summary, now)

    status = git_output("status", "--short")
    diffstat = git_output("diff", "--stat")
    recommend = subprocess.run(
        [sys.executable, str(ROOT / "pios" / "tools" / "recommend_sprint.py"), "--quiet"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    rec_text = (recommend.stdout or "").strip() or "(see recommend_sprint.py)"

    report = f"""# Completion Report

## Summary
{args.summary}

## Files created
(see git status untracked)

## Files modified
(see git diff --stat)

## Tests run
(record pytest commands executed in the agent session)

## Validation gates
- arch_check exit code: {arch_rc}
- refresh_status: {"skipped" if args.skip_refresh else "ran"}

## Architecture impact
Document in CURRENT_SPRINT if layers/registries/APIs changed.

## PIOS updates
- PROJECT_STATUS: refreshed
- CURRENT_SPRINT: completion entry appended ({now})
- TECHNICAL_DEBT: update manually if debt changed
- ROADMAP: update manually if scope changed

## Next sprint recommendation
{rec_text}

## Git status
```
{status or "(clean or unavailable)"}
```

## Git diff --stat
```
{diffstat or "(no unstaged diff or unavailable)"}
```

## Stop
Task protocol complete. Do not continue unless a new task is requested.
"""
    out_dir = PIOS / "05_status" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"completion_{stamp}.md"
    write_text(out_path, report)
    print(report)
    print(f"Wrote {out_path.relative_to(ROOT)}")
    return arch_rc


def _append_sprint_entry(summary: str, now: str) -> None:
    path = PIOS / "04_sprints" / "CURRENT_SPRINT.md"
    text = read_text(path) if path.exists() else "# Current Sprint\n"
    entry = f"\n## Completion entry — {now}\n\n- Summary: {summary}\n"
    write_text(path, text.rstrip() + "\n\n---\n" + entry)


if __name__ == "__main__":
    sys.exit(main())
