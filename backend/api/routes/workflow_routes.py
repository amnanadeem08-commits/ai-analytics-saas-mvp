from __future__ import annotations

from fastapi import APIRouter, Query, status

from backend.api.dependencies import ensure_runtime_ready, get_workflow_engine
from backend.api.error_handlers import map_service_exception, raise_api_error
from backend.api.models.workflow import (
    WorkflowExecuteRequest,
    WorkflowExecuteResponse,
    WorkflowResultsResponse,
    WorkflowStatisticsResponse,
    WorkflowStatusResponse,
)
from backend.models.workflow_models import WorkflowDefinition

router = APIRouter(prefix="/api/v1", tags=["Workflow"])


def _build_analyst_workflow(query: str, *, include_evaluation: bool = True) -> WorkflowDefinition:
    from backend.models.ai_insight_models import utc_now_iso
    from backend.services.workflow_engine_service import make_analyst_stage, make_evaluation_stage

    now = utc_now_iso()
    stages = [
        make_analyst_stage(
            stage_id="analyst",
            query=query,
            execution_order=1,
        )
    ]
    if include_evaluation:
        stages.append(
            make_evaluation_stage(
                stage_id="evaluation",
                dependencies=["analyst"],
                execution_order=2,
            )
        )
    return WorkflowDefinition(
        workflow_id=f"api_wf_{now.replace(':', '').replace('-', '')}",
        workflow_name="API Analyst Workflow",
        stages=stages,
        stop_on_error=False,
        created_at=now,
        metadata={"source": "api_gateway", "query": query},
    )


@router.post(
    "/workflow/execute",
    response_model=WorkflowExecuteResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute a workflow",
    description=(
        "Executes either an orchestrator-derived workflow (default) or an analyst "
        "shortcut pipeline when `query` is provided. Returns execution identifiers "
        "and a summary. Does not embed business logic in the route."
    ),
    responses={
        200: {"description": "Workflow executed"},
        400: {"description": "Invalid workflow request"},
    },
)
def execute_workflow_endpoint(request: WorkflowExecuteRequest) -> WorkflowExecuteResponse:
    try:
        ensure_runtime_ready()
        engine = get_workflow_engine()
        if request.query:
            definition = _build_analyst_workflow(
                request.query,
                include_evaluation=request.include_evaluation,
            )
            initial = dict(request.initial_context or {})
            initial.setdefault("user_query", request.query)
            if request.dataset_id:
                initial.setdefault("dataset_id", request.dataset_id)
            if request.domain:
                initial.setdefault("domain", request.domain)
            execution, _ctx = engine.execute_workflow(
                definition,
                initial_context=initial,
                dataset_id=request.dataset_id,
                domain=request.domain,
                stop_on_error=False,
            )
        else:
            definition = engine.build_workflow_definition(
                workflow_name=request.workflow_name,
                stage_ids=request.stage_ids,
                stop_on_error=request.stop_on_error,
            )
            execution, _ctx = engine.execute_workflow(
                definition,
                initial_context=request.initial_context,
                dataset_id=request.dataset_id,
                domain=request.domain,
                stop_on_error=request.stop_on_error,
            )
        summary = engine.workflow_summary(execution)
        return WorkflowExecuteResponse(
            success=True,
            execution_id=execution.execution_id,
            workflow_id=execution.workflow_id,
            workflow_name=execution.workflow_name,
            status=execution.status.value if hasattr(execution.status, "value") else str(execution.status),
            duration_ms=execution.duration_ms,
            summary=summary.model_dump(),
            context_keys=list(execution.context_keys),
            metadata={"schema_version": execution.schema_version},
        )
    except Exception as exc:
        raise map_service_exception(exc) from exc


