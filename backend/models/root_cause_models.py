from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.models.ai_insight_models import RiskLevel, ValidationStatus

RCA_SCHEMA_VERSION = "1.0.0"

# Reserved empty buckets for downstream engines. Do not populate with business logic here.
# Owners (future sprints — placeholders only):
#   prediction      → Prediction Engine
#   simulation      → Simulation Engine
#   workflow        → Workflow Engine
#   automation      → Automation Engine
#   approval        → Workflow / Approval Engine (compat reserved)
#   causal_graph    → Causal Graph Engine
#   knowledge_graph → Knowledge Graph Engine
#   llm_reasoning   → Executive Reasoning Engine (Sprint 5.7+)
#   agent_memory    → Multi-Agent Memory Layer
RCA_FUTURE_EXTENSION_KEYS: tuple[str, ...] = (
    "prediction",
    "simulation",
    "workflow",
    "automation",
    "approval",
    "causal_graph",
    "knowledge_graph",
    "llm_reasoning",
    "agent_memory",
)


def empty_rca_future_extensions() -> dict[str, dict[str, Any]]:
    """Return empty reserved extension buckets for RCA metadata."""
    return {key: {} for key in RCA_FUTURE_EXTENSION_KEYS}


class CauseCategory(str, Enum):
    sales = "Sales"
    marketing = "Marketing"
    finance = "Finance"
    operations = "Operations"
    inventory = "Inventory"
    supply_chain = "Supply Chain"
    customer = "Customer"
    pricing = "Pricing"
    quality = "Quality"
    data_quality = "Data Quality"
    external_factors = "External Factors"
    compliance = "Compliance"
    other = "Other"


class CauseSeverity(str, Enum):
    info = "info"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class CauseStatus(str, Enum):
    identified = "identified"
    inconclusive = "inconclusive"
    blocked = "blocked"


class ProbabilitySource(str, Enum):
    """How probability was obtained. Prediction Engine owns non-unknown values later."""

    unknown = "unknown"
    observed = "observed"
    estimated = "estimated"
    predicted = "predicted"


class CauseOrigin(str, Enum):
    """Deterministic provenance of a root cause explanation."""

    insight = "INSIGHT"
    decision = "DECISION"
    evidence = "EVIDENCE"
    metadata = "METADATA"
    mixed = "MIXED"


class CauseMetadata(BaseModel):
    """Structured metadata with reserved future_extensions for architecture freeze.

    future_extensions owners (placeholders only — no implementation in RCA):
    - prediction → Prediction Engine
    - simulation → Simulation Engine
    - workflow → Workflow Engine
    - automation → Automation Engine
    - approval → Workflow / Approval Engine
    - causal_graph → Causal Graph Engine
    - knowledge_graph → Knowledge Graph Engine
    - llm_reasoning → Executive Reasoning Engine
    - agent_memory → Multi-Agent Memory Layer
    """

    legacy: dict[str, Any] = Field(default_factory=dict)
    debug: dict[str, Any] = Field(default_factory=dict)
    custom: dict[str, Any] = Field(default_factory=dict)
    future_extensions: dict[str, Any] = Field(default_factory=empty_rca_future_extensions)


class CauseEvidence(BaseModel):
    label: str
    value: Any = None
    evidence_type: str = "text"
    source: str = ""
    confidence_score: float | None = None
    raw: dict[str, Any] | None = None


class CauseNode(BaseModel):
    """Graph-ready cause node for future DAG support without schema redesign.

    Current RCA builders populate a tree: at most one parent in ``parent_ids``.
    Fields ``parent_ids`` and ``child_ids`` are lists so multi-parent / multi-child
    graphs can be stored later without changing this model. This sprint does not
    implement DAG traversal or graph algorithms.
    """

    model_config = ConfigDict(extra="allow")

    node_id: str
    parent_ids: list[str] = Field(
        default_factory=list,
        description="Parent node ids. Tree mode uses 0–1 entry; future DAGs may use many.",
    )
    child_ids: list[str] = Field(
        default_factory=list,
        description="Child node ids. Supports one-to-many today and many-to-many later.",
    )
    level: int = 0
    description: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: list[CauseEvidence] = Field(default_factory=list)
    metadata: CauseMetadata = Field(default_factory=CauseMetadata)


