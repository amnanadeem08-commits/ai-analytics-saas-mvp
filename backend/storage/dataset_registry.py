from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from backend.core.config import settings
from backend.core.dataset_record import DatasetRecord
from backend.core.exceptions import DatasetNotFoundError


def dataset_directory(dataset_id: str) -> Path:
    return settings.DATASETS_DIR / dataset_id


def dataset_meta_path(dataset_id: str) -> Path:
    return dataset_directory(dataset_id) / "meta.json"


def dataset_data_path(dataset_id: str) -> Path:
    return dataset_directory(dataset_id) / "data.parquet"


def save_dataset_record(record: DatasetRecord) -> dict[str, Any]:
    """Persist canonical per-dataset metadata and a parquet copy when possible."""
    root = dataset_directory(record.dataset_id)
    root.mkdir(parents=True, exist_ok=True)

    metadata = record.to_metadata()
    parquet_path = dataset_data_path(record.dataset_id)
    try:
        record.dataframe.to_parquet(parquet_path, index=False)
        metadata["parquet_path"] = str(parquet_path.as_posix())
        metadata["storage_format"] = "parquet"
    except Exception:
        metadata["parquet_path"] = None
        metadata["storage_format"] = "csv"

    dataset_meta_path(record.dataset_id).write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )
    return metadata


def load_dataset_record(dataset_id: str) -> DatasetRecord:
    meta_path = dataset_meta_path(dataset_id)
    if not meta_path.exists():
        raise DatasetNotFoundError(f"Dataset '{dataset_id}' was not found.")

    metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    parquet_path = metadata.get("parquet_path")
    if parquet_path and Path(parquet_path).exists():
        dataframe = pd.read_parquet(parquet_path)
    else:
        dataframe = pd.read_csv(metadata["processed_path"])

    return DatasetRecord(
        dataset_id=metadata["dataset_id"],
        original_filename=metadata["original_filename"],
        stored_filename=metadata["stored_filename"],
        processed_filename=metadata["processed_filename"],
        dataframe=dataframe,
        original_path=metadata["original_path"],
        processed_path=metadata["processed_path"],
        overview=metadata.get("overview", {}),
        column_schema=metadata.get("column_schema", []),
        column_groups=metadata.get("column_groups", {}),
        status=metadata.get("status", "ready"),
        upload_time=metadata.get("upload_time", ""),
        file_hash=metadata.get("file_hash", ""),
        error_message=metadata.get("error_message"),
    )
