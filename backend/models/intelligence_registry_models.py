from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

INTELLIGENCE_REGISTRY_SCHEMA_VERSION = "1.0.0"

# Supported schema versions for registered asset types (metadata catalog only).
SUPPORTED_SCHEMA_VERSIONS: frozenset[str] = frozenset({"1.0.0"})

# Reserved empty buckets for future platform layers. Placeholders only.
# Owners:
#   agents          → Multi-Agent execution
#   scheduler       → Job / pipeline scheduling
#   planner         → Planning layer
#   workflow        → Workflow automation
#   memory          → Agent / session memory
#   vector_store    → Vector store layer
#   knowledge_graph → Knowledge graph
#   api_gateway     → API gateway / external exposure
#   event_bus       → Event bus / pub-sub
#   lineage         → Data / intelligence lineage
#   observability   → Observability / telemetry
INTELLIGENCE_REGISTRY_FUTURE_EXTENSION_KEYS: tuple[str, ...] = (
    "agents",
    "scheduler",
    "planner",
    "workflow",
    "memory",
    "vector_store",
    "knowledge_graph",
    "api_gateway",
    "event_bus",
    "lineage",
    "observability",
)

# Canonical pipeline order (metadata only — no execution).
CANONICAL_PIPELINE_TYPES: tuple[str, ...] = (
    "insight",
    "validation",
    "decision",
    "root_cause",
    "executive_reasoning",
    "storyboard",
    "intelligence_bundle",
)


def empty_intelligence_registry_future_extensions() -> dict[str, dict[str, Any]]:
    return {key: {} for key in INTELLIGENCE_REGISTRY_FUTURE_EXTENSION_KEYS}


class RegistryObjectType(str, Enum):
    insight = "insight"
    validation = "validation"
    decision = "decision"
    root_cause = "root_cause"
    executive_reasoning = "executive_reasoning"
    storyboard = "storyboard"
    intelligence_bundle = "intelligence_bundle"


class RegistryAssetStatus(str, Enum):
    registered = "registered"
    pending = "pending"
    validated = "validated"
    incomplete = "incomplete"
    rejected = "rejected"
    unknown = "unknown"


class RegistryAsset(BaseModel):
    """Metadata catalog record for one intelligence asset.

    Stores references only — never full intelligence payloads.
    """

    model_config = ConfigDict(extra="allow")

    object_id: str
    object_type: RegistryObjectType
    schema_version: str = INTELLIGENCE_REGISTRY_SCHEMA_VERSION
    dataset_id: str | None = None
    domain: str | None = None
    status: RegistryAssetStatus = RegistryAssetStatus.registered
    dependencies: list[str] = Field(default_factory=list)
    produced_by: str = ""
    consumed_by: list[str] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    reference_id: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class DependencyEdge(BaseModel):
    """Directed edge: from_id depends on to_id. Metadata only."""

    from_id: str
    to_id: str
    from_type: str = ""
    to_type: str = ""
    edge_kind: str = "depends_on"


class DependencyGraph(BaseModel):
    """Metadata-only dependency graph. No scheduling or execution."""

    nodes: list[str] = Field(default_factory=list)
    edges: list[DependencyEdge] = Field(default_factory=list)
    canonical_pipeline: list[str] = Field(default_factory=lambda: list(CANONICAL_PIPELINE_TYPES))
    type_edges: list[DependencyEdge] = Field(default_factory=list)


class RegistryStatistics(BaseModel):
    """Aggregated catalog counts only — no analytics or scoring."""

    total_assets: int = 0
    assets_by_type: dict[str, int] = Field(default_factory=dict)
    datasets: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    dependency_depth: int = 0
    leaf_nodes: list[str] = Field(default_factory=list)
    root_nodes: list[str] = Field(default_factory=list)
    orphan_assets: list[str] = Field(default_factory=list)
    validation_summary: dict[str, Any] = Field(default_factory=dict)


class RegistryMetadata(BaseModel):
    legacy: dict[str, Any] = Field(default_factory=dict)
    debug: dict[str, Any] = Field(default_factory=dict)
    custom: dict[str, Any] = Field(default_factory=dict)
    future_extensions: dict[str, Any] = Field(
        default_factory=empty_intelligence_registry_future_extensions
    )


class IntelligenceRegistry(BaseModel):
    """Single source of truth for intelligence asset metadata (catalog only)."""

    model_config = ConfigDict(extra="allow")

    registry_id: str
    schema_version: str = INTELLIGENCE_REGISTRY_SCHEMA_VERSION
    dataset_id: str | None = None
    domain: str | None = None
    assets: list[RegistryAsset] = Field(default_factory=list)
    dependency_graph: DependencyGraph = Field(default_factory=DependencyGraph)
    generated_at: str = ""
    metadata: RegistryMetadata = Field(default_factory=RegistryMetadata)