class CauseChain(BaseModel):
    model_config = ConfigDict(extra="allow")

    chain_id: str
    outcome_title: str
    nodes: list[CauseNode] = Field(default_factory=list)
    primary_node_id: str | None = None
    depth: int = 0
    metadata: CauseMetadata = Field(default_factory=CauseMetadata)


class RootCause(BaseModel):
    """Canonical root-cause unit. Architecture frozen for Sprint 5.7+.

    confidence
        Trust that this *explanation* is correct (independent of probability).

    probability
        Estimated likelihood of the *event/outcome*. Defaults to None.
        Never copied from confidence. Prediction Engine owns this later.

    probability_source
        Defaults to UNKNOWN until Prediction (or explicit metadata) sets it.

    traceability_score
        0–100 strength of support from validated evidence, validation status,
        chain completeness, and source quality. Independent of probability.
        Does not use probability as an input.
    """

    model_config = ConfigDict(extra="allow")

    root_cause_id: str
    schema_version: str = RCA_SCHEMA_VERSION
    title: str
    summary: str
    description: str
    cause_category: CauseCategory = CauseCategory.other
    severity: CauseSeverity = CauseSeverity.info
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Trust in the explanation; never used as probability.",
    )
    probability: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Event likelihood. Default None. Never copied from confidence.",
    )
    probability_source: ProbabilitySource = Field(
        default=ProbabilitySource.unknown,
        description="How probability was obtained. Default unknown.",
    )
    cause_origin: CauseOrigin = Field(
        default=CauseOrigin.insight,
        description="INSIGHT | DECISION | EVIDENCE | METADATA | MIXED",
    )
    business_area: str = ""
    affected_metrics: list[str] = Field(default_factory=list)
    affected_dimensions: list[str] = Field(default_factory=list)
    related_kpis: list[str] = Field(default_factory=list)
    related_charts: list[str] = Field(default_factory=list)
    supporting_evidence: list[CauseEvidence] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    business_impact: str = ""
    source_insight_id: str = ""
    source_decision_id: str = ""
    cause_score: float = Field(default=0.0, ge=0.0, le=100.0)
    cause_rank: int | None = None
    is_primary: bool = False
    traceability_score: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Evidence/validation/chain support score; independent of probability.",
    )
    status: CauseStatus = CauseStatus.inconclusive
    validation_status: ValidationStatus = ValidationStatus.pending
    generated_at: str
    metadata: CauseMetadata = Field(default_factory=CauseMetadata)


class CauseSummary(BaseModel):
    top_cause: str = ""
    top_risks: list[str] = Field(default_factory=list)
    contributing_factors: list[str] = Field(default_factory=list)
    quick_fixes: list[str] = Field(default_factory=list)
    long_term_improvements: list[str] = Field(default_factory=list)
    data_quality_issues: list[str] = Field(default_factory=list)
    primary_cause_id: str | None = None
    total_causes: int = 0
    identified_count: int = 0
    inconclusive_count: int = 0
    blocked_count: int = 0


class RootCauseCollection(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_version: str = RCA_SCHEMA_VERSION
    dataset_id: str | None = None
    domain: str | None = None
    root_causes: list[RootCause] = Field(default_factory=list)
    chains: list[CauseChain] = Field(default_factory=list)
    summary: CauseSummary = Field(default_factory=CauseSummary)
    generated_at: str
    metadata: CauseMetadata = Field(default_factory=CauseMetadata)


def severity_from_risk(risk_level: RiskLevel) -> CauseSeverity:
    mapping = {
        RiskLevel.info: CauseSeverity.info,
        RiskLevel.low: CauseSeverity.low,
        RiskLevel.medium: CauseSeverity.medium,
        RiskLevel.high: CauseSeverity.high,
        RiskLevel.critical: CauseSeverity.critical,
    }
    return mapping.get(risk_level, CauseSeverity.info)
