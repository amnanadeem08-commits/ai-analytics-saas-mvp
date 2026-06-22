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


class CleaningOptions(BaseModel):
    normalize_casing: str = Field(default="lower", pattern="^(lower|upper|title|none)$")
    numeric_missing_strategy: str = Field(default="median", pattern="^(mean|median|mode|drop_rows)$")
    categorical_missing_strategy: str = Field(default="mode", pattern="^(mode|unknown|drop_rows)$")
    datetime_missing_strategy: str = Field(default="manual", pattern="^(manual|ffill|bfill)$")
    high_missing_unknown_threshold: float = Field(default=0.2, ge=0.0, le=1.0)
    outlier_strategy: str = Field(default="keep", pattern="^(keep|cap|remove)$")
    outlier_method: str = Field(default="iqr", pattern="^(iqr|zscore)$")
    outlier_zscore_threshold: float = Field(default=3.0, ge=1.0, le=6.0)


class CleaningChange(BaseModel):
    column: str
    action: str
    method: str
    count: int


class DatasetCleaningResponse(BaseModel):
    dataset_id: str
    cleaned_filename_csv: str
    cleaned_filename_xlsx: str
    rows_before: int
    rows_after: int
    columns_before: int
    columns_after: int
    duplicates_removed: int
    fully_empty_rows_removed: int
    fully_empty_columns_removed: int
    completeness_before_pct: float
    completeness_after_pct: float
    high_missing_columns: list[str]
    outlier_flags: dict[str, int]
    changes: list[CleaningChange]
    preview_rows: list[dict[str, Any]]
