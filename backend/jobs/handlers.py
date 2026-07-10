from __future__ import annotations

"""Job handlers (Sprint 8.3).

Handlers reuse existing services unchanged. Each handler receives the job
payload and a ``progress`` callback and returns a JSON-serializable result dict.
"""

from typing import Any, Callable

from backend.models.job_models import JobType

# progress(percent: float, message: str, current_step: int, total_steps: int)
ProgressCallback = Callable[..., None]


def _run_analysis(payload: dict[str, Any], progress: ProgressCallback) -> dict[str, Any]:
    from backend.services.ai_analyst_runtime_service import analyze_query

    progress(10.0, "Starting analysis", 1, 3)
    response = analyze_query(
        payload["query"],
        user_context=payload.get("user_context") or {},
        session_id=payload.get("session_id"),
        follow_up=bool(payload.get("follow_up")),
        initial_context=payload.get("initial_context") or None,
    )
    progress(90.0, "Analysis complete", 3, 3)
    return {
        "answer": response.answer,
        "insights": list(response.insights),
        "recommendations": list(response.recommendations),
        "session_id": response.metadata.get("session_id"),
        "workflow_id": response.metadata.get("workflow_id"),
        "evaluation_id": response.metadata.get("evaluation_id"),
        "evaluation_grade": response.metadata.get("evaluation_grade"),
        "validation_status": response.validation_status,
    }


def _run_workflow_execution(payload: dict[str, Any], progress: ProgressCallback) -> dict[str, Any]:
    from backend.models.ai_insight_models import utc_now_iso
    from backend.models.workflow_models import WorkflowDefinition
    from backend.services.workflow_engine_service import (
        execute_workflow,
        make_analyst_stage,
        make_evaluation_stage,
        workflow_summary,
    )

    query = str(payload.get("query") or "Analyze available intelligence context")
    progress(10.0, "Building workflow", 1, 3)
    now = utc_now_iso()
    stages = [make_analyst_stage(stage_id="analyst", query=query, execution_order=1)]
    if payload.get("include_evaluation", True):
        stages.append(make_evaluation_stage(stage_id="evaluation", dependencies=["analyst"], execution_order=2))
    definition = WorkflowDefinition(
        workflow_id=f"job_wf_{now.replace(':', '').replace('-', '')}",
        workflow_name="Async Analyst Workflow",
        stages=stages,
        stop_on_error=False,
        created_at=now,
        metadata={"source": "job"},
    )
    progress(40.0, "Executing workflow", 2, 3)
    initial = {"user_query": query}
    if payload.get("dataset_id"):
        initial["dataset_id"] = payload["dataset_id"]
    execution, ctx = execute_workflow(
        definition,
        initial_context=initial,
        dataset_id=payload.get("dataset_id"),
        stop_on_error=False,
    )
    progress(95.0, "Workflow complete", 3, 3)
    summary = workflow_summary(execution)
    return {
        "execution_id": execution.execution_id,
        "workflow_id": execution.workflow_id,
        "status": execution.status.value if hasattr(execution.status, "value") else str(execution.status),
        "summary": summary.model_dump(),
        "evaluation_id": ctx.get("evaluation_id"),
        "evaluation_grade": ctx.get("evaluation_grade"),
    }


def _run_evaluation(payload: dict[str, Any], progress: ProgressCallback) -> dict[str, Any]:
    from backend.services.ai_analyst_runtime_service import get_session
    from backend.services.evaluation_service import evaluate_session

    session_id = str(payload.get("session_id") or "")
    progress(20.0, "Loading session", 1, 2)
    session = get_session(session_id)
    if session is None:
        raise ValueError(f"Analyst session not found: {session_id}")
    run = evaluate_session(session, weights=payload.get("weights") or None)
    progress(95.0, "Evaluation complete", 2, 2)
    return {
        "evaluation_id": run.evaluation_id,
        "session_id": run.session_id,
        "overall_score": run.overall_score,
        "grade": run.grade,
    }


def _run_knowledge_ingestion(payload: dict[str, Any], progress: ProgressCallback) -> dict[str, Any]:
    from backend.services.knowledge_ingestion_service import ingest_document

    progress(20.0, "Validating document", 1, 2)
    doc, chunks = ingest_document(
        title=payload["title"],
        content=payload.get("content", ""),
        source=payload.get("source", "text"),
        tags=payload.get("tags") or [],
        metadata=payload.get("metadata") or {},
        document_id=payload.get("document_id"),
        index=bool(payload.get("index", True)),
        storage_object_id=payload.get("storage_object_id"),
    )
    progress(95.0, "Ingestion complete", 2, 2)
    return {"document_id": doc.document_id, "title": doc.title, "chunk_count": len(chunks)}


def _run_generic(payload: dict[str, Any], progress: ProgressCallback) -> dict[str, Any]:
    """A no-op echo handler useful for testing the job lifecycle."""
    steps = int(payload.get("steps", 1) or 1)
    for i in range(1, steps + 1):
        progress(100.0 * i / steps, f"step {i}/{steps}", i, steps)
    if payload.get("fail"):
        raise RuntimeError(str(payload.get("fail_message", "intentional failure")))
    return {"echo": payload.get("echo", ""), "steps": steps}


_HANDLERS: dict[JobType, Callable[[dict[str, Any], ProgressCallback], dict[str, Any]]] = {
    JobType.analysis: _run_analysis,
    JobType.workflow_execution: _run_workflow_execution,
    JobType.evaluation: _run_evaluation,
    JobType.knowledge_ingestion: _run_knowledge_ingestion,
    JobType.generic: _run_generic,
}


def get_handler(job_type: JobType) -> Callable[[dict[str, Any], ProgressCallback], dict[str, Any]]:
    handler = _HANDLERS.get(job_type)
    if handler is None:
        raise ValueError(f"No handler registered for job type: {job_type}")
    return handler


def register_handler(job_type: JobType, handler: Callable[[dict[str, Any], ProgressCallback], dict[str, Any]]) -> None:
    _HANDLERS[job_type] = handler
