#!/usr/bin/env python3
"""Analyze likely module/test/doc impact for a task before implementation."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import ROOT, load_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="PIOS impact analyzer")
    parser.add_argument("--task", required=True, help="Task description")
    parser.add_argument("--paths", nargs="*", default=[], help="Optional known file paths")
    args = parser.parse_args()

    manifest = load_manifest()
    task_l = args.task.lower()
    keywords = manifest.get("keyword_module_map", {})
    doc_hints = manifest.get("doc_update_hints", {})

    matched_keywords: list[str] = []
    affected_dirs: set[str] = set()
    for key, dirs in keywords.items():
        if key in task_l:
            matched_keywords.append(key)
            for d in dirs:
                affected_dirs.add(d)

    for path in args.paths:
        p = Path(path)
        affected_dirs.add(str(p.parent).replace("\\", "/"))
        for key, dirs in keywords.items():
            if key in path.lower():
                matched_keywords.append(key)
                for d in dirs:
                    affected_dirs.add(d)

    if not affected_dirs:
        # Heuristic fallback from common tokens
        for token, folder in (
            ("frontend", "frontend"),
            ("backend", "backend/services"),
            ("test", "tests"),
            ("rag", "backend/rag"),
            ("api", "backend/api/routes"),
        ):
            if token in task_l:
                affected_dirs.add(folder)

    tests = _suggest_tests(matched_keywords, task_l, args.paths)
    docs = _suggest_docs(matched_keywords, doc_hints, task_l)
    duplicates = _find_similar(task_l)
    risks = _risks(matched_keywords, task_l)

    print("=== PIOS Impact Analysis ===")
    print(f"Task: {args.task}")
    print("\nMatched keywords:")
    print(", ".join(sorted(set(matched_keywords))) or "(none)")
    print("\nLikely affected modules/dirs:")
    for d in sorted(affected_dirs):
        print(f"  - {d}")
    print("\nSuggested tests to update/run:")
    for t in tests:
        print(f"  - {t}")
    print("\nDocumentation likely to change:")
    for d in docs:
        print(f"  - {d}")
    print("\nPossible existing functionality:")
    for d in duplicates:
        print(f"  - {d}")
    print("\nRisks:")
    for r in risks:
        print(f"  - {r}")
    print("\nArchitecture check: python pios/tools/arch_check.py")
    print("=== End ===")


def _suggest_tests(keywords: list[str], task_l: str, paths: list[str]) -> list[str]:
    tests_dir = ROOT / "tests"
    suggestions: list[str] = []
    needles = set(keywords)
    for token in re.findall(r"[a-z0-9_]{4,}", task_l):
        needles.add(token)
    for path in paths:
        stem = Path(path).stem.replace("_service", "").replace("_page", "")
        needles.add(stem.lower())

    if tests_dir.exists():
        for test in sorted(tests_dir.rglob("test_*.py")):
            name = test.name.lower()
            rel = str(test.relative_to(ROOT)).replace("\\", "/")
            if any(n in name for n in needles if len(n) >= 4):
                suggestions.append(rel)
    if not suggestions:
        suggestions.append("tests/ (run targeted pytest after identifying new helpers)")
    return suggestions[:15]


def _suggest_docs(keywords: list[str], doc_hints: dict, task_l: str) -> list[str]:
    docs: list[str] = ["pios/05_status/PROJECT_STATUS.md", "pios/04_sprints/CURRENT_SPRINT.md"]
    for key, paths in doc_hints.items():
        if key in task_l or key in keywords:
            docs.extend(paths)
    # keyword overlaps
    for key in keywords:
        for hint_key, paths in doc_hints.items():
            if key in hint_key or hint_key in key:
                docs.extend(paths)
    # dedupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for d in docs:
        if d not in seen:
            seen.add(d)
            out.append(d)
    return out


def _find_similar(task_l: str) -> list[str]:
    hits: list[str] = []
    search_roots = [ROOT / "backend" / "services", ROOT / "frontend" / "services", ROOT / "frontend" / "app_pages"]
    tokens = [t for t in re.findall(r"[a-z0-9_]{5,}", task_l) if t not in {"implement", "update", "create", "should"}]
    for base in search_roots:
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            name = path.name.lower()
            if any(t in name for t in tokens):
                hits.append(str(path.relative_to(ROOT)).replace("\\", "/"))
    return hits[:12] or ["(no strong filename matches — still search before duplicating)"]


def _risks(keywords: list[str], task_l: str) -> list[str]:
    risks = [
        "Skipping arch_check may introduce layer violations",
        "Forgetting PIOS status/sprint updates leaves SSOT stale",
    ]
    if "billing" in keywords or "auth" in keywords:
        risks.append("Touches commercial/auth surfaces — respect KI-002 in-memory limitations")
    if "rag" in keywords or "ai" in task_l:
        risks.append("AI/RAG changes need validation and must not invent mounted routes")
    if "storage" in keywords:
        risks.append("S3 remains stub (KI-003); prefer local backend unless intentionally extending stub")
    if "frontend" in task_l and "backend" in task_l:
        risks.append("Cross-stack change — keep frontend on HTTP clients, not backend imports")
    return risks


if __name__ == "__main__":
    main()
