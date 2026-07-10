from __future__ import annotations

from fastapi import APIRouter, status

from backend.api.dependencies import ensure_runtime_ready, get_analyst_runtime
from backend.api.error_handlers import map_service_exception, raise_api_error
from backend.api.models.analyst import (
    AnalystAnalyzeRequest,
    AnalystAnalyzeResponse,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionDetailResponse,
    SessionExecuteRequest,
    SessionSummaryResponse,
)
from backend.api.models.evaluation import EvaluationDetailResponse
from backend.models.analyst_models import AnalystRequest

router = APIRouter(prefix="/api/v1", tags=["AI Analyst"])


@router.post(
    "/analyst/analyze",
    response_model=AnalystAnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze a query with the AI Analyst runtime",
    description=(
        "Creates or continues an analyst session, runs memory/RAG/workflow "
        "orchestration, and returns a structured analyst response. "
        "Evaluation metadata is attached when available without altering the answer."
    ),
    responses={
        200: {"description": "Analysis completed"},
        400: {"description": "Invalid request"},
        500: {"description": "Service failure"},
    },
)
def analyze(request: AnalystAnalyzeRequest) -> AnalystAnalyzeResponse:
    try:
        ensure_runtime_ready()
        runtime = get_analyst_runtime()
        result = runtime.analyze_query(
            request.query,
            user_context=request.user_context,
            session_id=request.session_id,
            follow_up=request.follow_up,
            initial_context=request.initial_context or None,
        )
        meta = dict(result.metadata or {})
        return AnalystAnalyzeResponse(
            success=True,
            answer=result.answer,
            insights=list(result.insights),
            recommendations=list(result.recommendations),
            session_id=meta.get("session_id"),
            workflow_id=meta.get("workflow_id"),
            validation_status=result.validation_status,
            provider=result.provider,
            evaluation_id=meta.get("evaluation_id"),
            evaluation_score=meta.get("evaluation_score"),
            evaluation_grade=meta.get("evaluation_grade"),
            workflow_results=dict(result.workflow_results or {}),
            metadata=meta,
        )
    except Exception as exc:
        raise map_service_exception(exc) from exc


@router.post(
    "/session/create",
    response_model=SessionCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an AI Analyst session",
    description="Creates a new analyst session without executing analysis.",
    responses={
        201: {"description": "Session created"},
        400: {"description": "Invalid request"},
    },
)
def create_session(request: SessionCreateRequest) -> SessionCreateResponse:
    try:
        ensure_runtime_ready()
        runtime = get_analyst_runtime()
        session = runtime.create_session(
            AnalystRequest(
                query=request.query,
                user_context=request.user_context,
                session_id=request.session_id,
                follow_up=request.follow_up,
                metadata=request.metadata,
            )
        )
        return SessionCreateResponse(
            success=True,
            session_id=session.session_id,
            user_query=session.user_query,
            status=session.status.value if hasattr(session.status, "value") else str(session.status),
            created_at=session.created_at,
            metadata=dict(session.metadata or {}),
        )
    except Exception as exc:
        raise map_service_exception(exc) from exc


@router.get(
    "/session/{session_id}",
    response_model=SessionDetailResponse,
    summary="Get analyst session details",
    description="Returns the full analyst session record including result when present.",
    responses={
        200: {"description": "Session found"},
        404: {"description": "Session not found"},
    },
)
def get_session(session_id: str) -> SessionDetailResponse:
    try:
        runtime = get_analyst_runtime()
        session = runtime.get_session(session_id)
        if session is None:
            raise_api_error(404, f"Session not found: {session_id}")
        assert session is not None
        return SessionDetailResponse(
            success=True,
            session_id=session.session_id,
            user_query=session.user_query,
            status=session.status.value if hasattr(session.status, "value") else str(session.status),
            workflow_id=session.workflow_id,
            context=dict(session.context or {}),
            result=session.result.model_dump() if session.result else None,
            previous_queries=list(session.previous_queries),
            previous_results=list(session.previous_results),
            created_at=session.created_at,
            updated_at=session.updated_at,
            metadata=dict(session.metadata or {}),
        )
    except Exception as exc:
        if hasattr(exc, "status_code"):
            raise
        raise map_service_exception(exc) from exc


