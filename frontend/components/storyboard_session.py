from __future__ import annotations

from typing import Any


def add_storyboard_entry(storyboard: list[dict[str, Any]], entry: dict[str, Any]) -> dict[str, Any]:
    chart_id = str(entry.get("chart_id") or "").strip()
    if chart_id:
        existing = next((item for item in storyboard if item.get("chart_id") == chart_id), None)
        if existing:
            return {"entry": existing, "added": False}

    next_sequence = len(storyboard) + 1
    storyboard_entry = {**entry, "sequence": next_sequence, "order": next_sequence}
    if chart_id:
        storyboard_entry["chart_id"] = chart_id
    storyboard.append(storyboard_entry)
    return {"entry": storyboard_entry, "added": True}
