from typing import Any
from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    dataset_id: str
    filename: str
    message: str


class DatasetMetadata(BaseModel):
    dataset_id: str
    original_filename: str
    stored_filename: str
    processed_filename: str
    upload_time: str
    row_count: int
    column_count: int
    columns: list[str]
    original_path: str
    processed_path: str
    status: str = "ready"
    file_hash: str = ""
    error_message: str | None = None
    parquet_path: str | None = None
    storage_format: str = "csv"


class DatasetStatusResponse(BaseModel):
    dataset_id: str
    status: str
    row_count: int
    column_count: int
    error_message: str | None = None


class ColumnSchema(BaseModel):
    name: str
    dtype: str
    semantic_type: str
    missing_count: int
    unique_count: int
    sample_values: list[Any]


class MissingSummary(BaseModel):
    total_missing_values: int
    missing_values_by_column: dict[str, int]
    completeness_pct: float


class DatasetOverviewResponse(BaseModel):
    dataset_id: str
    original_filename: str
    status: str
    row_count: int
    column_count: int
    columns: list[str]
    column_schema: list[ColumnSchema]
    column_groups: dict[str, list[str]]
    missing_summary: MissingSummary
    duplicate_rows: int
    dtypes: dict[str, str]
    numeric_summary: dict[str, dict[str, Any]]
    categorical_summary: dict[str, list[dict[str, Any]]]
    preview: list[dict[str, Any]]


class DatasetPreviewResponse(BaseModel):
    dataset_id: str
    columns: list[str]
    rows: list[dict[str, Any]]
    preview_row_count: int = Field(..., description="Number of rows returned in preview.")
