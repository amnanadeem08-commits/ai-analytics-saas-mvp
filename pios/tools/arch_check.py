#!/usr/bin/env python3
"""Enforce PIOS dependency/import rules from MANIFEST.yaml."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import ROOT, load_manifest


def main() -> int:
    manifest = load_manifest()
    rules = manifest.get("dependency_rules", [])
    errors = 0
    warnings = 0

    print("=== PIOS Architecture Check ===")
    for rule in rules:
        rule_id = rule.get("id", "UNKNOWN")
        scoped = rule.get("scoped_to", "")
        forbidden = rule.get("forbidden_import", "")
        severity = rule.get("severity", "error")
        if rule.get("advisory"):
            severity = "warning"
        scope_path = ROOT / scoped.replace("/", "\\") if "\\" not in scoped else ROOT / scoped
        # Path join with forward slashes works on Windows Path
        scope_path = ROOT / Path(scoped)
        if not forbidden or not scope_path.exists():
            print(f"SKIP {rule_id}: scope missing ({scoped})")
            continue

        hits = _scan_imports(scope_path, forbidden)
        if not hits:
            print(f"PASS {rule_id}: no `{forbidden}` imports under {scoped}")
            continue

        label = "WARN" if severity == "warning" else "FAIL"
        if severity == "warning":
            warnings += 1
        else:
            errors += 1
        print(f"{label} {rule_id}: {rule.get('description', forbidden)}")
        for hit in hits[:20]:
            print(f"  - {hit}")
        if len(hits) > 20:
            print(f"  ... and {len(hits) - 20} more")

    print(f"=== Done: errors={errors} warnings={warnings} ===")
    return 1 if errors else 0


def _scan_imports(base: Path, forbidden: str) -> list[str]:
    hits: list[str] = []
    for path in base.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                if name == forbidden or name.startswith(forbidden + "."):
                    rel = str(path.relative_to(ROOT)).replace("\\", "/")
                    hits.append(f"{rel}: import {name}")
    return hits


if __name__ == "__main__":
    sys.exit(main())
