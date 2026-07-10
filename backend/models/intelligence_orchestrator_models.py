from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

INTELLIGENCE_ORCHESTRATOR_SCHEMA_VERSION = "1.0.0"

# Reserved empty buckets for future runtime / agent / LLM wiring. Placeholders only.
INTELLIGENCE_ORCHESTRATOR_FUTURE_EXTENSION_KEYS: tuple[str, ...] = (
    "runtime",
    "llm",
    "tool_execution",
    "workflow",
    "planner",
    "scheduler",
    "agents",
    "memory",
    "automation",
    "events",
    "queues",
    "observability",
    "monitoring",
    "retry",
    "distributed_execution",
    "parallel_execution",
)


def empty_intelligence_orchestrator_future_extensions() -> dict[str, dict[str, Any]]:
    return {key: {} for key in INTELLIGENCE_ORCHESTRATOR_FUTURE_EXTENSION_KEYS}


class StageStatus(str, Enum):
    planned = "planned"
    available = "available"
    experimental = "experimental"
    deprecated = "deprecated"
    disabled = "disabled"


class OrchestrationStage(BaseModel):
    """One orchestration stage in the intelligence/forecast chain. Metadata only."""

    model_config = ConfigDict(extra="allow")

    stage_id: str
    stage_name: str
    input_objects: list[str] = Field(default_factory=list)
    output_objects: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    optional_dependencies: list[str] = Field(default_factory=list)
    produced_assets: list[str] = Field(default_factory=list)
    consumed_assets: list[str] = Field(default_factory=list)
    execution_order: int = 0
    enabled: bool = True
    status: StageStatus = StageStatus.planned
    metadata: dict[str, Any] = Field(default_factory=dict)


class OrchestratorMetadata(BaseModel):
    legacy: dict[str, Any] = Field(default_factory=dict)
    debug: dict[str, Any] = Field(default_factory=dict)
    custom: dict[str, Any] = Field(default_factory=dict)
    future_extensions: dict[str, Any] = Field(
        default_factory=empty_intelligence_orchestrator_future_extensions
    )


class OrchestratorStatistics(BaseModel):
    total_stages: int = 0
    enabled_stages: int = 0
    disabled_stages: int = 0
    available_stages: int = 0
    planned_stages: int = 0
    experimental_stages: int = 0
    dependency_count: int = 0
    optional_dependency_count: int = 0
    max_execution_order: int = 0


class IntelligenceOrchestrator(BaseModel):
    """Canonical metadata catalog of how intelligence engines connect. Never executes."""

    model_config = ConfigDict(extra="allow")

    orchestrator_id: str
    schema_version: str = INTELLIGENCE_ORCHESTRATOR_SCHEMA_VERSION
    stages: list[OrchestrationStage] = Field(default_factory=list)
    generated_at: str = ""
    metadata: OrchestratorMetadata = Field(default_factory=OrchestratorMetadata)
