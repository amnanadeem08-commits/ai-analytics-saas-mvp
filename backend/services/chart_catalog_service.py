from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.services.dataset_service import get_dataset_metadata
from backend.storage.dataset_registry import dataset_meta_path


def _catalog_path(dataset_id: str) -> Path:
    return dataset_meta_path(dataset_id).with_name("custom_chart_specs.json")


def load_custom_chart_specs(dataset_id: str) -> list[dict[str, Any]]:
    get_dataset_metadata(dataset_id)
    path = _catalog_path(dataset_id)
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return list(payload.values()) if isinstance(payload, dict) else []


def register_custom_chart_spec(dataset_id: str, chart: dict[str, Any]) -> dict[str, Any]:
    get_dataset_metadata(dataset_id)
    chart_id = chart["chart_id"]
    path = _catalog_path(dataset_id)
    existing: dict[str, dict[str, Any]] = {}
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            existing = payload
    if chart_id in existing:
        return {"chart": existing[chart_id], "registered": False}
    existing[chart_id] = chart
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    temporary.replace(path)
    return {"chart": chart, "registered": True}