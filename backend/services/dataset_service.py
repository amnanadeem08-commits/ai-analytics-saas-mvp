from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

from backend.core.constants import DEFAULT_PREVIEW_ROWS, MAX_PREVIEW_ROWS
from backend.storage.metadata_store import get_dataset, list_datasets
from backend.utils.response_utils import dataframe_preview


def get_all_datasets() -> list[dict]:
    return sorted(list_datasets(), key=lambda item: item.get("upload_time", ""), reverse=True)


def get_dataset_metadata(dataset_id: str) -> dict:
    return get_dataset(dataset_id)


@lru_cache(maxsize=8)
def _load_dataset_dataframe_cached(
    dataset_id: str,
    file_hash: str,
    parquet_path: str,
    processed_path: str,
) -> pd.DataFrame:
    if parquet_path and Path(parquet_path).exists():
        dataframe = pd.read_parquet(parquet_path)
    else:
        dataframe = pd.read_csv(processed_path)
    dataframe.attrs["_dataset_cache_key"] = f"{dataset_id}:{file_hash}"
    return dataframe


def load_dataset_dataframe(dataset_id: str) -> pd.DataFrame:
    metadata = get_dataset(dataset_id)
    return _load_dataset_dataframe_cached(
        dataset_id,
        metadata.get("file_hash", ""),
        metadata.get("parquet_path") or "",
        metadata.get("processed_path") or "",
    )


def clear_dataset_cache() -> None:
    _load_dataset_dataframe_cached.cache_clear()


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