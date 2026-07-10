from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

FORECAST_CAPABILITY_SCHEMA_VERSION = "1.0.0"

# Reserved empty buckets for future forecasting capabilities. Placeholders only.
FORECAST_CAPABILITY_FUTURE_EXTENSION_KEYS: tuple[str, ...] = (
    "arima",
    "prophet",
    "xgboost",
    "lightgbm",
    "catboost",
    "lstm",
    "gru",
    "tft",
    "nhits",
    "transformer",
    "automl",
    "hyperparameter_tuning",
    "feature_selection",
    "model_registry",
    "model_serving",
    "online_learning",
    "ensemble_manager",
    "drift_monitor",
    "model_monitoring",
    "experiment_tracking",
)


def empty_forecast_capability_future_extensions() -> dict[str, dict[str, Any]]:
    return {key: {} for key in FORECAST_CAPABILITY_FUTURE_EXTENSION_KEYS}


class CapabilityType(str, Enum):
    adapter = "adapter"
    pipeline = "pipeline"
    prediction = "prediction"
    validation = "validation"
    statistical = "statistical"
    machine_learning = "machine_learning"
    deep_learning = "deep_learning"
    ensemble = "ensemble"
    custom = "custom"


class CapabilityStatus(str, Enum):
    planned = "planned"
    available = "available"
    deprecated = "deprecated"
    experimental = "experimental"
    disabled = "disabled"


class ForecastCapability(BaseModel):
    """Catalog entry for one forecasting capability. Metadata only — never executes."""

    model_config = ConfigDict(extra="allow")

    capability_id: str
    capability_name: str
    capability_type: CapabilityType
    version: str = FORECAST_CAPABILITY_SCHEMA_VERSION
    status: CapabilityStatus = CapabilityStatus.planned
    supported_data_types: list[str] = Field(default_factory=list)
    supported_time_granularity: list[str] = Field(default_factory=list)
    supported_targets: list[str] = Field(default_factory=list)
    supported_features: list[str] = Field(default_factory=list)
    required_inputs: list[str] = Field(default_factory=list)
    optional_inputs: list[str] = Field(default_factory=list)
    produced_outputs: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    owner: str = "platform"
    created_at: str = ""
    updated_at: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class CapabilityRegistryMetadata(BaseModel):
    legacy: dict[str, Any] = Field(default_factory=dict)
    debug: dict[str, Any] = Field(default_factory=dict)
    custom: dict[str, Any] = Field(default_factory=dict)
    future_extensions: dict[str, Any] = Field(
        default_factory=empty_forecast_capability_future_extensions
    )


class CapabilityStatistics(BaseModel):
    total_capabilities: int = 0
    active_capabilities: int = 0
    planned_capabilities: int = 0
    experimental_capabilities: int = 0
    deprecated_capabilities: int = 0
    disabled_capabilities: int = 0
    capability_type_breakdown: dict[str, int] = Field(default_factory=dict)
    dependency_count: int = 0


class CapabilityRegistrySummary(BaseModel):
    registry_version: str = FORECAST_CAPABILITY_SCHEMA_VERSION
    total_capabilities: int = 0
    available: int = 0
    planned: int = 0
    experimental: int = 0
    dependency_count: int = 0
    overall_health: str = "unknown"


class ForecastCapabilityRegistry(BaseModel):
    """Single source of truth for forecasting capability metadata."""

    model_config = ConfigDict(extra="allow")

    registry_id: str
    schema_version: str = FORECAST_CAPABILITY_SCHEMA_VERSION
    capabilities: list[ForecastCapability] = Field(default_factory=list)
    generated_at: str = ""
    metadata: CapabilityRegistryMetadata = Field(default_factory=CapabilityRegistryMetadata)