@router.get(
    "/workflow/status/{execution_id}",
    response_model=WorkflowStatusResponse,
    summary="Get workflow execution status",
    description="Returns status and stage counters for a completed or stored execution.",
    responses={
        200: {"description": "Status found"},
        404: {"description": "Execution not found"},
    },
)
def workflow_status(execution_id: str) -> WorkflowStatusResponse:
    try:
        engine = get_workflow_engine()
        execution = engine.get_execution(execution_id)
        if execution is None:
            raise_api_error(404, f"Workflow execution not found: {execution_id}")
        assert execution is not None
        stats = engine.workflow_statistics(execution)
        return WorkflowStatusResponse(
            success=True,
            execution_id=execution.execution_id,
            workflow_id=execution.workflow_id,
            workflow_name=execution.workflow_name,
            status=execution.status.value if hasattr(execution.status, "value") else str(execution.status),
            started_at=execution.started_at,
            finished_at=execution.finished_at,
            duration_ms=execution.duration_ms,
            completed_stages=stats.completed_stages,
            failed_stages=stats.failed_stages,
            error_count=stats.error_count,
        )
    except Exception as exc:
        if hasattr(exc, "status_code"):
            raise
        raise map_service_exception(exc) from exc


@router.get(
    "/workflow/results/{execution_id}",
    response_model=WorkflowResultsResponse,
    summary="Get workflow execution results",
    description="Returns stage results, errors, and a sanitized context snapshot.",
    responses={
        200: {"description": "Results found"},
        404: {"description": "Execution not found"},
    },
)
def workflow_results(execution_id: str) -> WorkflowResultsResponse:
    try:
        engine = get_workflow_engine()
        execution = engine.get_execution(execution_id)
        if execution is None:
            raise_api_error(404, f"Workflow execution not found: {execution_id}")
        assert execution is not None
        ctx = engine.get_execution_context(execution_id) or {}
        return WorkflowResultsResponse(
            success=True,
            execution_id=execution.execution_id,
            status=execution.status.value if hasattr(execution.status, "value") else str(execution.status),
            stage_results=[s.model_dump() for s in execution.stage_results],
            context=ctx,
            errors=[e.model_dump() for e in execution.errors],
            context_keys=list(execution.context_keys),
        )
    except Exception as exc:
        if hasattr(exc, "status_code"):
            raise
        raise map_service_exception(exc) from exc


@router.get(
    "/workflow/statistics",
    response_model=WorkflowStatisticsResponse,
    summary="Get workflow statistics",
    description=(
        "When `execution_id` is provided, returns statistics for that run. "
        "Otherwise returns aggregate counters across stored executions."
    ),
    responses={200: {"description": "Statistics returned"}},
)
def workflow_statistics(
    execution_id: str | None = Query(default=None, description="Optional execution id"),
) -> WorkflowStatisticsResponse:
    try:
        engine = get_workflow_engine()
        if execution_id:
            execution = engine.get_execution(execution_id)
            if execution is None:
                raise_api_error(404, f"Workflow execution not found: {execution_id}")
            assert execution is not None
            stats = engine.workflow_statistics(execution)
            return WorkflowStatisticsResponse(
                success=True,
                execution_id=execution.execution_id,
                total_stages=stats.total_stages,
                completed_stages=stats.completed_stages,
                failed_stages=stats.failed_stages,
                skipped_stages=stats.skipped_stages,
                blocked_stages=stats.blocked_stages,
                pending_stages=stats.pending_stages,
                log_count=stats.log_count,
                error_count=stats.error_count,
                execution_count=1,
            )
        executions = engine.list_executions()
        totals = {
            "total_stages": 0,
            "completed_stages": 0,
            "failed_stages": 0,
            "skipped_stages": 0,
            "blocked_stages": 0,
            "pending_stages": 0,
            "log_count": 0,
            "error_count": 0,
        }
        for execution in executions:
            stats = engine.workflow_statistics(execution)
            for key in totals:
                totals[key] += getattr(stats, key)
        return WorkflowStatisticsResponse(
            success=True,
            execution_id=None,
            execution_count=len(executions),
            **totals,
        )
    except Exception as exc:
        if hasattr(exc, "status_code"):
            raise
        raise map_service_exception(exc) from exc
