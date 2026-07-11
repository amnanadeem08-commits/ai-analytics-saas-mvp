#!/usr/bin/env python3
"""Run the beta E2E smoke gate against the real sample sales dataset.

Usage (from repo root):

    python scripts/e2e_smoke.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "samples" / "sample_sales_data.csv"


def main() -> int:
    if not SAMPLE.exists():
        print(f"FAIL  missing sample dataset: {SAMPLE}")
        return 1
    print(f"PASS  sample dataset present: {SAMPLE.name}")
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/release/test_e2e_production.py",
        "tests/release/test_release_api.py",
        "-q",
        "--tb=short",
    ]
    print("RUN  ", " ".join(cmd))
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode == 0:
        print("PASSED  E2E smoke gate")
    else:
        print("FAILED  E2E smoke gate")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
