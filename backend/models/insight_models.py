from typing import Any
from pydantic import BaseModel


class Insight(BaseModel):
    type: str
    title: str
    message: str
    severity: str = "info"
    metadata: dict[str, Any] = {}


class ExecutiveSummary(BaseModel):
    insight: str
    reason: str
    action: str
    evidence: list[str]
    metrics_snapshot: dict[str, Any]
    confidence: str
    key_findings: list[dict[str, Any]] = []
    risks: list[dict[str, Any]] = []
    opportunities: list[dict[str, Any]] = []
    recommendations: list[dict[str, Any]] = []
    action_plan: list[dict[str, Any]] = []
    ceo_insights: list[dict[str, Any]] = []
    decision_framework: list[dict[str, Any]] = []


class InsightResponse(BaseModel):
    dataset_id: str
    insights: list[Insight]
    executive_summary: ExecutiveSummary | None = None


class QuestionRequest(BaseModel):
    question: str


class QuestionResponse(BaseModel):
    dataset_id: str
    question: str
    answer: str
    supporting_data: dict[str, Any] = {}
    analyst: dict[str, Any] = {}
