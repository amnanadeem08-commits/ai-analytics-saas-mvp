#!/usr/bin/env python3
"""Rank next-sprint recommendations from roadmap, debt, and current sprint."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import PIOS, read_text


def main() -> None:
    parser = argparse.ArgumentParser(description="PIOS sprint recommender")
    parser.add_argument("--quiet", action="store_true", help="Print top recommendation only")
    args = parser.parse_args()

    current = _first_heading(PIOS / "04_sprints" / "CURRENT_SPRINT.md")
    roadmap_items = _roadmap_items()
    debt_items = _debt_items()

    ranked: list[tuple[int, str]] = []

    # Finish current sprint first
    ranked.append((100, f"Complete current sprint: {current}"))

    # Map high-priority debt to roadmap
    for debt_id, title, priority in debt_items:
        score = {"High": 90, "High (ops)": 88, "Medium": 70, "Medium (ops)": 68, "Low": 40}.get(priority, 50)
        ranked.append((score, f"Pay down {debt_id}: {title}"))

    for idx, item in enumerate(roadmap_items):
        score = 85 - idx * 5
        ranked.append((score, f"Roadmap: {item}"))

    ranked.sort(key=lambda x: x[0], reverse=True)
    # Dedupe similar lines loosely
    seen: set[str] = set()
    unique: list[tuple[int, str]] = []
    for score, line in ranked:
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append((score, line))

    if args.quiet:
        print(unique[0][1] if unique else "No recommendation")
        return

    print("=== PIOS Sprint Recommendations ===")
    print(f"Current: {current}")
    print("\nRanked next actions:")
    for i, (score, line) in enumerate(unique[:10], 1):
        print(f"{i}. [{score}] {line}")
    print("=== End ===")


def _first_heading(path) -> str:
    if not path.exists():
        return "Unknown"
    for line in read_text(path).splitlines():
        if line.startswith("#"):
            return line.lstrip("# ").strip()
    return "Unknown"


def _roadmap_items() -> list[str]:
    text = read_text(PIOS / "01_vision" / "ROADMAP.md")
    items: list[str] = []
    in_post = False
    for line in text.splitlines():
        if line.startswith("## Post-1.0"):
            in_post = True
            continue
        if in_post and line.startswith("## "):
            break
        if in_post:
            m = re.match(r"\d+\.\s+\*\*(.+?)\*\*", line)
            if m:
                items.append(m.group(1))
    return items


def _debt_items() -> list[tuple[str, str, str]]:
    text = read_text(PIOS / "05_status" / "TECHNICAL_DEBT.md")
    items: list[tuple[str, str, str]] = []
    for line in text.splitlines():
        m = re.match(r"\|\s*(TD-\d+)\s*\|\s*(.+?)\s*\|\s*.*?\|\s*(.+?)\s*\|", line)
        if m and m.group(1) != "ID":
            items.append((m.group(1), m.group(2).strip(), m.group(3).strip()))
    return items


if __name__ == "__main__":
    main()
