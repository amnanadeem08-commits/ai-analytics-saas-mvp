from __future__ import annotations

from typing import Any, Mapping

from backend.models.ai_insight_models import utc_now_iso
from backend.models.evaluation_models import (
    EVALUATION_SCHEMA_VERSION,
    EvaluationCategory,
    EvaluationMetric,
    EvaluationReport,
    EvaluationRun,
    EvaluationStatus,
    empty_evaluation_future_extensions,
)
from backend.services.evaluation_report_service import build_evaluation_report
from backend.services.scoring_service import (
    average_metric_scores,
    calculate_weighted_score,
    clamp_score,
)

_EVALUATION_STORE: dict[str, EvaluationRun] = {}


def clear_evaluations() -> None:
    global _EVALUATION_STORE
    _EVALUATION_STORE = {}


def get_evaluation(evaluation_id: str) -> EvaluationRun | None:
    item = _EVALUATION_STORE.get(evaluation_id)
    return item.model_copy(deep=True) if item is not None else None


def list_evaluations() -> list[EvaluationRun]:
    return [item.model_copy(deep=True) for item in _EVALUATION_STORE.values()]


def find_evaluations_by_session(session_id: str) -> list[EvaluationRun]:
    sid = str(session_id or "")
    return [
        item.model_copy(deep=True)
        for item in _EVALUATION_STORE.values()
        if item.session_id == sid
    ]


def find_evaluations_by_workflow(workflow_id: str) -> list[EvaluationRun]:
    wid = str(workflow_id or "")
    return [
        item.model_copy(deep=True)
        for item in _EVALUATION_STORE.values()
        if item.workflow_id == wid
    ]


def latest_evaluation_for_session(session_id: str) -> EvaluationRun | None:
    items = find_evaluations_by_session(session_id)
    if not items:
        return None
    items.sort(key=lambda r: r.created_at, reverse=True)
    return items[0]


def latest_evaluation_for_workflow(workflow_id: str) -> EvaluationRun | None:
    items = find_evaluations_by_workflow(workflow_id)
    if not items:
        return None
    items.sort(key=lambda r: r.created_at, reverse=True)
    return items[0]


def _metric(
    name: str,
    category: EvaluationCategory,
    score: float,
    *,
    weight: float = 1.0,
    explanation: str = "",
    **metadata: Any,
) -> EvaluationMetric:
    return EvaluationMetric(
        name=name,
        category=category,
        score=clamp_score(score),
        weight=weight,
        explanation=explanation,
        metadata=dict(metadata),
    )


def _as_dict(obj: Any) -> dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return dict(obj)
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return {}


