from __future__ import annotations

from enum import Enum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

FORECAST_PLUGIN_SCHEMA_VERSION = "1.0.0"

# Reserved empty buckets for future plug-in infrastructure. Placeholders only.
FORECAST_PLUGIN_FUTURE_EXTENSION_KEYS: tuple[str, ...] = (
    "training_runtime",
    "gpu_runtime",
    "distributed_execution",
    "model_registry",
    "model_versioning",
    "feature_store",
    "backtesting",
    "paper_trading",
    "live_prediction",
    "streaming",
    "ensemble",
    "auto_ml",
)

# Reserved future plug-in placeholders — catalog only, no implementations.
FORECAST_FUTURE_PLUGIN_KEYS: tuple[str, ...] = (
    "arima",
    "sarima",
    "prophet",
    "neural_prophet",
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
    "timesfm",
    "patchtst",
    "chronos",
    "trading_forecast",
    "business_forecast",
    "demand_forecast",
    "inventory_forecast",
    "custom_forecast",
)

# Lifecycle methods every future forecasting plug-in must expose.
FORECAST_PLUGIN_INTERFACE_METHODS: tuple[str, ...] = (
    "initialize",
    "prepare",
    "fit",
    "predict",
    "validate",
    "explain",
    "cleanup",
    "shutdown",
)


def empty_forecast_plugin_future_extensions() -> dict[str, dict[str, Any]]:
    return {key: {} for key in FORECAST_PLUGIN_FUTURE_EXTENSION_KEYS}


def empty_forecast_future_plugins() -> dict[str, dict[str, Any]]:
    return {key: {} for key in FORECAST_FUTURE_PLUGIN_KEYS}


class PluginType(str, Enum):
    statistical = "Statistical"
    machine_learning = "Machine Learning"
    deep_learning = "Deep Learning"
    foundation_model = "Foundation Model"
    hybrid = "Hybrid"
    trading = "Trading"
    business = "Business"
    custom = "Custom"


class PluginExecutionState(str, Enum):
    """Catalog state only — plug-ins are never executed in this sprint."""

    registered = "registered"
    available = "available"
    unavailable = "unavailable"
    deprecated = "deprecated"
    experimental = "experimental"


class PluginCapability(str, Enum):
    multivariate = "multivariate"
    probabilistic = "probabilistic"
    explainability = "explainability"
    online_learning = "online_learning"


class ForecastPluginInterfaceSpec(BaseModel):
    """Lifecycle interface definition only — no executable logic."""

    methods: list[str] = Field(default_factory=lambda: list(FORECAST_PLUGIN_INTERFACE_METHODS))
    notes: str = "Interface definitions only. Do not implement forecasting logic here."


@runtime_checkable
class ForecastPluginProtocol(Protocol):
    """Structural contract for future forecasting plug-ins. Not implemented here."""

    def initialize(self, *args: Any, **kwargs: Any) -> Any: ...

    def prepare(self, *args: Any, **kwargs: Any) -> Any: ...

    def fit(self, *args: Any, **kwargs: Any) -> Any: ...

    def predict(self, *args: Any, **kwargs: Any) -> Any: ...

    def validate(self, *args: Any, **kwargs: Any) -> Any: ...

    def explain(self, *args: Any, **kwargs: Any) -> Any: ...

    def cleanup(self, *args: Any, **kwargs: Any) -> Any: ...

    def shutdown(self, *args: Any, **kwargs: Any) -> Any: ...


class PluginCompatibility(BaseModel):
    """Declared compatibility with platform layers. Metadata only."""

    adapter_compatible: bool = True
    prediction_compatible: bool = True
    validation_compatible: bool = True
    registry_compatible: bool = True
    bundle_compatible: bool = True
    compatible_adapter_ids: list[str] = Field(default_factory=list)
    notes: str = ""


class ForecastPlugin(BaseModel):
    """Catalog entry for one forecast plug-in. Metadata only — never executes."""

    model_config = ConfigDict(extra="allow")

    plugin_id: str
    plugin_name: str
    plugin_type: PluginType
    plugin_version: str = FORECAST_PLUGIN_SCHEMA_VERSION
    description: str = ""
    author: str = "platform"
    supported_domains: list[str] = Field(default_factory=list)
    supported_prediction_types: list[str] = Field(default_factory=list)
    supported_time_horizons: list[str] = Field(default_factory=list)
    supported_frequencies: list[str] = Field(default_factory=list)
    supported_features: list[str] = Field(default_factory=list)
    supported_targets: list[str] = Field(default_factory=list)
    supports_multivariate: bool = False
    supports_probabilistic: bool = False
    supports_explainability: bool = False
    supports_online_learning: bool = False
    execution_state: PluginExecutionState = PluginExecutionState.registered
    compatibility: PluginCompatibility = Field(default_factory=PluginCompatibility)
    dependencies: list[str] = Field(default_factory=list)
    interface: ForecastPluginInterfaceSpec = Field(default_factory=ForecastPluginInterfaceSpec)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PluginRegistryMetadata(BaseModel):
    legacy: dict[str, Any] = Field(default_factory=dict)
    debug: dict[str, Any] = Field(default_factory=dict)
    custom: dict[str, Any] = Field(default_factory=dict)
    future_extensions: dict[str, Any] = Field(
        default_factory=empty_forecast_plugin_future_extensions
    )
    future_plugins: dict[str, Any] = Field(default_factory=empty_forecast_future_plugins)


class PluginStatistics(BaseModel):
    total_plugins: int = 0
    by_type: dict[str, int] = Field(default_factory=dict)
    by_state: dict[str, int] = Field(default_factory=dict)
    by_domain: dict[str, int] = Field(default_factory=dict)
    multivariate_count: int = 0
    probabilistic_count: int = 0
    explainability_count: int = 0
    online_learning_count: int = 0
    fully_compatible_count: int = 0


class ForecastPluginRegistry(BaseModel):
    """Read-only catalog of forecast plug-ins. Architecture only."""

    model_config = ConfigDict(extra="allow")

    registry_id: str
    schema_version: str = FORECAST_PLUGIN_SCHEMA_VERSION
    plugins: list[ForecastPlugin] = Field(default_factory=list)
    interface_contract: ForecastPluginInterfaceSpec = Field(
        default_factory=ForecastPluginInterfaceSpec
    )
    generated_at: str = ""
    metadata: PluginRegistryMetadata = Field(default_factory=PluginRegistryMetadata)
