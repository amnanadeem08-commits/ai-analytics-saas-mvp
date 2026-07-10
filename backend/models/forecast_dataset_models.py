from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

FORECAST_DATASET_SCHEMA_VERSION = "1.0.0"

# Reserved empty buckets for future dataset readiness analytics. Placeholders only.
FORECAST_DATASET_FUTURE_EXTENSION_KEYS: tuple[str, ...] = (
    "seasonality",
    "trend_detection",
    "stationarity",
    "lag_analysis",
    "rolling_windows",
    "holiday_calendar",
    "feature_engineering",
    "encoding",
    "normalization",
    "outlier_detection",
    "data_drift",
    "concept_drift",
    "quality_monitoring",
    "backtesting",
    "live_validation",
)

# Canonical validation section names — representation only.
READINESS_VALIDATION_SECTIONS: tuple[str, ...] = (
    "Dataset Identity",
    "Time Index",
    "Target Variable",
    "Feature Availability",
    "Data Completeness",
    "Data Consistency",
    "Forecast Compatibility",
)


def empty_forecast_dataset_future_extensions() -> dict[str, dict[str, Any]]:
    return {key: {} for key in FORECAST_DATASET_FUTURE_EXTENSION_KEYS}


class ReadinessStatus(str, Enum):
    unknown = "unknown"
    not_ready = "not_ready"
    partially_ready = "partially_ready"
    ready = "ready"
    excellent = "excellent"


class TimeGranularity(str, Enum):
    unknown = "unknown"
    hourly = "hourly"
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    quarterly = "quarterly"
    yearly = "yearly"
    custom = "custom"


class ValidationCheckStatus(str, Enum):
    passed = "passed"
    failed = "failed"
    warning = "warning"
    skipped = "skipped"


class ReadinessValidationResult(BaseModel):
    """One metadata validation check. Never inspects dataframe values."""

    validation_id: str
    section: str
    check_name: str
    status: ValidationCheckStatus = ValidationCheckStatus.skipped
    message: str = ""
    field: str = ""


class ForecastDatasetMetadata(BaseModel):
    legacy: dict[str, Any] = Field(default_factory=dict)
    debug: dict[str, Any] = Field(default_factory=dict)
    custom: dict[str, Any] = Field(default_factory=dict)
    future_extensions: dict[str, Any] = Field(
        default_factory=empty_forecast_dataset_future_extensions
    )


class ForecastDatasetSummary(BaseModel):
    dataset_name: str = ""
    status: str = ""
    overall_score: float = 0.0
    record_count: int | None = None
    time_column: str | None = None
    target_column: str | None = None
    granularity: str = ""
    recommendation_count: int = 0
    warning_count: int = 0


class ForecastDatasetStatistics(BaseModel):
    validation_count: int = 0
    warning_count: int = 0
    recommendation_count: int = 0
    missing_fields: list[str] = Field(default_factory=list)
    passed_checks: int = 0
    failed_checks: int = 0


class ForecastDatasetReadiness(BaseModel):
    """Metadata-only readiness assessment for future forecasting engines."""

    model_config = ConfigDict(extra="allow")

    readiness_id: str
    schema_version: str = FORECAST_DATASET_SCHEMA_VERSION
    dataset_id: str | None = None
    dataset_name: str = ""
    readiness_status: ReadinessStatus = ReadinessStatus.unknown
    overall_score: float = Field(default=0.0, ge=0.0, le=100.0)
    time_column: str | None = None
    target_column: str | None = None
    feature_columns: list[str] = Field(default_factory=list)
    record_count: int | None = None
    time_granularity: TimeGranularity = TimeGranularity.unknown
    missing_values: dict[str, Any] = Field(default_factory=dict)
    duplicate_records: int | None = None
    date_range: dict[str, Any] = Field(default_factory=dict)
    recommended_frequency: str = ""
    warnings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    validation_results: list[ReadinessValidationResult] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    metadata: ForecastDatasetMetadata = Field(default_factory=ForecastDatasetMetadata)