def _status_str(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def evaluate_workflow(artifact: Mapping[str, Any] | Any) -> list[EvaluationMetric]:
    """Score workflow completion, failure rate, and retries from completed artifacts."""
    data = _as_dict(artifact)
    execution = _as_dict(data.get("execution") or data.get("workflow_execution") or data)
    stage_results = list(
        execution.get("stage_results")
        or data.get("stage_results")
        or []
    )
    errors = list(execution.get("errors") or data.get("errors") or [])
    status = _status_str(execution.get("status") or data.get("status")).lower()

    total = len(stage_results)
    completed = 0
    failed = 0
    retries = 0
    for stage in stage_results:
        s = _as_dict(stage)
        st = _status_str(s.get("status")).lower()
        if st == "completed":
            completed += 1
        elif st in {"failed", "blocked"}:
            failed += 1
        retries += int((_as_dict(s.get("metadata")).get("retry_count") or 0))

    if total == 0 and status in {"completed", "partial"}:
        # Session workflow_results may only expose stage_count / status.
        stage_count = int(data.get("stage_count") or 0)
        if stage_count > 0:
            total = stage_count
            completed = stage_count if status == "completed" else max(0, stage_count - 1)
            failed = 0 if status == "completed" else 1

    completion = (completed / total) if total else (1.0 if status == "completed" else 0.0)
    failure_rate = 1.0 - ((failed / total) if total else (0.0 if status == "completed" else 1.0))
    # Fewer retries → higher score. Cap at 5 retries for normalization.
    retry_score = clamp_score(1.0 - (retries / 5.0))
    if status == "failed":
        completion = min(completion, 0.3)
        failure_rate = min(failure_rate, 0.3)

    return [
        _metric(
            "completion",
            EvaluationCategory.workflow,
            completion,
            explanation=f"{completed}/{total or 'n'} stages completed; status={status or 'unknown'}",
            completed=completed,
            total=total,
            status=status,
        ),
        _metric(
            "failure_rate",
            EvaluationCategory.workflow,
            failure_rate,
            explanation=f"{failed} failed/blocked stages; {len(errors)} workflow errors",
            failed=failed,
            error_count=len(errors),
        ),
        _metric(
            "retries",
            EvaluationCategory.workflow,
            retry_score,
            explanation=f"{retries} recorded stage retries",
            retries=retries,
        ),
    ]


def evaluate_agents(artifact: Mapping[str, Any] | Any) -> list[EvaluationMetric]:
    data = _as_dict(artifact)
    executions = list(
        data.get("agent_executions")
        or _as_dict(data.get("workflow_results")).get("agent_executions")
        or []
    )
    agent_results = data.get("agent_results") or _as_dict(data.get("workflow_results")).get(
        "agent_results"
    ) or {}
    plan = _as_dict(data.get("plan_result") or _as_dict(data.get("workflow_results")).get("plan_result"))

    total = len(executions)
    successes = 0
    for ex in executions:
        e = _as_dict(ex)
        st = _status_str(e.get("status")).lower()
        if st == "completed" and not e.get("error_message"):
            successes += 1
        elif st == "completed":
            successes += 1

    if total == 0 and agent_results:
        total = len(agent_results)
        successes = sum(1 for v in agent_results.values() if v)

    completion = (successes / total) if total else (0.5 if plan else 0.0)
    success_rate = completion

    # Planning quality: presence of steps + validated flag / step count.
    steps = plan.get("steps") or plan.get("plan_steps") or []
    if isinstance(steps, dict):
        steps = list(steps.values())
    step_count = len(steps) if isinstance(steps, list) else 0
    validated = bool(plan.get("validated") or plan.get("valid") or plan.get("status") == "validated")
    if step_count >= 2 and validated:
        planning_quality = 0.95
    elif step_count >= 2:
        planning_quality = 0.8
    elif step_count == 1:
        planning_quality = 0.65
    elif plan:
        planning_quality = 0.4
    else:
        planning_quality = 0.2 if total else 0.0

    return [
        _metric(
            "completion",
            EvaluationCategory.agents,
            completion,
            explanation=f"{successes}/{total or 0} agent executions completed",
            successes=successes,
            total=total,
        ),
        _metric(
            "success_rate",
            EvaluationCategory.agents,
            success_rate,
            explanation=f"Agent success rate {success_rate:.2f}",
        ),
        _metric(
            "planning_quality",
            EvaluationCategory.agents,
            planning_quality,
            explanation=f"Plan steps={step_count}, validated={validated}",
            step_count=step_count,
            validated=validated,
        ),
    ]


def evaluate_tools(artifact: Mapping[str, Any] | Any) -> list[EvaluationMetric]:
    data = _as_dict(artifact)
    executions = list(
        data.get("agent_executions")
        or _as_dict(data.get("workflow_results")).get("agent_executions")
        or []
    )
    tool_calls = 0
    tool_successes = 0
    fallback_count = 0
    selected_tools: list[str] = []

    for ex in executions:
        e = _as_dict(ex)
        meta = _as_dict(e.get("metadata"))
        result = _as_dict(e.get("result"))
        req_ids = list(e.get("tool_request_ids") or [])
        tool_calls += len(req_ids)
        selected_tools.extend(req_ids)
        if meta.get("fallback") or result.get("fallback"):
            fallback_count += 1
        tool_results = result.get("tool_results") or meta.get("tool_results") or []
        if isinstance(tool_results, list):
            for tr in tool_results:
                t = _as_dict(tr)
                tool_calls += 1
                if not t.get("error") and _status_str(t.get("status")).lower() not in {
                    "failed",
                    "error",
                }:
                    tool_successes += 1
        elif req_ids and _status_str(e.get("status")).lower() == "completed":
            tool_successes += len(req_ids)

    plan = _as_dict(data.get("plan_result") or _as_dict(data.get("workflow_results")).get("plan_result"))
    planned_tools = []
    for step in plan.get("steps") or []:
        s = _as_dict(step)
        if s.get("tool_name"):
            planned_tools.append(str(s["tool_name"]))

    if tool_calls == 0 and planned_tools:
        # Plan selected tools but no detailed call log — partial credit.
        correct_selection = 0.7
        execution_success = 0.6
    elif tool_calls == 0:
        correct_selection = 0.3
        execution_success = 0.3
    else:
        execution_success = tool_successes / tool_calls
        if planned_tools:
            overlap = len(set(planned_tools).intersection(set(selected_tools))) if selected_tools else 0
            correct_selection = clamp_score(
                (overlap / len(set(planned_tools))) if planned_tools else execution_success
            )
            if not selected_tools:
                correct_selection = 0.75  # planned tools exist; call IDs may be opaque
        else:
            correct_selection = execution_success

    fallback_score = clamp_score(1.0 - (fallback_count / max(1, tool_calls or 1)))

    return [
        _metric(
            "correct_selection",
            EvaluationCategory.tools,
            correct_selection,
            explanation=f"Planned tools={len(planned_tools)}, recorded calls={tool_calls}",
            planned_tools=planned_tools,
            tool_calls=tool_calls,
        ),
        _metric(
            "execution_success",
            EvaluationCategory.tools,
            execution_success,
            explanation=f"{tool_successes}/{tool_calls or 0} tool executions succeeded",
        ),
        _metric(
            "fallback_usage",
            EvaluationCategory.tools,
            fallback_score,
            explanation=f"{fallback_count} fallback usages observed",
            fallback_count=fallback_count,
        ),
    ]


def evaluate_memory(artifact: Mapping[str, Any] | Any) -> list[EvaluationMetric]:
    data = _as_dict(artifact)
    context = _as_dict(data.get("context") or data)
    memory_ids = list(
        data.get("memory_ids")
        or context.get("memory_ids")
        or _as_dict(data.get("workflow_results")).get("memory_ids")
        or []
    )
    snippets = list(
        data.get("memory_snippets")
        or context.get("memory_snippets")
        or []
    )
    memory_ctx = _as_dict(data.get("memory_context") or context.get("memory_context"))

    retrieval_usefulness = 0.0
    if memory_ids or snippets:
        retrieval_usefulness = clamp_score(0.5 + 0.1 * min(5, len(memory_ids) + len(snippets)))
    elif memory_ctx:
        retrieval_usefulness = 0.4

    context_usage = 0.0
    if snippets or memory_ids:
        context_usage = 0.85 if (data.get("plan_result") or context.get("planning_task")) else 0.7
    elif "memory_context" in context or data.get("memory_context"):
        context_usage = 0.5

    return [
        _metric(
            "retrieval_usefulness",
            EvaluationCategory.memory,
            retrieval_usefulness,
            explanation=f"{len(memory_ids)} memory ids, {len(snippets)} snippets",
            memory_id_count=len(memory_ids),
            snippet_count=len(snippets),
        ),
        _metric(
            "context_usage",
            EvaluationCategory.memory,
            context_usage,
            explanation="Memory context merged into runtime"
            if context_usage >= 0.7
            else "Limited memory context usage",
        ),
    ]


def evaluate_rag(artifact: Mapping[str, Any] | Any) -> list[EvaluationMetric]:
    data = _as_dict(artifact)
    context = _as_dict(data.get("context") or data)
    wr = _as_dict(data.get("workflow_results"))
    chunk_ids = list(
        data.get("rag_chunk_ids")
        or context.get("rag_chunk_ids")
        or wr.get("rag_chunk_ids")
        or []
    )
    snippets = list(data.get("rag_snippets") or context.get("rag_snippets") or [])
    sources = list(data.get("rag_sources") or context.get("rag_sources") or [])
    rag_text = str(data.get("rag_context_text") or context.get("rag_context_text") or "")

    # Relevance from snippet scores when present; else presence-based.
    relevances: list[float] = []
    for snip in snippets:
        s = _as_dict(snip)
        if s.get("relevance") is not None:
            try:
                relevances.append(float(s["relevance"]))
            except (TypeError, ValueError):
                pass
        if s.get("source") and s["source"] not in sources:
            sources.append(s["source"])
        if s.get("document_id") and s["document_id"] not in sources:
            sources.append(s["document_id"])

    if relevances:
        retrieval_relevance = clamp_score(sum(relevances) / len(relevances))
    elif chunk_ids or snippets or rag_text:
        retrieval_relevance = clamp_score(0.55 + 0.08 * min(5, len(chunk_ids) or len(snippets) or 1))
    else:
        retrieval_relevance = 0.0

    unique_sources = len(set(str(s) for s in sources if s))
    if unique_sources >= 3:
        source_diversity = 0.95
    elif unique_sources == 2:
        source_diversity = 0.75
    elif unique_sources == 1:
        source_diversity = 0.55
    elif chunk_ids:
        source_diversity = 0.4
    else:
        source_diversity = 0.0

    if rag_text and len(rag_text) > 40:
        context_quality = 0.9
    elif snippets or chunk_ids:
        context_quality = 0.7
    else:
        context_quality = 0.0

    return [
        _metric(
            "retrieval_relevance",
            EvaluationCategory.rag,
            retrieval_relevance,
            explanation=f"{len(chunk_ids)} chunks, avg_relevance={retrieval_relevance:.2f}",
            chunk_count=len(chunk_ids),
        ),
        _metric(
            "source_diversity",
            EvaluationCategory.rag,
            source_diversity,
            explanation=f"{unique_sources} unique sources",
            source_count=unique_sources,
        ),
        _metric(
            "context_quality",
            EvaluationCategory.rag,
            context_quality,
            explanation="RAG context text present" if rag_text else "RAG context limited or missing",
        ),
    ]


def evaluate_llm(artifact: Mapping[str, Any] | Any) -> list[EvaluationMetric]:
    data = _as_dict(artifact)
    result = _as_dict(data.get("result") or data.get("analyst_response") or data)
    structured = _as_dict(
        result.get("structured_output")
        or data.get("structured_output")
        or data.get("llm_response")
    )
    validation_status = str(
        result.get("validation_status")
        or data.get("validation_status")
        or structured.get("validation_status")
        or "unchecked"
    ).lower()
    understanding = _as_dict(
        data.get("llm_understanding")
        or _as_dict(data.get("context")).get("llm_understanding")
    )

    if validation_status in {"valid", "ok"}:
        structured_validity = 1.0
    elif validation_status in {"repaired"}:
        structured_validity = 0.7
    elif validation_status in {"invalid"}:
        structured_validity = 0.2
    elif structured:
        structured_validity = 0.6
    else:
        structured_validity = 0.3

    required = ("answer", "insights", "recommendations")
    present = sum(1 for k in required if structured.get(k) not in (None, "", []))
    if present == 0 and result.get("answer"):
        # Final response fields may live outside structured_output.
        present = sum(
            1
            for k in required
            if result.get(k) not in (None, "", [])
        )
    schema_compliance = present / len(required)

    # Rule-based hallucination indicators (no model calls).
    answer = str(result.get("answer") or structured.get("answer") or "")
    rag_ids = list(
        data.get("rag_chunk_ids")
        or _as_dict(data.get("context")).get("rag_chunk_ids")
        or _as_dict(data.get("workflow_results")).get("rag_chunk_ids")
        or result.get("metadata", {}).get("rag_chunk_ids")
        or []
    )
    indicators = 0
    if answer and not rag_ids and not result.get("insights"):
        indicators += 1
    if "analysis failed" in answer.lower():
        indicators += 1
    if understanding.get("understanding") and answer and len(answer) < 5:
        indicators += 1
    hallucination_score = clamp_score(1.0 - 0.35 * indicators)

    return [
        _metric(
            "structured_output_validity",
            EvaluationCategory.llm,
            structured_validity,
            explanation=f"validation_status={validation_status}",
            validation_status=validation_status,
        ),
        _metric(
            "schema_compliance",
            EvaluationCategory.llm,
            schema_compliance,
            explanation=f"{present}/{len(required)} required response fields present",
        ),
        _metric(
            "hallucination_indicators",
            EvaluationCategory.llm,
            hallucination_score,
            explanation=f"{indicators} rule-based risk indicators",
            indicator_count=indicators,
        ),
    ]


def evaluate_final_response(artifact: Mapping[str, Any] | Any) -> list[EvaluationMetric]:
    data = _as_dict(artifact)
    result = _as_dict(data.get("result") or data.get("analyst_response") or data)
    answer = str(result.get("answer") or "").strip()
    insights = result.get("insights") if isinstance(result.get("insights"), list) else []
    recommendations = (
        result.get("recommendations")
        if isinstance(result.get("recommendations"), list)
        else []
    )

    completeness_parts = [
        1.0 if answer else 0.0,
        1.0 if insights else 0.0,
        1.0 if recommendations else 0.0,
    ]
    completeness = sum(completeness_parts) / len(completeness_parts)

    wr = _as_dict(result.get("workflow_results") or data.get("workflow_results"))
    rag_ids = list(
        _as_dict(result.get("metadata")).get("rag_chunk_ids")
        or wr.get("rag_chunk_ids")
        or data.get("rag_chunk_ids")
        or []
    )
    consistency = 0.5
    if answer and str(wr.get("status") or "").lower() in {"completed", "partial"}:
        consistency = 0.85
    if answer and rag_ids:
        consistency = max(consistency, 0.9)
    if "analysis failed" in answer.lower():
        consistency = 0.2

    rec_quality = 0.0
    if recommendations:
        concrete = sum(1 for r in recommendations if isinstance(r, str) and len(r.strip()) >= 8)
        rec_quality = clamp_score(concrete / max(1, len(recommendations)))
        if rec_quality < 0.5 and concrete:
            rec_quality = 0.55

    return [
        _metric(
            "completeness",
            EvaluationCategory.final_response,
            completeness,
            explanation=f"answer={bool(answer)}, insights={len(insights)}, recommendations={len(recommendations)}",
        ),
        _metric(
            "consistency",
            EvaluationCategory.final_response,
            consistency,
            explanation="Response aligned with workflow/RAG evidence"
            if consistency >= 0.8
            else "Limited evidence alignment",
        ),
        _metric(
            "recommendation_quality",
            EvaluationCategory.final_response,
            rec_quality,
            explanation=f"{len(recommendations)} recommendations",
        ),
    ]


def _collect_all_metrics(artifact: Mapping[str, Any] | Any) -> list[EvaluationMetric]:
    metrics: list[EvaluationMetric] = []
    metrics.extend(evaluate_workflow(artifact))
    metrics.extend(evaluate_agents(artifact))
    metrics.extend(evaluate_tools(artifact))
    metrics.extend(evaluate_memory(artifact))
    metrics.extend(evaluate_rag(artifact))
    metrics.extend(evaluate_llm(artifact))
    metrics.extend(evaluate_final_response(artifact))
    return metrics


def _category_scores(metrics: list[EvaluationMetric]) -> dict[str, float]:
    categories = [
        EvaluationCategory.workflow.value,
        EvaluationCategory.agents.value,
        EvaluationCategory.tools.value,
        EvaluationCategory.memory.value,
        EvaluationCategory.rag.value,
        EvaluationCategory.llm.value,
        EvaluationCategory.final_response.value,
    ]
    return {c: average_metric_scores(metrics, category=c) for c in categories}


def generate_report(
    metrics: list[EvaluationMetric],
    *,
    category_scores: dict[str, float] | None = None,
    weights: dict[str, float] | None = None,
    workflow_id: str = "",
    session_id: str = "",
) -> EvaluationReport:
    return build_evaluation_report(
        metrics,
        category_scores=category_scores,
        weights=weights,
        workflow_id=workflow_id,
        session_id=session_id,
    )


def export_evaluation(run: EvaluationRun) -> dict[str, Any]:
    """JSON-ready export: report, metrics summary, score breakdown."""
    report = run.report
    return {
        "evaluation_id": run.evaluation_id,
        "workflow_id": run.workflow_id,
        "session_id": run.session_id,
        "created_at": run.created_at,
        "status": run.status.value if hasattr(run.status, "value") else str(run.status),
        "overall_score": run.overall_score,
        "grade": run.grade,
        "category_scores": dict(run.category_scores),
        "metrics_summary": [
            {
                "name": m.name,
                "category": m.category.value if hasattr(m.category, "value") else str(m.category),
                "score": m.score,
                "weight": m.weight,
                "explanation": m.explanation,
            }
            for m in run.metrics
        ],
        "score_breakdown": (report.metadata.get("score_breakdown") if report else {}),
        "report": report.model_dump() if report else {},
        "schema_version": run.schema_version,
        "read_only": True,
    }


def evaluation_summary(evaluation_id: str) -> dict[str, Any]:
    run = get_evaluation(evaluation_id)
    if run is None:
        return {"found": False, "evaluation_id": evaluation_id}
    return {
        "found": True,
        "evaluation_id": run.evaluation_id,
        "workflow_id": run.workflow_id,
        "session_id": run.session_id,
        "status": run.status.value if hasattr(run.status, "value") else str(run.status),
        "overall_score": run.overall_score,
        "grade": run.grade,
        "metric_count": len(run.metrics),
        "strength_count": len(run.report.strengths) if run.report else 0,
        "weakness_count": len(run.report.weaknesses) if run.report else 0,
        "recommendation_count": len(run.report.recommendations) if run.report else 0,
    }


def _new_evaluation_id() -> str:
    stamp = utc_now_iso().replace(":", "").replace("-", "")
    return f"eval_{stamp}_{len(_EVALUATION_STORE) + 1:04d}"


def _finalize_run(
    *,
    workflow_id: str,
    session_id: str,
    metrics: list[EvaluationMetric],
    weights: dict[str, float] | None = None,
    metadata: dict[str, Any] | None = None,
) -> EvaluationRun:
    cats = _category_scores(metrics)
    breakdown = calculate_weighted_score(cats, weights=weights)
    report = generate_report(
        metrics,
        category_scores=cats,
        weights=weights,
        workflow_id=workflow_id,
        session_id=session_id,
    )
    now = utc_now_iso()
    run = EvaluationRun(
        evaluation_id=_new_evaluation_id(),
        workflow_id=workflow_id,
        session_id=session_id,
        created_at=now,
        overall_score=breakdown.overall_score,
        grade=breakdown.grade,
        status=EvaluationStatus.completed,
        report=report,
        metrics=metrics,
        category_scores=cats,
        schema_version=EVALUATION_SCHEMA_VERSION,
        metadata={
            "schema": EVALUATION_SCHEMA_VERSION,
            "future_extensions": empty_evaluation_future_extensions(),
            "read_only": True,
            "mutates_execution": False,
            **dict(metadata or {}),
        },
    )
    run.export = export_evaluation(run)
    _persist_evaluation_export(run)
    _EVALUATION_STORE[run.evaluation_id] = run
    try:
        from backend.monitoring.metrics import record_evaluation

        record_evaluation(event="completed")
    except Exception:
        pass
    return run.model_copy(deep=True)


def _persist_evaluation_export(run: EvaluationRun) -> None:
    """Store evaluation export JSON as a storage artifact (Sprint 8.4)."""
    if not run.export:
        return
    try:
        from backend.models.storage_models import ArtifactType
        from backend.services import storage_service

        obj = storage_service.store_json_artifact(
            run.export,
            name=f"{run.evaluation_id}.json",
            artifact_type=ArtifactType.evaluation_export,
            metadata={
                "evaluation_id": run.evaluation_id,
                "workflow_id": run.workflow_id,
                "session_id": run.session_id,
            },
        )
        run.metadata = dict(run.metadata or {})
        run.metadata["storage_object_id"] = obj.object_id
    except Exception:
        # Storage is additive — evaluation logic must not fail if storage is unavailable.
        pass


def evaluate_session(
    session: Any,
    *,
    weights: dict[str, float] | None = None,
    execution: Any | None = None,
) -> EvaluationRun:
    """Evaluate a completed AnalystSession (and optional workflow execution). Read-only."""
    data = _as_dict(session)
    if execution is not None:
        data["execution"] = _as_dict(execution)
        data["workflow_execution"] = _as_dict(execution)
    result = _as_dict(data.get("result"))
    wr = _as_dict(result.get("workflow_results") or data.get("workflow_results"))
    artifact = {
        **data,
        **wr,
        "result": result,
        "workflow_results": wr,
        "context": _as_dict(data.get("context")),
        "status": wr.get("status") or _status_str(data.get("status")),
        "stage_count": wr.get("stage_count") or data.get("stage_count"),
        "agent_executions": wr.get("agent_executions") or data.get("agent_executions") or [],
        "agent_results": wr.get("agent_results") or data.get("agent_results") or {},
        "plan_result": wr.get("plan_result") or data.get("plan_result"),
        "rag_chunk_ids": wr.get("rag_chunk_ids")
        or _as_dict(data.get("context")).get("rag_chunk_ids")
        or [],
        "memory_ids": wr.get("memory_ids")
        or _as_dict(data.get("context")).get("memory_ids")
        or [],
        "llm_understanding": _as_dict(data.get("context")).get("llm_understanding"),
    }
    metrics = _collect_all_metrics(artifact)
    return _finalize_run(
        workflow_id=str(data.get("workflow_id") or wr.get("workflow_id") or ""),
        session_id=str(data.get("session_id") or ""),
        metrics=metrics,
        weights=weights,
        metadata={"source": "evaluate_session"},
    )


def evaluate_workflow_run(
    execution: Any,
    *,
    context: Mapping[str, Any] | None = None,
    session_id: str = "",
    weights: dict[str, float] | None = None,
) -> EvaluationRun:
    """Evaluate a completed WorkflowExecution (+ optional final context). Read-only."""
    exec_data = _as_dict(execution)
    ctx = dict(context or {})
    artifact = {
        "execution": exec_data,
        "workflow_execution": exec_data,
        "status": _status_str(exec_data.get("status")),
        "stage_results": list(exec_data.get("stage_results") or []),
        "errors": list(exec_data.get("errors") or []),
        "agent_executions": ctx.get("agent_executions") or [],
        "agent_results": ctx.get("agent_results") or {},
        "plan_result": ctx.get("plan_result"),
        "rag_chunk_ids": ctx.get("rag_chunk_ids") or [],
        "memory_ids": ctx.get("memory_ids") or [],
        "rag_snippets": ctx.get("rag_snippets") or [],
        "rag_sources": ctx.get("rag_sources") or [],
        "rag_context_text": ctx.get("rag_context_text") or "",
        "memory_snippets": ctx.get("memory_snippets") or [],
        "result": ctx.get("analyst_runtime_response")
        or ctx.get("analyst_response")
        or {
            "answer": ctx.get("analyst_answer") or "",
            "insights": ctx.get("analyst_insights") or [],
            "recommendations": ctx.get("analyst_recommendations") or [],
            "validation_status": "unchecked",
            "workflow_results": {
                "status": _status_str(exec_data.get("status")),
                "workflow_id": exec_data.get("workflow_id"),
            },
            "metadata": {
                "rag_chunk_ids": ctx.get("rag_chunk_ids") or [],
            },
        },
        "context": ctx,
        "workflow_results": {
            "status": _status_str(exec_data.get("status")),
            "workflow_id": exec_data.get("workflow_id"),
            "agent_executions": ctx.get("agent_executions") or [],
            "agent_results": ctx.get("agent_results") or {},
            "plan_result": ctx.get("plan_result"),
            "rag_chunk_ids": ctx.get("rag_chunk_ids") or [],
            "memory_ids": ctx.get("memory_ids") or [],
        },
    }
    metrics = _collect_all_metrics(artifact)
    return _finalize_run(
        workflow_id=str(exec_data.get("workflow_id") or ""),
        session_id=session_id or str(ctx.get("analyst_session_id") or ""),
        metrics=metrics,
        weights=weights,
        metadata={"source": "evaluate_workflow_run", "execution_id": exec_data.get("execution_id")},
    )


# Spec alias: evaluate_workflow() scores metrics; evaluate_workflow_run() returns EvaluationRun.
def evaluate_workflow_metrics(artifact: Mapping[str, Any] | Any) -> list[EvaluationMetric]:
    return evaluate_workflow(artifact)
