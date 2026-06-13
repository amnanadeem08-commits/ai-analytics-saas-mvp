from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.core.config import settings
from backend.core.exceptions import DatasetNotFoundError


def _metadata_file() -> Path:
    settings.METADATA_DIR.mkdir(parents=True, exist_ok=True)
    if not settings.DATASETS_METADATA_FILE.exists():
        settings.DATASETS_METADATA_FILE.write_text("[]", encoding="utf-8")
    return settings.DATASETS_METADATA_FILE


def list_datasets() -> list[dict[str, Any]]:
    path = _metadata_file()
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def save_datasets(datasets: list[dict[str, Any]]) -> None:
    path = _metadata_file()
    path.write_text(json.dumps(datasets, indent=2), encoding="utf-8")


def add_dataset(metadata: dict[str, Any]) -> dict[str, Any]:
    datasets = list_datasets()
    datasets.append(metadata)
    save_datasets(datasets)
    return metadata


def get_dataset(dataset_id: str) -> dict[str, Any]:
    for dataset in list_datasets():
        if dataset.get("dataset_id") == dataset_id:
            return dataset
    raise DatasetNotFoundError(f"Dataset '{dataset_id}' was not found.")
