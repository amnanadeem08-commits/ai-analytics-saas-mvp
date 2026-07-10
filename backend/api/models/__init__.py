from __future__ import annotations

"""API request/response models for the Sprint 7.8 gateway.

Pydantic schemas only — no business logic.
"""

from backend.api.models.analyst import (
    AnalystAnalyzeRequest,
    AnalystAnalyzeResponse,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionDetailResponse,
    SessionSummaryResponse,
)
from backend.api.models.evaluation import (
    EvaluationDetailResponse,
    EvaluationExportResponse,
    EvaluationRequest,
    EvaluationResponse,
    ScoreSummary,
)
from backend.api.models.knowledge import (
    KnowledgeDocumentRequest,
    KnowledgeDocumentResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from backend.api.models.system import (
    CapabilitiesResponse,
    HealthResponse,
    VersionResponse,
)
from backend.api.models.workflow import (
    WorkflowExecuteRequest,
    WorkflowExecuteResponse,
    WorkflowResultsResponse,
    WorkflowStatisticsResponse,
    WorkflowStatusResponse,
)

__all__ = [
    "AnalystAnalyzeRequest",
    "AnalystAnalyzeResponse",
    "SessionCreateRequest",
    "SessionCreateResponse",
    "SessionDetailResponse",
    "SessionSummaryResponse",
    "WorkflowExecuteRequest",
    "WorkflowExecuteResponse",
    "WorkflowStatusResponse",
    "WorkflowResultsResponse",
    "WorkflowStatisticsResponse",
    "EvaluationRequest",
    "EvaluationResponse",
    "EvaluationDetailResponse",
    "EvaluationExportResponse",
    "ScoreSummary",
    "KnowledgeDocumentRequest",
    "KnowledgeDocumentResponse",
    "KnowledgeSearchRequest",
    "KnowledgeSearchResponse",
    "HealthResponse",
    "VersionResponse",
    "CapabilitiesResponse",
]
