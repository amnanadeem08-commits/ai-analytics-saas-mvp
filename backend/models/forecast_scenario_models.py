from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

FORECAST_SCENARIO_SCHEMA_VERSION = "1.0.0"

# Reserved empty buckets for future scenario engines. Placeholders only.
FORECAST_SCENARIO_FUTURE_EXTENSION_KEYS: tuple[str, ...] = (
    "monte_carlo",
    "what_if",
    "stress_testing",
    "sensitivity_analysis",
    "optimization",
    "constraint_solver",
    "economic_models",
    "market_models",
    "risk_models",
    "business_rules",
    "simulation",
    "digital_twin",
)


def empty_forecast_scenario_future_extensions() -> dict[str, dict[str, Any]]:
    return {key: {} for key in FORECAST_SCENARIO_FUTURE_EXTENSION_KEYS}


class ScenarioType(str, Enum):
    baseline = "baseline"
    expected = "expected"
    optimistic = "optimistic"
    pessimistic = "pessimistic"
    best_case = "best_case"
    worst_case = "worst_case"
    custom = "custom"


class ScenarioStatus(str, Enum):
    planned = "planned"
    available = "available"
    experimental = "experimental"
    deprecated = "deprecated"
    disabled = "disabled"


class ForecastScenario(BaseModel):
    """Catalog entry for one forecast scenario. Metadata only — never simulates."""

    model_config = ConfigDict(extra="allow")

    scenario_id: str
    scenario_name: str
    scenario_type: ScenarioType
    description: str = ""
    status: ScenarioStatus = ScenarioStatus.planned
    priority: int = 0
    dataset_id: str | None = None
    applicable_domains: list[str] = Field(default_factory=list)
    supported_targets: list[str] = Field(default_factory=list)
    supported_granularity: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScenarioRegistryMetadata(BaseModel):
    legacy: dict[str, Any] = Field(default_factory=dict)
    debug: dict[str, Any] = Field(default_factory=dict)
    custom: dict[str, Any] = Field(default_factory=dict)
    future_extensions: dict[str, Any] = Field(
        default_factory=empty_forecast_scenario_future_extensions
    )


class ScenarioStatistics(BaseModel):
    total_scenarios: int = 0
    available: int = 0
    planned: int = 0
    experimental: int = 0
    deprecated: int = 0
    disabled: int = 0
    custom: int = 0
    dependency_count: int = 0


class ScenarioRegistrySummary(BaseModel):
    registry_version: str = FORECAST_SCENARIO_SCHEMA_VERSION
    scenario_count: int = 0
    available: int = 0
    experimental: int = 0
    dependency_count: int = 0
    overall_health: str = "unknown"


class ForecastScenarioRegistry(BaseModel):
    """Canonical catalog of forecast scenarios. Metadata only."""

    model_config = ConfigDict(extra="allow")

    registry_id: str
    schema_version: str = FORECAST_SCENARIO_SCHEMA_VERSION
    scenarios: list[ForecastScenario] = Field(default_factory=list)
    generated_at: str = ""
    metadata: ScenarioRegistryMetadata = Field(default_factory=ScenarioRegistryMetadata)
