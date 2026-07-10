from __future__ import annotations

"""Dependency audit helper (Sprint 8.7)."""

import re
from pathlib import Path
from typing import Any


def _requirements_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    for name in ("requirements.txt", "requirements-prod.txt"):
        path = root / name
        if path.exists():
            return path
    return root / "requirements.txt"


def parse_requirements() -> list[dict[str, str]]:
    path = _requirements_path()
    if not path.exists():
        return []
    packages: list[dict[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"^([A-Za-z0-9_.-]+)([=<>!~]+.*)?$", line.split("[", 1)[0])
        if match:
            packages.append({"name": match.group(1), "spec": (match.group(2) or "").strip()})
    return packages


def audit_dependencies() -> dict[str, Any]:
    packages = parse_requirements()
    issues: list[str] = []
    if not packages:
        issues.append("No requirements file found or file is empty")
    pinned = [p for p in packages if p.get("spec", "").startswith("==")]
    if packages and len(pinned) < len(packages) * 0.5:
        issues.append("Fewer than 50% of dependencies are exactly pinned")
    return {
        "requirements_file": str(_requirements_path()),
        "package_count": len(packages),
        "pinned_count": len(pinned),
        "issues": issues,
        "packages": packages[:50],
    }
