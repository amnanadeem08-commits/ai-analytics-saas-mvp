from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import pandas as pd


DATASET_STATUS_UPLOADING = "uploading"
DATASET_STATUS_PROCESSING = "processing"
DATASET_STATUS_READY = "ready"
DATASET_STATUS_FAILED = "failed"


@dataclass
class DatasetRecord:
    """Canonical local dataset record used by storage and analytics layers."""

    dataset_id: str
    original_filename: str
    stored_filename: str
    processed_filename: str
    dataframe: pd.DataFrame
    original_path: str
    processed_path: str
    overview: dict[str, Any] = field(default_factory=dict)
    column_schema: list[dict[str, Any]] = field(default_factory=list)
    column_groups: dict[str, list[str]] = field(default_factory=dict)
    status: str = DATASET_STATUS_READY
    upload_time: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    file_hash: str = ""
    error_message: str | None = None

    @property
    def row_count(self) -> int:
        return int(len(self.dataframe))

    @property
    def column_count(self) -> int:
        return int(len(self.dataframe.columns))

    @property
    def columns(self) -> list[str]:
        return self.dataframe.columns.tolist()

    def to_metadata(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "original_filename": self.original_filename,
            "stored_filename": self.stored_filename,
            "processed_filename": self.processed_filename,
            "upload_time": self.upload_time,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "columns": self.columns,
            "original_path": self.original_path,
            "processed_path": self.processed_path,
            "overview": self.overview,
            "column_schema": self.column_schema,
            "column_groups": self.column_groups,
            "status": self.status,
            "file_hash": self.file_hash,
            "error_message": self.error_message,
        }
