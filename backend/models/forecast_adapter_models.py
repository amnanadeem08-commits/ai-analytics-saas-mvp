from __future__ import annotations

from enum import Enum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

FORECAST_ADAPTER_SCHEMA_VERSION = "1.0.0"

# Reserved empty buckets for future forecasting infrastructure. Placeholders only.
# Owners:
#   feature_store         → Feature store
#   model_registry        → Model registry
#   training_pipeline     → Training pipeline
#   model_monitoring      → Model monitoring
#   hyperparameter_search → HPO / tuning
#   ensemble_engine       → Ensemble engine
#   gpu_execution         → GPU execution
#   distributed_training  → Distributed training
#   backtesting           → Backtesting
#   live_prediction       → Live prediction serving
FORECAST_ADAPTER_FUTURE_EXTENSION_KEYS: tuple[str, ...] = (
    "feature_store",
    "model_registry",
    "training_pipeline",
    "model_monitoring",
    "hyperparameter_search",
    "ensemble_engine",
    "gpu_execution",
    "distributed_training",
    "backtesting",
    "live_prediction",
)

# Reserved future adapter placeholders — catalog entries only, no implementations.
FORECAST_FUTURE_ADAPTER_KEYS: tuple[str, ...] = (
    "arima",
    "sarima",
    "prophet",
    "xgboost",
    "lightgbm",
    "catboost",
    "random_forest",
    "lstm",
    "gru",
    "transformer",
    "temporal_fusion_transformer",
    "n_beats",
    "deepar",
    "patchtst",
    "trading_forecast",
    "business_forecast",
    "custom_forecast",
)

# Standard interface method names every future forecasting engine must expose.
FORECAST_ADAPTER_INTERFACE_METHODS: tuple[str, ...] = (
    "prepare",
    "predict",
    "validate",
    "explain",
    "cleanup",
)


def empty_forecast_adapter_future_extensions() -> dict[str, dict[str, Any]]:
    return {key: {} for key in FORECAST_ADAPTER_FUTURE_EXTENSION_KEYS}


def empty_forecast_future_adapters() -> dict[str, dict[str, Any]]:
    return {key: {} for key in FORECAST_FUTURE_ADAPTER_KEYS}


class AdapterType(str, Enum):
    statistical = "Statistical"
    machine_learning = "Machine Learning"
    deep_learning = "Deep Learning"
    llm_forecasting = "LLM Forecasting"
    rule_based = "Rule Based"
    hybrid = "Hybrid"
    custom = "Custom"


class AdapterExecutionStatus(str, Enum):
    """Catalog status only — adapters are never executed in this sprint."""

    registered = "registered"
    available = "available"
    unavailable = "unavailable"
    deprecated = "deprecated"
    experimental = "experimental"


class ForecastAdapterInterfaceSpec(BaseModel):
    """Interface contract definition only — no executable logic."""

    methods: list[str] = Field(default_factory=lambda: list(FORECAST_ADAPTER_INTERFACE_METHODS))
    notes: str = "Interface definitions only. Do not implement forecasting logic here."


@runtime_checkable
class ForecastAdapterProtocol(Protocol):
    """Structural contract for future forecasting engines. Not implemented here."""

    def prepare(self, *args: Any, **kwargs: Any) -> Any: ...

    def predict(self, *args: Any, **kwargs: Any) -> Any: ...

    def validate(self, *args: Any, **kwargs: Any) -> Any: ...

    def explain(self, *args: Any, **kwargs: Any) -> Any: ...

    def cleanup(self, *args: Any, **kwargs: Any) -> Any: ...


class ForecastAdapter(BaseModel):
    """Catalog entry for one forecast adapter. Metadata only — never executes."""

    model_config = ConfigDict(extra="allow")

    adapter_id: str
    adapter_name: str
    adapter_type: AdapterType
    version: str = FORECAST_ADAPTER_SCHEMA_VERSION
    description: str = ""
    supported_domains: list[str] = Field(default_factory=list)
    supported_prediction_types: list[str] = Field(default_factory=list)
    required_inputs: list[str] = Field(default_factory=list)
    optional_inputs: list[str] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    confidence_supported: bool = False
    training_supported: bool = False
    online_learning_supported: bool = False
    validation_supported: bool = False
    execution_status: AdapterExecutionStatus = AdapterExecutionStatus.registered
    dependencies: list[str] = Field(default_factory=list)
    interface: ForecastAdapterInterfaceSpec = Field(default_factory=ForecastAdapterInterfaceSpec)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AdapterRegistryMetadata(BaseModel):
    legacy: dict[str, Any] = Field(default_factory=dict)
    debug: dict[str, Any] = Field(default_factory=dict)
    custom: dict[str, Any] = Field(default_factory=dict)
    future_extensions: dict[str, Any] = Field(
        default_factory=empty_forecast_adapter_future_extensions
    )
    future_adapters: dict[str, Any] = Field(default_factory=empty_forecast_future_adapters)


class AdapterStatistics(BaseModel):
    total_adapters: int = 0
    by_type: dict[str, int] = Field(default_factory=dict)
    by_status: dict[str, int] = Field(default_factory=dict)
    by_domain: dict[str, int] = Field(default_factory=dict)
    confidence_supported_count: int = 0
    training_supported_count: int = 0
    validation_supported_count: int = 0
    online_learning_supported_count: int = 0


class ForecastAdapterRegistry(BaseModel):
    """Read-only catalog of forecast adapters. Architecture only."""

    model_config = ConfigDict(extra="allow")

    registry_id: str
    schema_version: str = FORECAST_ADAPTER_SCHEMA_VERSION
    adapters: list[ForecastAdapter] = Field(default_factory=list)
    interface_contract: ForecastAdapterInterfaceSpec = Field(
        default_factory=ForecastAdapterInterfaceSpec
    )
    generated_at: str = ""
    metadata: AdapterRegistryMetadata = Field(default_factory=AdapterRegistryMetadata)
