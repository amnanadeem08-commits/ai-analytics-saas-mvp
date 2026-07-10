from __future__ import annotations

from fastapi import APIRouter, status

from backend.api.dependencies import get_evaluation_service, get_analyst_runtime
from backend.api.error_handlers import map_service_exception, raise_api_error
from backend.api.models.evaluation import (
    EvaluationDetailResponse,
    EvaluationExportResponse,
    EvaluationRequest,
    EvaluationResponse,
    ScoreSummary,
)

router = APIRouter(prefix="/api/v1", tags=["Evaluation"])


def _to_response(run) -> EvaluationResponse:
    return EvaluationResponse(
        success=True,
        evaluation_id=run.evaluation_id,
        workflow_id=run.workflow_id,
        session_id=run.session_id,
        status=run.status.value if hasattr(run.status, "value") else str(run.status),
        overall_score=run.overall_score,
        grade=run.grade,
        score_summary=ScoreSummary(
            overall_score=run.overall_score,
            grade=run.grade,
            category_scores=dict(run.category_scores),
            metric_count=len(run.metrics),
        ),
        created_at=run.created_at,
    )


def _to_detail(run) -> EvaluationDetailResponse:
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


@router.post(
    "/evaluation/run",
    response_model=EvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate a completed analyst session",
    description=(
        "Runs read-only evaluation against a completed session. "
        "Never mutates the original analysis result."
    ),
    responses={
        200: {"description": "Evaluation completed"},
        404: {"description": "Session not found"},
    },
)
def run_evaluation(request: EvaluationRequest) -> EvaluationResponse:
    try:
        if not request.session_id:
            raise_api_error(400, "session_id is required")
        runtime = get_analyst_runtime()
        session = runtime.get_session(request.session_id)
        if session is None:
            raise_api_error(404, f"Session not found: {request.session_id}")
        assert session is not None
        eval_svc = get_evaluation_service()
        run = eval_svc.evaluate_session(
            session,
            weights=request.weights or None,
        )
        return _to_response(run)
    except Exception as exc:
        if hasattr(exc, "status_code"):
            raise
        raise map_service_exception(exc) from exc


@router.get(
    "/evaluation/session/{session_id}",
    response_model=EvaluationResponse,
    summary="Get evaluation by session id",
    description="Returns the latest evaluation linked to a session.",
    responses={
        200: {"description": "Evaluation found"},
        404: {"description": "Not found"},
    },
)
def evaluation_by_session(session_id: str) -> EvaluationResponse:
    try:
        eval_svc = get_evaluation_service()
        run = eval_svc.latest_evaluation_for_session(session_id)
        if run is None:
            raise_api_error(404, f"Evaluation not found for session: {session_id}")
        assert run is not None
        return _to_response(run)
    except Exception as exc:
        if hasattr(exc, "status_code"):
            raise
        raise map_service_exception(exc) from exc


@router.get(
    "/evaluation/workflow/{workflow_id}",
    response_model=EvaluationResponse,
    summary="Get evaluation by workflow id",
    description="Returns the latest evaluation linked to a workflow_id.",
    responses={
        200: {"description": "Evaluation found"},
        404: {"description": "Not found"},
    },
)
def evaluation_by_workflow(workflow_id: str) -> EvaluationResponse:
    try:
        eval_svc = get_evaluation_service()
        run = eval_svc.latest_evaluation_for_workflow(workflow_id)
        if run is None:
            raise_api_error(404, f"Evaluation not found for workflow: {workflow_id}")
        assert run is not None
        return _to_response(run)
    except Exception as exc:
        if hasattr(exc, "status_code"):
            raise
        raise map_service_exception(exc) from exc


@router.get(
    "/evaluation/report/{evaluation_id}",
    response_model=EvaluationDetailResponse,
    summary="Get evaluation report",
    description="Returns the full evaluation report and metrics for an evaluation_id.",
    responses={
        200: {"description": "Report found"},
        404: {"description": "Not found"},
    },
)
def evaluation_report(evaluation_id: str) -> EvaluationDetailResponse:
    try:
        eval_svc = get_evaluation_service()
        run = eval_svc.get_evaluation(evaluation_id)
        if run is None:
            raise_api_error(404, f"Evaluation not found: {evaluation_id}")
        assert run is not None
        return _to_detail(run)
    except Exception as exc:
        if hasattr(exc, "status_code"):
            raise
        raise map_service_exception(exc) from exc


@router.get(
    "/evaluation/export/{evaluation_id}",
    response_model=EvaluationExportResponse,
    summary="Export evaluation as JSON",
    description="Returns a JSON-ready evaluation export (report, metrics summary, score breakdown).",
    responses={
        200: {"description": "Export returned"},
        404: {"description": "Not found"},
    },
)
def evaluation_export(evaluation_id: str) -> EvaluationExportResponse:
    try:
        eval_svc = get_evaluation_service()
        run = eval_svc.get_evaluation(evaluation_id)
        if run is None:
            raise_api_error(404, f"Evaluation not found: {evaluation_id}")
        assert run is not None
        export = run.export or eval_svc.export_evaluation(run)
        return EvaluationExportResponse(
            success=True,
            evaluation_id=run.evaluation_id,
            export=export,
        )
    except Exception as exc:
        if hasattr(exc, "status_code"):
            raise
        raise map_service_exception(exc) from exc