@router.get(
    "/session/{session_id}/summary",
    response_model=SessionSummaryResponse,
    summary="Get analyst session summary",
    description="Returns a compact summary of an analyst session.",
    responses={
        200: {"description": "Summary returned"},
        404: {"description": "Session not found"},
    },
)
def get_session_summary(session_id: str) -> SessionSummaryResponse:
    try:
        runtime = get_analyst_runtime()
        summary = runtime.session_summary(session_id)
        if not summary.get("found"):
            raise_api_error(404, f"Session not found: {session_id}")
        session = runtime.get_session(session_id)
        evaluation_id = None
        evaluation_grade = None
        if session is not None:
            evaluation_id = (session.metadata or {}).get("evaluation_id")
            evaluation_grade = (session.metadata or {}).get("evaluation_grade")
        return SessionSummaryResponse(success=True, **summary, evaluation_id=evaluation_id, evaluation_grade=evaluation_grade)
    except Exception as exc:
        if hasattr(exc, "status_code"):
            raise
        raise map_service_exception(exc) from exc


@router.get(
    "/session/{session_id}/evaluation",
    response_model=EvaluationDetailResponse,
    summary="Get evaluation for an analyst session",
    description="Returns the latest evaluation run linked to the given session_id.",
    responses={
        200: {"description": "Evaluation found"},
        404: {"description": "Session or evaluation not found"},
    },
)
def get_session_evaluation(session_id: str) -> EvaluationDetailResponse:
    try:
        from backend.api.dependencies import get_evaluation_service

        runtime = get_analyst_runtime()
        if runtime.get_session(session_id) is None:
            raise_api_error(404, f"Session not found: {session_id}")
        eval_svc = get_evaluation_service()
        run = eval_svc.latest_evaluation_for_session(session_id)
        if run is None:
            # Fall back to session metadata evaluation_id
            session = runtime.get_session(session_id)
            eid = (session.metadata or {}).get("evaluation_id") if session else None
            if eid:
                run = eval_svc.get_evaluation(str(eid))
        if run is None:
            raise_api_error(404, f"Evaluation not found for session: {session_id}")
        assert run is not None
        return EvaluationDetailResponse(
            success=True,
            evaluation_id=run.evaluation_id,
            workflow_id=run.workflow_id,
            session_id=run.session_id,
            status=run.status.value if hasattr(run.status, "value") else str(run.status),
            overall_score=run.overall_score,
            grade=run.grade,
            report=run.report.model_dump() if run.report else {},
            metrics=[m.model_dump() for m in run.metrics],
            category_scores=dict(run.category_scores),
            created_at=run.created_at,
        )
    except Exception as exc:
        if hasattr(exc, "status_code"):
            raise
        raise map_service_exception(exc) from exc


@router.post(
    "/session/{session_id}/execute",
    response_model=AnalystAnalyzeResponse,
    summary="Execute analysis for an existing session",
    description="Runs the AI Analyst runtime against an existing session_id.",
    responses={
        200: {"description": "Analysis completed"},
        404: {"description": "Session not found"},
    },
)
def execute_session(
    session_id: str,
    request: SessionExecuteRequest | None = None,
) -> AnalystAnalyzeResponse:
    try:
        ensure_runtime_ready()
        runtime = get_analyst_runtime()
        if runtime.get_session(session_id) is None:
            raise_api_error(404, f"Session not found: {session_id}")
        initial_context = dict(request.initial_context) if request and request.initial_context else None
        completed = runtime.execute_analysis(session_id, initial_context=initial_context)
        result = completed.result
        if result is None:
            raise_api_error(500, "Analysis completed without a result")
        assert result is not None
        meta = {
            **dict(result.metadata or {}),
            "session_id": completed.session_id,
            "workflow_id": completed.workflow_id,
            "evaluation_id": completed.metadata.get("evaluation_id"),
            "evaluation_score": completed.metadata.get("evaluation_score"),
            "evaluation_grade": completed.metadata.get("evaluation_grade"),
        }
        return AnalystAnalyzeResponse(
            success=True,
            answer=result.answer,
            insights=list(result.insights),
            recommendations=list(result.recommendations),
            session_id=completed.session_id,
            workflow_id=completed.workflow_id,
            validation_status=result.validation_status,
            provider=result.provider,
            evaluation_id=meta.get("evaluation_id"),
            evaluation_score=meta.get("evaluation_score"),
            evaluation_grade=meta.get("evaluation_grade"),
            workflow_results=dict(result.workflow_results or {}),
            metadata=meta,
        )
    except Exception as exc:
        if hasattr(exc, "status_code"):
            raise
        raise map_service_exception(exc) from exc
