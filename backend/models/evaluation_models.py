from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

EVALUATION_SCHEMA_VERSION = "1.0.0"

EVALUATION_FUTURE_EXTENSION_KEYS: tuple[str, ...] = (
    "rest_api",
    "ui",
    "online_learning",
    "prompt_optimization",
    "model_tuning",
    "autonomous_workflow_changes",
)


def empty_evaluation_future_extensions() -> dict[str, dict[str, Any]]:
    return {key: {} for key in EVALUATION_FUTURE_EXTENSION_KEYS}


class EvaluationStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    skipped = "skipped"


class EvaluationCategory(str, Enum):
    workflow = "workflow"
    agents = "agents"
    tools = "tools"
    memory = "memory"
    rag = "rag"
    llm = "llm"
    final_response = "final_response"


class EvaluationGrade(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"


class EvaluationMetric(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    category: EvaluationCategory | str
    score: float = 0.0
    weight: float = 1.0
    explanation: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluationReport(BaseModel):
    model_config = ConfigDict(extra="allow")

    summary: str = ""
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    metrics: list[EvaluationMetric] = Field(default_factory=list)
    grade: str = ""
    overall_score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluationRun(BaseModel):
    """Read-only evaluation of a completed workflow/session. Never mutates execution."""

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    evaluation_id: str
    workflow_id: str = ""
    session_id: str = ""
    created_at: str = ""
    overall_score: float = 0.0
    grade: str = EvaluationGrade.F.value
    status: EvaluationStatus = EvaluationStatus.pending
    report: EvaluationReport | None = None
    metrics: list[EvaluationMetric] = Field(default_factory=list)
    category_scores: dict[str, float] = Field(default_factory=dict)
    export: dict[str, Any] = Field(default_factory=dict)
    schema_version: str = EVALUATION_SCHEMA_VERSION
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScoreBreakdown(BaseModel):
    model_config = ConfigDict(extra="allow")

    overall_score: float = 0.0
    grade: str = EvaluationGrade.F.value
    normalized_scores: dict[str, float] = Field(default_factory=dict)
    weighted_contribution: dict[str, float] = Field(default_factory=dict)
    weights_used: dict[str, float] = Field(default_factory=dict)
