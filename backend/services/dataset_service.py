from __future__ import annotations

import pandas as pd

from backend.core.constants import DEFAULT_PREVIEW_ROWS, MAX_PREVIEW_ROWS
from backend.storage.dataset_registry import load_dataset_record
from backend.storage.local_storage import load_processed_dataframe
from backend.storage.metadata_store import get_dataset, list_datasets
from backend.utils.response_utils import dataframe_preview


def get_all_datasets() -> list[dict]:
    return sorted(list_datasets(), key=lambda item: item.get("upload_time", ""), reverse=True)


def get_dataset_metadata(dataset_id: str) -> dict:
    return get_dataset(dataset_id)


def load_dataset_dataframe(dataset_id: str) -> pd.DataFrame:
    metadata = get_dataset(dataset_id)
    if metadata.get("parquet_path"):
        return load_dataset_record(dataset_id).dataframe
    return load_processed_dataframe(metadata["processed_filename"])


def get_dataset_status(dataset_id: str) -> dict:
    metadata = get_dataset(dataset_id)
    return {
        "dataset_id": dataset_id,
        "status": metadata.get("status", "ready"),
        "row_count": int(metadata.get("row_count", 0)),
        "column_count": int(metadata.get("column_count", 0)),
        "error_message": metadata.get("error_message"),
    }


def get_dataset_overview(dataset_id: str) -> dict:
    metadata = get_dataset(dataset_id)
    overview = metadata.get("overview") or {}
    if not overview:
        record = load_dataset_record(dataset_id)
        overview = record.overview

    return {
        "dataset_id": dataset_id,
        "original_filename": metadata["original_filename"],
        "status": metadata.get("status", "ready"),
        **overview,
    }


def get_dataset_preview(dataset_id: str, rows: int = DEFAULT_PREVIEW_ROWS) -> dict:
    rows = max(1, min(rows, MAX_PREVIEW_ROWS))
    df = load_dataset_dataframe(dataset_id)
    return {
        "dataset_id": dataset_id,
        "columns": df.columns.tolist(),
        "rows": dataframe_preview(df, rows=rows),
        "preview_row_count": min(rows, len(df)),
    }
