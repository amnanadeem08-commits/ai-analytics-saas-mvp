from __future__ import annotations

"""Secrets validation (Sprint 8.7)."""

import os
from typing import Any


_INSECURE_DEFAULTS = {
    "JWT_SECRET": {"changeme", "secret", "dev", "development"},
    "SECRET_KEY": {"changeme", "secret", "dev", "development"},
}


def validate_secrets() -> dict[str, Any]:
    issues: list[str] = []
    checked: dict[str, str] = {}
    for key in ("JWT_SECRET", "SECRET_KEY", "DATABASE_URL"):
        value = os.getenv(key, "")
        checked[key] = "set" if value else "missing"
        if not value and key != "DATABASE_URL":
            issues.append(f"{key} is not set")
        elif value.lower() in _INSECURE_DEFAULTS.get(key, set()):
            issues.append(f"{key} uses an insecure default value")
        elif key.endswith("SECRET") and len(value) < 32:
            issues.append(f"{key} should be at least 32 characters")
    return {"checked": checked, "issues": issues, "ok": len(issues) == 0}
