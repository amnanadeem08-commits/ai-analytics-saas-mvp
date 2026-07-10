from __future__ import annotations

import traceback
from collections.abc import Callable, Mapping
from time import perf_counter
from typing import Any, Protocol

from backend.models.ai_insight_models import UniversalAIInsight, UniversalAIInsightCollection, utc_now_iso
from backend.models.intelligence_orchestrator_models import IntelligenceOrchestrator, OrchestrationStage
from backend.models.workflow_models import (
    WORKFLOW_SCHEMA_VERSION,
    LogLevel,
    StageRunResult,
    StageRunStatus,
    WorkflowDefinition,
    WorkflowError,
    WorkflowExecution,
    WorkflowLogEntry,
    WorkflowStageDefinition,
    WorkflowStatistics,
    WorkflowStatus,
    WorkflowSummary,
    empty_workflow_future_extensions,
)
from backend.services.intelligence_orchestrator_service import (
    build_orchestrator,
    execution_order,
    find_stage,
)

# ---------------------------------------------------------------------------
# Context keys written/read by stage runners
# ---------------------------------------------------------------------------
CTX_INSIGHTS = "insights"
CTX_VALIDATIONS = "validations"
CTX_DECISIONS = "decisions"
CTX_ROOT_CAUSES = "root_causes"
CTX_REASONINGS = "reasonings"
CTX_STORYBOARD = "storyboard"
CTX_BUNDLE = "bundle"
CTX_REGISTRY = "registry"
CTX_ANALYST_RESPONSE = "analyst_response"
CTX_PREDICTIONS = "predictions"
CTX_PREDICTION_VALIDATIONS = "prediction_validations"
CTX_FORECAST_ADAPTERS = "forecast_adapters"
CTX_FORECAST_PIPELINE = "forecast_pipeline"
CTX_CAPABILITY_REGISTRY = "capability_registry"
CTX_DATASET_READINESS = "dataset_readiness"
CTX_SCENARIO_REGISTRY = "scenario_registry"
CTX_EXPLANATION = "explanation"
CTX_GOVERNANCE = "governance"
CTX_DATASET_ID = "dataset_id"
CTX_DOMAIN = "domain"
CTX_OBSERVATIONS = "observations"
CTX_RAW_INSIGHTS = "raw_insights"  # optional pre-validation UniversalAIInsight list
CTX_AGENT_EXECUTIONS = "agent_executions"
CTX_AGENT_RESULTS = "agent_results"
CTX_AGENT_PLAN = "agent_plan"
CTX_PLAN_RESULT = "plan_result"
CTX_MEMORY_CONTEXT = "memory_context"
CTX_MEMORY_IDS = "memory_ids"
CTX_RAG_CONTEXT = "rag_context"
CTX_RAG_CHUNK_IDS = "rag_chunk_ids"
CTX_ANALYST_SESSION = "analyst_session"
CTX_ANALYST_RUNTIME_RESPONSE = "analyst_runtime_response"
CTX_EVALUATION = "evaluation"
CTX_EVALUATION_REPORT = "evaluation_report"


class StageRunner(Protocol):
    """Callable interface for stage runners. Must be side-effect free w.r.t. prior context mutation."""

    def __call__(
        self,
        context: dict[str, Any],
        stage: WorkflowStageDefinition,
        *,
        dataset_id: str | None,
        domain: str | None,
    ) -> dict[str, Any]:
        """Return a partial context update (merged into the shared context)."""


def _asset_ref(value: Any) -> str | None:
    if value is None:
        return None
    for attr in (
        "id",
        "collection_id",
        "bundle_id",
        "registry_id",
        "storyboard_id",
        "response_id",
        "readiness_id",
        "explanation_id",
        "governance_id",
        "pipeline_id",
        "orchestrator_id",
    ):
        if hasattr(value, attr):
            ref = getattr(value, attr)
            if ref:
                return f"{type(value).__name__}:{ref}"
    if isinstance(value, list) and value:
        first = _asset_ref(value[0])
        return f"list[{len(value)}]:{first}" if first else f"list[{len(value)}]"
    return type(value).__name__


def _copy_ctx(context: Mapping[str, Any]) -> dict[str, Any]:
    """Shallow-copy context; deep-copy pydantic models when present."""
    out: dict[str, Any] = {}
    for key, value in context.items():
        if hasattr(value, "model_copy"):
            try:
                out[key] = value.model_copy(deep=True)
                continue
            except Exception:
                pass
        if isinstance(value, list):
            copied: list[Any] = []
            for item in value:
                if hasattr(item, "model_copy"):
                    try:
                        copied.append(item.model_copy(deep=True))
                        continue
                    except Exception:
                        pass
                copied.append(item)
            out[key] = copied
        else:
            out[key] = value
    return out


def _resolve_dataset_domain(
    context: Mapping[str, Any],
    dataset_id: str | None,
    domain: str | None,
) -> tuple[str | None, str | None]:
    ds = dataset_id or context.get(CTX_DATASET_ID)
    dom = domain or context.get(CTX_DOMAIN)
    return ds, dom


# ---------------------------------------------------------------------------
# Built-in stage runners — call existing engines; never regenerate from scratch
# when inputs are missing in a way that would invent data.
# ---------------------------------------------------------------------------


def _run_insights(
    context: dict[str, Any],
    stage: WorkflowStageDefinition,
    *,
    dataset_id: str | None,
    domain: str | None,
) -> dict[str, Any]:
    from backend.services.ai_insight_mapper_service import build_insight_collection

    ds, dom = _resolve_dataset_domain(context, dataset_id, domain)
    existing = context.get(CTX_INSIGHTS)
    if existing is not None:
        return {CTX_INSIGHTS: existing, CTX_DATASET_ID: ds, CTX_DOMAIN: dom}

    raw = context.get(CTX_RAW_INSIGHTS) or []
    if not isinstance(raw, list):
        raw = [raw]
    insights = [item for item in raw if isinstance(item, UniversalAIInsight)]
    if not insights and isinstance(existing, UniversalAIInsightCollection):
        return {CTX_INSIGHTS: existing}

    collection = build_insight_collection(insights, dataset_id=ds, domain=dom)
    return {CTX_INSIGHTS: collection, CTX_DATASET_ID: ds, CTX_DOMAIN: dom}


def _run_validation(
    context: dict[str, Any],
    stage: WorkflowStageDefinition,
    *,
    dataset_id: str | None,
    domain: str | None,
) -> dict[str, Any]:
    from backend.services.ai_insight_mapper_service import build_insight_collection
    from backend.services.ai_validation_service import validate_insight

    ds, dom = _resolve_dataset_domain(context, dataset_id, domain)
    insights = context.get(CTX_INSIGHTS)
    if insights is None:
        raise ValueError("validation stage requires insights in context")

    validated_list: list[UniversalAIInsight] = []
    reports = []
    for insight in insights.insights:
        validated, report = validate_insight(insight)
        validated_list.append(validated)
        reports.append(report)

    collection = build_insight_collection(validated_list, dataset_id=ds or insights.dataset_id, domain=dom or insights.domain)
    return {
        CTX_INSIGHTS: collection,
        CTX_VALIDATIONS: reports,
        CTX_DATASET_ID: ds or insights.dataset_id,
        CTX_DOMAIN: dom or insights.domain,
    }


def _run_decision(
    context: dict[str, Any],
    stage: WorkflowStageDefinition,
    *,
    dataset_id: str | None,
    domain: str | None,
) -> dict[str, Any]:
    from backend.services.decision_intelligence_service import build_decision_collection

    ds, dom = _resolve_dataset_domain(context, dataset_id, domain)
    insights = context.get(CTX_INSIGHTS)
    if insights is None:
        raise ValueError("decision stage requires insights in context")
    decisions = build_decision_collection(
        list(insights.insights),
        dataset_id=ds or insights.dataset_id,
        domain=dom or insights.domain,
    )
    return {CTX_DECISIONS: decisions}


def _run_root_cause(
    context: dict[str, Any],
    stage: WorkflowStageDefinition,
    *,
    dataset_id: str | None,
    domain: str | None,
) -> dict[str, Any]:
    from backend.services.root_cause_analysis_service import build_root_cause_collection

    ds, dom = _resolve_dataset_domain(context, dataset_id, domain)
    insights = context.get(CTX_INSIGHTS)
    decisions = context.get(CTX_DECISIONS)
    if insights is None:
        raise ValueError("root_cause stage requires insights in context")
    root_causes = build_root_cause_collection(
        insights=list(insights.insights),
        decisions=list(decisions.decisions) if decisions is not None else None,
        dataset_id=ds or insights.dataset_id,
        domain=dom or insights.domain,
    )
    return {CTX_ROOT_CAUSES: root_causes}


def _run_executive_reasoning(
    context: dict[str, Any],
    stage: WorkflowStageDefinition,
    *,
    dataset_id: str | None,
    domain: str | None,
) -> dict[str, Any]:
    from backend.services.executive_reasoning_service import (
        build_executive_reasoning,
        build_reasoning_collection,
    )

    ds, dom = _resolve_dataset_domain(context, dataset_id, domain)
    insights = context.get(CTX_INSIGHTS)
    decisions = context.get(CTX_DECISIONS)
    root_causes = context.get(CTX_ROOT_CAUSES)
    validations = context.get(CTX_VALIDATIONS) or []
    if insights is None or decisions is None:
        raise ValueError("executive_reasoning stage requires insights and decisions")

    reasonings = []
    decision_by_insight = {d.source_insight_id: d for d in decisions.decisions}
    root_by_decision = {
        rc.source_decision_id: rc for rc in (root_causes.root_causes if root_causes else []) if rc.source_decision_id
    }
    root_by_insight = {
        rc.source_insight_id: rc for rc in (root_causes.root_causes if root_causes else []) if rc.source_insight_id
    }
    primary_validation = validations[0] if validations else None

    for insight in insights.insights:
        decision = decision_by_insight.get(insight.id)
        if decision is None and decisions.decisions:
            decision = decisions.decisions[0]
        if decision is None:
            continue
        root = root_by_decision.get(decision.decision_id) or root_by_insight.get(insight.id)
        reasonings.append(
            build_executive_reasoning(
                insight=insight,
                decision=decision,
                root_cause=root,
                validation=primary_validation,
                dataset_id=ds or insights.dataset_id,
                domain=dom or insights.domain,
            )
        )

    collection = build_reasoning_collection(
        reasonings=reasonings,
        dataset_id=ds or insights.dataset_id,
        domain=dom or insights.domain,
    )
    return {CTX_REASONINGS: collection}


def _run_storyboard(
    context: dict[str, Any],
    stage: WorkflowStageDefinition,
    *,
    dataset_id: str | None,
    domain: str | None,
) -> dict[str, Any]:
    from backend.services.storyboard_engine_service import build_executive_storyboard_from_reasoning

    ds, dom = _resolve_dataset_domain(context, dataset_id, domain)
    reasonings = context.get(CTX_REASONINGS)
    if reasonings is None:
        raise ValueError("storyboard stage requires reasonings in context")
    storyboard = build_executive_storyboard_from_reasoning(
        reasonings=reasonings,
        decisions=context.get(CTX_DECISIONS),
        root_causes=context.get(CTX_ROOT_CAUSES),
        validations=context.get(CTX_VALIDATIONS) or [],
        dataset_id=ds,
        domain=dom,
    )
    return {CTX_STORYBOARD: storyboard}


def _run_bundle(
    context: dict[str, Any],
    stage: WorkflowStageDefinition,
    *,
    dataset_id: str | None,
    domain: str | None,
) -> dict[str, Any]:
    from backend.services.intelligence_bundle_service import build_intelligence_bundle

    ds, dom = _resolve_dataset_domain(context, dataset_id, domain)
    bundle = build_intelligence_bundle(
        insights=context.get(CTX_INSIGHTS),
        validations=context.get(CTX_VALIDATIONS) or [],
        decisions=context.get(CTX_DECISIONS),
        root_causes=context.get(CTX_ROOT_CAUSES),
        reasonings=context.get(CTX_REASONINGS),
        storyboard=context.get(CTX_STORYBOARD),
        dataset_id=ds,
        domain=dom,
    )
    return {CTX_BUNDLE: bundle}


def _run_registry(
    context: dict[str, Any],
    stage: WorkflowStageDefinition,
    *,
    dataset_id: str | None,
    domain: str | None,
) -> dict[str, Any]:
    from backend.services.intelligence_registry_service import build_registry

    ds, dom = _resolve_dataset_domain(context, dataset_id, domain)
    registry = build_registry(
        insights=context.get(CTX_INSIGHTS),
        validations=context.get(CTX_VALIDATIONS) or [],
        decisions=context.get(CTX_DECISIONS),
        root_causes=context.get(CTX_ROOT_CAUSES),
        reasonings=context.get(CTX_REASONINGS),
        storyboard=context.get(CTX_STORYBOARD),
        bundle=context.get(CTX_BUNDLE),
        dataset_id=ds,
        domain=dom,
    )
    return {CTX_REGISTRY: registry}


def _run_ai_analyst(
    context: dict[str, Any],
    stage: WorkflowStageDefinition,
    *,
    dataset_id: str | None,
    domain: str | None,
) -> dict[str, Any]:
    from backend.services.ai_analyst_service import build_ai_response

    ds, dom = _resolve_dataset_domain(context, dataset_id, domain)
    response = build_ai_response(
        question=str(context.get("question", "Summarize the current intelligence.")),
        bundle=context.get(CTX_BUNDLE),
        registry=context.get(CTX_REGISTRY),
        storyboard=context.get(CTX_STORYBOARD),
        reasonings=context.get(CTX_REASONINGS),
        decisions=context.get(CTX_DECISIONS),
        root_causes=context.get(CTX_ROOT_CAUSES),
        validations=context.get(CTX_VALIDATIONS) or [],
        insights=context.get(CTX_INSIGHTS),
        dataset_id=ds,
        domain=dom,
    )
    return {CTX_ANALYST_RESPONSE: response}


def _run_prediction(
    context: dict[str, Any],
    stage: WorkflowStageDefinition,
    *,
    dataset_id: str | None,
    domain: str | None,
) -> dict[str, Any]:
    from backend.services.prediction_engine_service import build_prediction_collection

    ds, dom = _resolve_dataset_domain(context, dataset_id, domain)
    predictions = build_prediction_collection(
        insights=context.get(CTX_INSIGHTS),
        validations=context.get(CTX_VALIDATIONS) or [],
        decisions=context.get(CTX_DECISIONS),
        root_causes=context.get(CTX_ROOT_CAUSES),
        reasonings=context.get(CTX_REASONINGS),
        storyboard=context.get(CTX_STORYBOARD),
        bundle=context.get(CTX_BUNDLE),
        registry=context.get(CTX_REGISTRY),
        analyst_response=context.get(CTX_ANALYST_RESPONSE),
        dataset_id=ds,
        domain=dom,
    )
    return {CTX_PREDICTIONS: predictions}


def _run_prediction_validation(
    context: dict[str, Any],
    stage: WorkflowStageDefinition,
    *,
    dataset_id: str | None,
    domain: str | None,
) -> dict[str, Any]:
    from backend.services.prediction_validation_service import validate_collection

    predictions = context.get(CTX_PREDICTIONS)
    if predictions is None:
        raise ValueError("prediction_validation stage requires predictions in context")
    results = validate_collection(
        predictions,
        observations=context.get(CTX_OBSERVATIONS) or [],
        bundle=context.get(CTX_BUNDLE),
        registry=context.get(CTX_REGISTRY),
        validations=context.get(CTX_VALIDATIONS) or [],
        decisions=context.get(CTX_DECISIONS),
        root_causes=context.get(CTX_ROOT_CAUSES),
    )
    return {CTX_PREDICTION_VALIDATIONS: results}


def _run_forecast_adapter(
    context: dict[str, Any],
    stage: WorkflowStageDefinition,
    *,
    dataset_id: str | None,
    domain: str | None,
) -> dict[str, Any]:
    from backend.services.forecast_adapter_service import build_adapter_registry

    return {CTX_FORECAST_ADAPTERS: build_adapter_registry()}


def _run_pipeline(
    context: dict[str, Any],
    stage: WorkflowStageDefinition,
    *,
    dataset_id: str | None,
    domain: str | None,
) -> dict[str, Any]:
    from backend.services.forecast_pipeline_service import build_default_pipeline

    ds, _ = _resolve_dataset_domain(context, dataset_id, domain)
    adapters = context.get(CTX_FORECAST_ADAPTERS)
    adapter_id = None
    if adapters is not None and getattr(adapters, "adapters", None):
        adapter_id = adapters.adapters[0].adapter_id
    return {
        CTX_FORECAST_PIPELINE: build_default_pipeline(
            dataset_id=ds,
            adapter_id=adapter_id,
        )
    }


def _run_capability_registry(
    context: dict[str, Any],
    stage: WorkflowStageDefinition,
    *,
    dataset_id: str | None,
    domain: str | None,
) -> dict[str, Any]:
    from backend.services.forecast_capability_service import build_capability_registry

    return {CTX_CAPABILITY_REGISTRY: build_capability_registry()}


def _run_dataset_readiness(
    context: dict[str, Any],
    stage: WorkflowStageDefinition,
    *,
    dataset_id: str | None,
    domain: str | None,
) -> dict[str, Any]:
    from backend.services.forecast_dataset_service import build_dataset_readiness

    ds, _ = _resolve_dataset_domain(context, dataset_id, domain)
    meta = context.get("dataset_readiness_meta") or {}
    readiness = build_dataset_readiness(
        dataset_id=ds or meta.get("dataset_id"),
        dataset_name=str(meta.get("dataset_name", ds or "")),
        time_column=meta.get("time_column"),
        target_column=meta.get("target_column"),
        feature_columns=list(meta.get("feature_columns") or []),
        record_count=meta.get("record_count"),
        time_granularity=meta.get("time_granularity"),
        missing_values=meta.get("missing_values"),
        date_range=meta.get("date_range"),
    )
    return {CTX_DATASET_READINESS: readiness}


def _run_scenario_registry(
    context: dict[str, Any],
    stage: WorkflowStageDefinition,
    *,
    dataset_id: str | None,
    domain: str | None,
) -> dict[str, Any]:
    from backend.services.forecast_scenario_service import build_scenario_registry

    return {CTX_SCENARIO_REGISTRY: build_scenario_registry()}


def _run_explainability(
    context: dict[str, Any],
    stage: WorkflowStageDefinition,
    *,
    dataset_id: str | None,
    domain: str | None,
) -> dict[str, Any]:
    from backend.services.forecast_explainability_service import build_explanation

    ds, _ = _resolve_dataset_domain(context, dataset_id, domain)
    predictions = context.get(CTX_PREDICTIONS)
    prediction_id = None
    if predictions is not None and getattr(predictions, "predictions", None):
        prediction_id = predictions.predictions[0].prediction_id
    scenarios = context.get(CTX_SCENARIO_REGISTRY)
    scenario_id = None
    if scenarios is not None and getattr(scenarios, "scenarios", None):
        scenario_id = scenarios.scenarios[0].scenario_id
    adapters = context.get(CTX_FORECAST_ADAPTERS)
    adapter_id = None
    if adapters is not None and getattr(adapters, "adapters", None):
        adapter_id = adapters.adapters[0].adapter_id

    explanation = build_explanation(
        prediction_id=prediction_id,
        dataset_id=ds,
        scenario_id=scenario_id,
        adapter_id=adapter_id,
        summary="Workflow-assembled forecast explanation template.",
        forecast_horizon=str(context.get("forecast_horizon", "")),
        confidence_level=str(context.get("confidence_level", "")),
        key_drivers=list(context.get("key_drivers") or []),
        assumptions=["Produced by workflow engine from existing stage outputs."],
        limitations=["No model attribution. Metadata explanation only."],
        supporting_evidence=list(context.get("supporting_evidence") or []),
    )
    return {CTX_EXPLANATION: explanation}


def _run_governance(
    context: dict[str, Any],
    stage: WorkflowStageDefinition,
    *,
    dataset_id: str | None,
    domain: str | None,
) -> dict[str, Any]:
    from backend.services.forecast_governance_service import build_governance

    ds, _ = _resolve_dataset_domain(context, dataset_id, domain)
    pipeline = context.get(CTX_FORECAST_PIPELINE)
    forecast_id = None
    if pipeline is not None:
        forecast_id = getattr(pipeline, "pipeline_id", None)
    governance = build_governance(
        forecast_id=forecast_id or f"workflow_forecast_{ds or 'unknown'}",
        dataset_id=ds,
        owner=str(context.get("owner", "workflow_engine")),
        business_unit=str(context.get("business_unit", "")),
        forecast_version=str(context.get("forecast_version", "1.0.0")),
        tags=["workflow"],
    )
    return {CTX_GOVERNANCE: governance}


def _run_agent_stage(
    context: dict[str, Any],
    stage: WorkflowStageDefinition,
    *,
    dataset_id: str | None,
    domain: str | None,
) -> dict[str, Any]:
    """Workflow stage runner that executes one or more agents and merges context updates."""
    from backend.services.agent_service import ensure_builtin_agents, execute_agent

    ensure_builtin_agents()
    ds, dom = _resolve_dataset_domain(context, dataset_id, domain)
    if ds:
        context.setdefault(CTX_DATASET_ID, ds)
    if dom:
        context.setdefault(CTX_DOMAIN, dom)

    agent_ids = stage.metadata.get("agent_ids") or stage.metadata.get("agents")
    if not agent_ids:
        single = stage.metadata.get("agent_id")
        agent_ids = [single] if single else []
    if isinstance(agent_ids, str):
        agent_ids = [agent_ids]
    if not agent_ids:
        raise ValueError(
            f"Agent stage '{stage.stage_id}' requires metadata.agent_id or metadata.agent_ids"
        )

    objectives = stage.metadata.get("objectives") or {}
    payloads = stage.metadata.get("payloads") or {}
    executions = list(context.get(CTX_AGENT_EXECUTIONS) or [])
    results = dict(context.get(CTX_AGENT_RESULTS) or {})
    updates: dict[str, Any] = {}

    for agent_id in agent_ids:
        objective = None
        if isinstance(objectives, dict):
            objective = objectives.get(agent_id)
        objective = objective or stage.metadata.get("objective") or f"Workflow stage {stage.stage_id}"
        payload: dict[str, Any] = {}
        if isinstance(payloads, dict):
            payload = dict(payloads.get(agent_id) or {})
        payload.setdefault("dataset_id", ds)
        execution = execute_agent(
            str(agent_id),
            context=context,
            objective=str(objective),
            payload=payload,
        )
        executions.append(execution)
        if execution.result is not None:
            results[str(agent_id)] = execution.result
            for key, value in execution.result.context_updates.items():
                updates[key] = value
                context[key] = value
        if execution.status.value == "failed" and stage.metadata.get("fail_on_agent_error", True):
            raise RuntimeError(execution.error_message or f"Agent failed: {agent_id}")

    updates[CTX_AGENT_EXECUTIONS] = executions
    updates[CTX_AGENT_RESULTS] = results
    return updates


def make_agent_stage(
    *,
    stage_id: str,
    agent_ids: list[str] | str,
    stage_name: str = "",
    dependencies: list[str] | None = None,
    execution_order: int = 0,
    objective: str = "",
    fail_on_agent_error: bool = True,
    metadata: dict[str, Any] | None = None,
) -> WorkflowStageDefinition:
    """Helper to create a workflow stage that runs agent(s)."""
    ids = [agent_ids] if isinstance(agent_ids, str) else list(agent_ids)
    meta = dict(metadata or {})
    meta["agent_ids"] = ids
    if len(ids) == 1:
        meta["agent_id"] = ids[0]
    if objective:
        meta["objective"] = objective
    meta["fail_on_agent_error"] = fail_on_agent_error
    return WorkflowStageDefinition(
        stage_id=stage_id,
        stage_name=stage_name or f"Agent:{','.join(ids)}",
        dependencies=list(dependencies or []),
        execution_order=execution_order,
        enabled=True,
        required=True,
        runner_key="agent_runner",
        metadata=meta,
    )


def _run_planner_stage(
    context: dict[str, Any],
    stage: WorkflowStageDefinition,
    *,
    dataset_id: str | None,
    domain: str | None,
) -> dict[str, Any]:
    """Workflow stage: Agent Planner → Generated Plan → Tool Execution → Validation."""
    from backend.services.agent_service import ensure_builtin_agents, execute_reasoning_loop

    ensure_builtin_agents()
    ds, dom = _resolve_dataset_domain(context, dataset_id, domain)
    if ds:
        context.setdefault(CTX_DATASET_ID, ds)
    if dom:
        context.setdefault(CTX_DOMAIN, dom)

    task = (
        stage.metadata.get("task")
        or stage.metadata.get("objective")
        or context.get("planning_task")
        or "Analyze available intelligence context"
    )
    agent_id = stage.metadata.get("agent_id")
    multi_agent = bool(stage.metadata.get("multi_agent", True))
    stop_on_error = bool(stage.metadata.get("stop_on_error", True))
    payload = dict(stage.metadata.get("payload") or {})
    payload.setdefault("dataset_id", ds)

    execution = execute_reasoning_loop(
        str(task),
        agent_id=str(agent_id) if agent_id else None,
        context=context,
        multi_agent=multi_agent,
        stop_on_error=stop_on_error,
        payload=payload,
    )

    updates: dict[str, Any] = {}
    executions = list(context.get(CTX_AGENT_EXECUTIONS) or [])
    executions.append(execution)
    updates[CTX_AGENT_EXECUTIONS] = executions

    results = dict(context.get(CTX_AGENT_RESULTS) or {})
    if execution.result is not None:
        results[execution.agent_id] = execution.result
        updates[CTX_AGENT_RESULTS] = results
        for key, value in execution.result.context_updates.items():
            updates[key] = value
            context[key] = value
        plan_dump = (execution.result.outputs or {}).get("plan")
        plan_result = (execution.result.outputs or {}).get("plan_result")
        if plan_dump is not None:
            updates[CTX_AGENT_PLAN] = plan_dump
        if plan_result is not None:
            updates[CTX_PLAN_RESULT] = plan_result

    if execution.status.value == "failed" and stage.metadata.get("fail_on_agent_error", True):
        raise RuntimeError(execution.error_message or "Planner stage failed")

    return updates


def make_planner_stage(
    *,
    stage_id: str,
    task: str,
    stage_name: str = "",
    dependencies: list[str] | None = None,
    execution_order: int = 0,
    agent_id: str | None = None,
    multi_agent: bool = True,
    fail_on_agent_error: bool = True,
    metadata: dict[str, Any] | None = None,
) -> WorkflowStageDefinition:
    """Helper to create a workflow stage that runs the agent planning engine."""
    meta = dict(metadata or {})
    meta["task"] = task
    meta["objective"] = task
    meta["multi_agent"] = multi_agent
    meta["fail_on_agent_error"] = fail_on_agent_error
    if agent_id:
        meta["agent_id"] = agent_id
    return WorkflowStageDefinition(
        stage_id=stage_id,
        stage_name=stage_name or "Agent Planner",
        dependencies=list(dependencies or []),
        execution_order=execution_order,
        enabled=True,
        required=True,
        runner_key="planner_runner",
        metadata=meta,
    )


def _run_memory_context_stage(
    context: dict[str, Any],
    stage: WorkflowStageDefinition,
    *,
    dataset_id: str | None,
    domain: str | None,
) -> dict[str, Any]:
    """Workflow stage: retrieve memory and merge into shared context before planning."""
    from backend.services.context_retrieval_service import build_agent_context
    from backend.services.memory_service import clear_expired_memory

    ds, dom = _resolve_dataset_domain(context, dataset_id, domain)
    if ds:
        context.setdefault(CTX_DATASET_ID, ds)
    if dom:
        context.setdefault(CTX_DOMAIN, dom)

    if stage.metadata.get("clear_expired", True):
        clear_expired_memory()

    task = (
        stage.metadata.get("task")
        or stage.metadata.get("objective")
        or context.get("planning_task")
        or "Analyze available intelligence context"
    )
    agent_name = str(stage.metadata.get("agent_name") or stage.metadata.get("agent_id") or "")
    limit = int(stage.metadata.get("limit") or 8)
    bundle = build_agent_context(
        str(task),
        agent_name=agent_name,
        runtime_context=context,
        limit=limit,
    )
    updates = {
        CTX_MEMORY_CONTEXT: bundle.model_dump(),
        CTX_MEMORY_IDS: list(bundle.merged_context.get("memory_ids") or []),
        "memory_snippets": list(bundle.merged_context.get("memory_snippets") or []),
        "planning_task": str(task),
    }
    if bundle.merged_context.get("memory_suggested_tools"):
        updates["memory_suggested_tools"] = bundle.merged_context["memory_suggested_tools"]
    return updates


def make_memory_context_stage(
    *,
    stage_id: str,
    task: str = "",
    stage_name: str = "",
    dependencies: list[str] | None = None,
    execution_order: int = 0,
    agent_name: str = "",
    limit: int = 8,
    metadata: dict[str, Any] | None = None,
) -> WorkflowStageDefinition:
    """Helper to create a workflow stage that retrieves agent memory context."""
    meta = dict(metadata or {})
    if task:
        meta["task"] = task
        meta["objective"] = task
    if agent_name:
        meta["agent_name"] = agent_name
    meta["limit"] = limit
    meta.setdefault("clear_expired", True)
    return WorkflowStageDefinition(
        stage_id=stage_id,
        stage_name=stage_name or "Memory Context",
        dependencies=list(dependencies or []),
        execution_order=execution_order,
        enabled=True,
        required=True,
        runner_key="memory_context_runner",
        metadata=meta,
    )


def _run_rag_context_stage(
    context: dict[str, Any],
    stage: WorkflowStageDefinition,
    *,
    dataset_id: str | None,
    domain: str | None,
) -> dict[str, Any]:
    """Workflow stage: retrieve RAG knowledge and merge into shared context."""
    from backend.services.rag_service import build_rag_context

    ds, dom = _resolve_dataset_domain(context, dataset_id, domain)
    if ds:
        context.setdefault(CTX_DATASET_ID, ds)
    if dom:
        context.setdefault(CTX_DOMAIN, dom)

    task = (
        stage.metadata.get("task")
        or stage.metadata.get("objective")
        or context.get("planning_task")
        or context.get("rag_query")
        or "Analyze available intelligence context"
    )
    agent_name = str(stage.metadata.get("agent_name") or stage.metadata.get("agent_id") or "")
    top_k = int(stage.metadata.get("top_k") or 5)
    filters = dict(stage.metadata.get("filters") or {})
    bundle = build_rag_context(
        str(task),
        agent_name=agent_name,
        runtime_context=context,
        top_k=top_k,
        filters=filters or None,
    )
    updates = {
        CTX_RAG_CONTEXT: bundle.model_dump(),
        CTX_RAG_CHUNK_IDS: list(bundle.merged_context.get("rag_chunk_ids") or []),
        "rag_snippets": list(bundle.merged_context.get("rag_snippets") or []),
        "rag_sources": list(bundle.merged_context.get("rag_sources") or []),
        "rag_query": str(task),
    }
    if bundle.merged_context.get("rag_context_text"):
        updates["rag_context_text"] = bundle.merged_context["rag_context_text"]
    return updates


def make_rag_context_stage(
    *,
    stage_id: str,
    task: str = "",
    stage_name: str = "",
    dependencies: list[str] | None = None,
    execution_order: int = 0,
    agent_name: str = "",
    top_k: int = 5,
    filters: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> WorkflowStageDefinition:
    """Helper to create a workflow stage that retrieves RAG knowledge context."""
    meta = dict(metadata or {})
    if task:
        meta["task"] = task
        meta["objective"] = task
    if agent_name:
        meta["agent_name"] = agent_name
    meta["top_k"] = top_k
    if filters:
        meta["filters"] = dict(filters)
    return WorkflowStageDefinition(
        stage_id=stage_id,
        stage_name=stage_name or "RAG Knowledge Context",
        dependencies=list(dependencies or []),
        execution_order=execution_order,
        enabled=True,
        required=True,
        runner_key="rag_context_runner",
        metadata=meta,
    )


def _run_analyst_stage(
    context: dict[str, Any],
    stage: WorkflowStageDefinition,
    *,
    dataset_id: str | None,
    domain: str | None,
) -> dict[str, Any]:
    """Workflow stage: run AI Analyst runtime (query → memory/RAG → workflow → response).

    Pipeline support:
    Analyst Request → Planner → Agents → Tools → Validation → Governance → Response
    """
    from backend.services.ai_analyst_runtime_service import analyze_query, execute_analysis

    ds, dom = _resolve_dataset_domain(context, dataset_id, domain)
    query = str(
        stage.metadata.get("query")
        or stage.metadata.get("task")
        or context.get("user_query")
        or context.get("question")
        or context.get("planning_task")
        or "Analyze available intelligence context"
    )
    session_id = stage.metadata.get("session_id") or context.get("analyst_session_id")
    follow_up = bool(stage.metadata.get("follow_up") or context.get("follow_up"))
    user_context = dict(stage.metadata.get("user_context") or context.get("user_context") or {})
    if ds:
        user_context.setdefault("dataset_id", ds)
    if dom:
        user_context.setdefault("domain", dom)

    initial = {
        **{k: v for k, v in context.items() if k in {CTX_RAW_INSIGHTS, CTX_DATASET_ID, CTX_DOMAIN}},
        **dict(stage.metadata.get("initial_context") or {}),
    }
    if ds:
        initial[CTX_DATASET_ID] = ds
    if dom:
        initial[CTX_DOMAIN] = dom

    # Prefer full session execution when session already exists; else analyze_query.
    if session_id and not follow_up:
        from backend.services.ai_analyst_runtime_service import get_session

        existing = get_session(str(session_id))
        if existing is not None and existing.result is None:
            completed = execute_analysis(str(session_id), initial_context=initial)
            response = completed.result
            return {
                CTX_ANALYST_SESSION: completed.model_dump(),
                CTX_ANALYST_RUNTIME_RESPONSE: response.model_dump() if response else {},
                "analyst_session_id": completed.session_id,
                "user_query": query,
            }

    response = analyze_query(
        query,
        user_context=user_context,
        session_id=str(session_id) if session_id else None,
        follow_up=follow_up,
        initial_context=initial,
    )
    return {
        CTX_ANALYST_RUNTIME_RESPONSE: response.model_dump(),
        "analyst_session_id": response.metadata.get("session_id"),
        "user_query": query,
        "analyst_answer": response.answer,
        "analyst_insights": list(response.insights),
        "analyst_recommendations": list(response.recommendations),
    }


def make_analyst_stage(
    *,
    stage_id: str,
    query: str = "",
    stage_name: str = "",
    dependencies: list[str] | None = None,
    execution_order: int = 0,
    session_id: str | None = None,
    follow_up: bool = False,
    user_context: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> WorkflowStageDefinition:
    """Helper to create a workflow stage that runs the AI Analyst runtime."""
    meta = dict(metadata or {})
    if query:
        meta["query"] = query
        meta["task"] = query
    if session_id:
        meta["session_id"] = session_id
    if follow_up:
        meta["follow_up"] = True
    if user_context:
        meta["user_context"] = dict(user_context)
    return WorkflowStageDefinition(
        stage_id=stage_id,
        stage_name=stage_name or "AI Analyst Runtime",
        dependencies=list(dependencies or []),
        execution_order=execution_order,
        enabled=True,
        required=True,
        runner_key="analyst_runner",
        metadata=meta,
    )


def _run_evaluation_stage(
    context: dict[str, Any],
    stage: WorkflowStageDefinition,
    *,
    dataset_id: str | None,
    domain: str | None,
) -> dict[str, Any]:
    """Read-only evaluation of completed workflow artifacts. Never mutates prior results."""
    from backend.services.evaluation_service import evaluate_session, evaluate_workflow_run

    _ = dataset_id, domain
    session_payload = context.get(CTX_ANALYST_SESSION)
    session_id = str(
        stage.metadata.get("session_id")
        or context.get("analyst_session_id")
        or (session_payload.get("session_id") if isinstance(session_payload, dict) else "")
        or ""
    )

    # Prefer evaluating a completed analyst session when present.
    if session_payload:
        from backend.models.analyst_models import AnalystSession

        if isinstance(session_payload, dict):
            try:
                session_obj = AnalystSession(**session_payload)
            except Exception:
                session_obj = None
        else:
            session_obj = session_payload
        if session_obj is not None:
            run = evaluate_session(session_obj)
            return {
                CTX_EVALUATION: run.model_dump(),
                CTX_EVALUATION_REPORT: run.report.model_dump() if run.report else {},
                "evaluation_id": run.evaluation_id,
                "evaluation_score": run.overall_score,
                "evaluation_grade": run.grade,
                "evaluation_export": run.export,
            }

    # Otherwise score whatever completed artifacts are already in context.
    # Stage runners do not receive the WorkflowExecution object; build a minimal
    # snapshot from context keys so evaluation remains read-only and deterministic.
    synthetic_execution = {
        "execution_id": str(context.get("execution_id") or stage.metadata.get("execution_id") or ""),
        "workflow_id": str(context.get("workflow_id") or stage.metadata.get("workflow_id") or ""),
        "status": str(context.get("workflow_status") or "completed"),
        "stage_results": list(context.get("stage_results_snapshot") or []),
        "errors": list(context.get("workflow_errors") or []),
    }
    # If analyst runtime response exists, fold it into context for final_response metrics.
    run = evaluate_workflow_run(
        synthetic_execution,
        context=context,
        session_id=session_id,
        weights=dict(stage.metadata.get("weights") or {}) or None,
    )
    return {
        CTX_EVALUATION: run.model_dump(),
        CTX_EVALUATION_REPORT: run.report.model_dump() if run.report else {},
        "evaluation_id": run.evaluation_id,
        "evaluation_score": run.overall_score,
        "evaluation_grade": run.grade,
        "evaluation_export": run.export,
    }


def make_evaluation_stage(
    *,
    stage_id: str,
    stage_name: str = "",
    dependencies: list[str] | None = None,
    execution_order: int = 0,
    session_id: str | None = None,
    weights: dict[str, float] | None = None,
    metadata: dict[str, Any] | None = None,
) -> WorkflowStageDefinition:
    """Helper to create a read-only evaluation stage after governance/response."""
    meta = dict(metadata or {})
    if session_id:
        meta["session_id"] = session_id
    if weights:
        meta["weights"] = dict(weights)
    return WorkflowStageDefinition(
        stage_id=stage_id,
        stage_name=stage_name or "Evaluation",
        dependencies=list(dependencies or []),
        execution_order=execution_order,
        enabled=True,
        required=False,
        runner_key="evaluation_runner",
        metadata=meta,
    )


DEFAULT_STAGE_RUNNERS: dict[str, Callable[..., dict[str, Any]]] = {
    "insights": _run_insights,
    "validation": _run_validation,
    "decision": _run_decision,
    "root_cause": _run_root_cause,
    "executive_reasoning": _run_executive_reasoning,
    "storyboard": _run_storyboard,
    "bundle": _run_bundle,
    "registry": _run_registry,
    "ai_analyst": _run_ai_analyst,
    "prediction": _run_prediction,
    "prediction_validation": _run_prediction_validation,
    "forecast_adapter": _run_forecast_adapter,
    "pipeline": _run_pipeline,
    "capability_registry": _run_capability_registry,
    "dataset_readiness": _run_dataset_readiness,
    "scenario_registry": _run_scenario_registry,
    "explainability": _run_explainability,
    "governance": _run_governance,
    "agent_runner": _run_agent_stage,
    "planner_runner": _run_planner_stage,
    "memory_context_runner": _run_memory_context_stage,
    "rag_context_runner": _run_rag_context_stage,
    "analyst_runner": _run_analyst_stage,
    "evaluation_runner": _run_evaluation_stage,
}


def _stage_from_orchestrator(stage: OrchestrationStage) -> WorkflowStageDefinition:
    return WorkflowStageDefinition(
        stage_id=stage.stage_id,
        stage_name=stage.stage_name,
        dependencies=list(stage.dependencies),
        optional_dependencies=list(stage.optional_dependencies),
        execution_order=stage.execution_order,
        enabled=stage.enabled,
        required=True,
        runner_key=stage.stage_id,
        metadata=dict(stage.metadata),
    )


def build_workflow_definition(
    *,
    orchestrator: IntelligenceOrchestrator | None = None,
    workflow_name: str = "Intelligence Pipeline",
    stage_ids: list[str] | None = None,
    stop_on_error: bool = True,
    include_disabled: bool = False,
) -> WorkflowDefinition:
    """Build a workflow definition from the intelligence orchestrator catalog."""
    orch = orchestrator or build_orchestrator()
    now = utc_now_iso()
    ordered_ids = execution_order(orch)
    if stage_ids is not None:
        allow = set(stage_ids)
        ordered_ids = [sid for sid in ordered_ids if sid in allow]

    stages: list[WorkflowStageDefinition] = []
    for stage_id in ordered_ids:
        stage = find_stage(orch, stage_id)
        if stage is None:
            continue
        if not include_disabled and not stage.enabled:
            continue
        stages.append(_stage_from_orchestrator(stage))

    return WorkflowDefinition(
        workflow_id=f"workflow_{now.replace(':', '').replace('-', '')}",
        workflow_name=workflow_name,
        schema_version=WORKFLOW_SCHEMA_VERSION,
        stages=stages,
        stop_on_error=stop_on_error,
        created_at=now,
        metadata={
            "orchestrator_id": orch.orchestrator_id,
            "future_extensions": empty_workflow_future_extensions(),
            "schema": WORKFLOW_SCHEMA_VERSION,
        },
    )


def workflow_execution_graph(definition: WorkflowDefinition) -> dict[str, Any]:
    """Read-only execution graph for a workflow definition."""
    nodes = []
    edges = []
    for stage in sorted(definition.stages, key=lambda s: s.execution_order):
        nodes.append(
            {
                "stage_id": stage.stage_id,
                "stage_name": stage.stage_name,
                "execution_order": stage.execution_order,
                "enabled": stage.enabled,
                "runner_key": stage.runner_key or stage.stage_id,
            }
        )
        for dep in stage.dependencies:
            edges.append({"from": dep, "to": stage.stage_id, "kind": "required"})
        for dep in stage.optional_dependencies:
            edges.append({"from": dep, "to": stage.stage_id, "kind": "optional"})
    return {
        "workflow_id": definition.workflow_id,
        "nodes": nodes,
        "edges": edges,
        "ordered_stage_ids": [s.stage_id for s in sorted(definition.stages, key=lambda x: x.execution_order)],
    }


def get_stage_runner(
    stage_id: str,
    runners: Mapping[str, Callable[..., dict[str, Any]]] | None = None,
) -> Callable[..., dict[str, Any]] | None:
    registry = runners or DEFAULT_STAGE_RUNNERS
    return registry.get(stage_id)


def _append_log(
    logs: list[WorkflowLogEntry],
    *,
    level: LogLevel,
    message: str,
    stage_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> WorkflowLogEntry:
    now = utc_now_iso()
    entry = WorkflowLogEntry(
        log_id=f"log_{len(logs) + 1}_{now.replace(':', '').replace('-', '')}",
        timestamp=now,
        level=level,
        stage_id=stage_id,
        message=message,
        details=details or {},
    )
    logs.append(entry)
    return entry


def _dependencies_satisfied(
    stage: WorkflowStageDefinition,
    completed: set[str],
    failed: set[str],
    skipped: set[str],
) -> tuple[bool, str]:
    for dep in stage.dependencies:
        if dep in failed:
            return False, f"required dependency failed: {dep}"
        if dep in skipped:
            return False, f"required dependency skipped: {dep}"
        if dep not in completed:
            return False, f"required dependency not completed: {dep}"
    return True, ""


def execute_workflow(
    definition: WorkflowDefinition,
    *,
    initial_context: Mapping[str, Any] | None = None,
    dataset_id: str | None = None,
    domain: str | None = None,
    runners: Mapping[str, Callable[..., dict[str, Any]]] | None = None,
    stop_on_error: bool | None = None,
) -> tuple[WorkflowExecution, dict[str, Any]]:
    """Execute a workflow definition sequentially by execution_order.

    Returns (execution_record, final_context). Context values are live objects for
    downstream stages/tests; the execution record stores keys/refs only.
    """
    runner_map = dict(DEFAULT_STAGE_RUNNERS)
    if runners:
        runner_map.update(runners)

    should_stop = definition.stop_on_error if stop_on_error is None else stop_on_error
    context = _copy_ctx(initial_context or {})
    try:
        from backend.logging.workflow_logger import log_workflow_started
        from backend.monitoring.metrics import record_workflow
        from backend.monitoring.tracing import trace_workflow

        trace_workflow(definition.workflow_id)
        log_workflow_started(definition.workflow_id)
        record_workflow(event="started")
    except Exception:
        pass
    if dataset_id:
        context[CTX_DATASET_ID] = dataset_id
    if domain:
        context[CTX_DOMAIN] = domain

    now = utc_now_iso()
    logs: list[WorkflowLogEntry] = []
    errors: list[WorkflowError] = []
    stage_results: list[StageRunResult] = []
    completed: set[str] = set()
    failed: set[str] = set()
    skipped: set[str] = set()

    start_perf = perf_counter()
    _append_log(logs, level=LogLevel.info, message="Workflow execution started")

    ordered = sorted(definition.stages, key=lambda s: (s.execution_order, s.stage_id))
    abort = False

    for stage in ordered:
        if not stage.enabled:
            result = StageRunResult(
                stage_id=stage.stage_id,
                stage_name=stage.stage_name,
                status=StageRunStatus.skipped,
                finished_at=utc_now_iso(),
                metadata={"reason": "disabled"},
            )
            stage_results.append(result)
            skipped.add(stage.stage_id)
            _append_log(
                logs,
                level=LogLevel.info,
                stage_id=stage.stage_id,
                message="Stage skipped (disabled)",
            )
            continue

        if abort:
            result = StageRunResult(
                stage_id=stage.stage_id,
                stage_name=stage.stage_name,
                status=StageRunStatus.skipped,
                finished_at=utc_now_iso(),
                metadata={"reason": "aborted_after_error"},
            )
            stage_results.append(result)
            skipped.add(stage.stage_id)
            continue

        ok, reason = _dependencies_satisfied(stage, completed, failed, skipped)
        if not ok:
            status = StageRunStatus.blocked if stage.required else StageRunStatus.skipped
            result = StageRunResult(
                stage_id=stage.stage_id,
                stage_name=stage.stage_name,
                status=status,
                finished_at=utc_now_iso(),
                error_message=reason,
                metadata={"reason": reason},
            )
            stage_results.append(result)
            if status == StageRunStatus.blocked:
                failed.add(stage.stage_id)
                errors.append(
                    WorkflowError(
                        error_id=f"err_{stage.stage_id}_{utc_now_iso().replace(':', '')}",
                        stage_id=stage.stage_id,
                        error_type="DependencyError",
                        message=reason,
                        recoverable=False,
                        timestamp=utc_now_iso(),
                    )
                )
            else:
                skipped.add(stage.stage_id)
            _append_log(
                logs,
                level=LogLevel.warning,
                stage_id=stage.stage_id,
                message=f"Stage {status.value}: {reason}",
            )
            if should_stop and status == StageRunStatus.blocked:
                abort = True
            continue

        runner_key = stage.runner_key or stage.stage_id
        runner = runner_map.get(runner_key)
        input_keys = sorted(context.keys())
        started_at = utc_now_iso()
        stage_logs: list[WorkflowLogEntry] = []
        t0 = perf_counter()
        _append_log(
            logs,
            level=LogLevel.info,
            stage_id=stage.stage_id,
            message=f"Stage running via {runner_key}",
        )
        stage_logs.append(logs[-1])

        if runner is None:
            message = f"No runner registered for stage '{runner_key}'"
            finished_at = utc_now_iso()
            result = StageRunResult(
                stage_id=stage.stage_id,
                stage_name=stage.stage_name,
                status=StageRunStatus.failed,
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=round((perf_counter() - t0) * 1000, 3),
                input_keys=input_keys,
                error_message=message,
                logs=stage_logs,
            )
            stage_results.append(result)
            failed.add(stage.stage_id)
            errors.append(
                WorkflowError(
                    error_id=f"err_{stage.stage_id}_{finished_at.replace(':', '')}",
                    stage_id=stage.stage_id,
                    error_type="MissingRunner",
                    message=message,
                    recoverable=False,
                    timestamp=finished_at,
                )
            )
            _append_log(logs, level=LogLevel.error, stage_id=stage.stage_id, message=message)
            if should_stop:
                abort = True
            continue

        try:
            updates = runner(
                context,
                stage,
                dataset_id=context.get(CTX_DATASET_ID),
                domain=context.get(CTX_DOMAIN),
            )
            if not isinstance(updates, dict):
                raise TypeError(f"Runner '{runner_key}' must return a dict context update")
            for key, value in updates.items():
                context[key] = value
            output_keys = sorted(updates.keys())
            refs = [r for r in (_asset_ref(updates[k]) for k in output_keys) if r]
            finished_at = utc_now_iso()
            result = StageRunResult(
                stage_id=stage.stage_id,
                stage_name=stage.stage_name,
                status=StageRunStatus.completed,
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=round((perf_counter() - t0) * 1000, 3),
                input_keys=input_keys,
                output_keys=output_keys,
                produced_asset_refs=refs,
                logs=stage_logs,
            )
            stage_results.append(result)
            completed.add(stage.stage_id)
            _append_log(
                logs,
                level=LogLevel.info,
                stage_id=stage.stage_id,
                message="Stage completed",
                details={"output_keys": output_keys},
            )
        except Exception as exc:  # noqa: BLE001 — capture into workflow errors
            finished_at = utc_now_iso()
            message = str(exc) or type(exc).__name__
            result = StageRunResult(
                stage_id=stage.stage_id,
                stage_name=stage.stage_name,
                status=StageRunStatus.failed,
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=round((perf_counter() - t0) * 1000, 3),
                input_keys=input_keys,
                error_message=message,
                logs=stage_logs,
                metadata={"traceback": traceback.format_exc()},
            )
            stage_results.append(result)
            failed.add(stage.stage_id)
            errors.append(
                WorkflowError(
                    error_id=f"err_{stage.stage_id}_{finished_at.replace(':', '')}",
                    stage_id=stage.stage_id,
                    error_type=type(exc).__name__,
                    message=message,
                    recoverable=False,
                    timestamp=finished_at,
                    details={"traceback": traceback.format_exc()},
                )
            )
            _append_log(logs, level=LogLevel.error, stage_id=stage.stage_id, message=message)
            if should_stop:
                abort = True

    finished_at = utc_now_iso()
    duration_ms = round((perf_counter() - start_perf) * 1000, 3)

    enabled_stages = [s for s in ordered if s.enabled]
    completed_enabled = [s for s in enabled_stages if s.stage_id in completed]
    failed_enabled = [s for s in enabled_stages if s.stage_id in failed]
    if not enabled_stages:
        status = WorkflowStatus.completed
    elif failed_enabled and not completed_enabled:
        status = WorkflowStatus.failed
    elif failed_enabled and completed_enabled:
        status = WorkflowStatus.partial
    elif len(completed_enabled) == len(enabled_stages):
        status = WorkflowStatus.completed
    elif completed_enabled:
        status = WorkflowStatus.partial
    else:
        status = WorkflowStatus.failed

    _append_log(
        logs,
        level=LogLevel.info,
        message=f"Workflow finished with status={status.value}",
        details={"completed": len(completed), "failed": len(failed), "skipped": len(skipped)},
    )

    execution = WorkflowExecution(
        execution_id=f"exec_{now.replace(':', '').replace('-', '')}",
        workflow_id=definition.workflow_id,
        workflow_name=definition.workflow_name,
        status=status,
        dataset_id=context.get(CTX_DATASET_ID),
        domain=context.get(CTX_DOMAIN),
        stage_results=stage_results,
        context_keys=sorted(context.keys()),
        logs=logs,
        errors=errors,
        started_at=now,
        finished_at=finished_at,
        duration_ms=duration_ms,
        schema_version=WORKFLOW_SCHEMA_VERSION,
        metadata={
            "future_extensions": empty_workflow_future_extensions(),
            "stop_on_error": should_stop,
            "completed_stage_ids": sorted(completed),
            "failed_stage_ids": sorted(failed),
            "skipped_stage_ids": sorted(skipped),
        },
    )
    # Sprint 7.8 — retain completed executions for API status/results lookup.
    _store_execution(execution, context)
    _persist_workflow_artifact(execution, context)
    try:
        from backend.logging.workflow_logger import log_workflow_completed
        from backend.monitoring.metrics import record_workflow

        status = execution.status.value if hasattr(execution.status, "value") else str(execution.status)
        log_workflow_completed(execution.workflow_id, execution_id=execution.execution_id, status=status)
        record_workflow(event="completed", status=status)
    except Exception:
        pass
    return execution, context


def _persist_workflow_artifact(execution: WorkflowExecution, context: dict[str, Any]) -> None:
    """Store workflow execution summary as a storage artifact (Sprint 8.4)."""
    try:
        from backend.models.storage_models import ArtifactType
        from backend.services import storage_service

        payload = {
            "execution_id": execution.execution_id,
            "workflow_id": execution.workflow_id,
            "workflow_name": execution.workflow_name,
            "status": execution.status.value if hasattr(execution.status, "value") else str(execution.status),
            "dataset_id": execution.dataset_id,
            "stage_count": len(execution.stage_results),
            "error_count": len(execution.errors),
            "evaluation_id": context.get("evaluation_id"),
            "evaluation_export": context.get("evaluation_export"),
            "started_at": execution.started_at,
            "finished_at": execution.finished_at,
        }
        obj = storage_service.store_json_artifact(
            payload,
            name=f"{execution.execution_id}.json",
            artifact_type=ArtifactType.workflow_artifact,
            metadata={
                "execution_id": execution.execution_id,
                "workflow_id": execution.workflow_id,
            },
        )
        execution.metadata = dict(execution.metadata or {})
        execution.metadata["storage_object_id"] = obj.object_id
    except Exception:
        pass


_EXECUTION_STORE: dict[str, WorkflowExecution] = {}
_EXECUTION_CONTEXT_STORE: dict[str, dict[str, Any]] = {}


def clear_execution_store() -> None:
    global _EXECUTION_STORE, _EXECUTION_CONTEXT_STORE
    _EXECUTION_STORE = {}
    _EXECUTION_CONTEXT_STORE = {}


def _store_execution(execution: WorkflowExecution, context: dict[str, Any]) -> None:
    _EXECUTION_STORE[execution.execution_id] = execution.model_copy(deep=True)
    # Store only JSON-safe context refs / serializable summaries for API retrieval.
    safe: dict[str, Any] = {}
    for key, value in context.items():
        if hasattr(value, "model_dump"):
            try:
                safe[key] = value.model_dump()
                continue
            except Exception:
                pass
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[key] = value
        elif isinstance(value, (list, dict)):
            safe[key] = value
        else:
            safe[key] = str(type(value).__name__)
    _EXECUTION_CONTEXT_STORE[execution.execution_id] = safe


def get_execution(execution_id: str) -> WorkflowExecution | None:
    item = _EXECUTION_STORE.get(execution_id)
    return item.model_copy(deep=True) if item is not None else None


def get_execution_context(execution_id: str) -> dict[str, Any] | None:
    item = _EXECUTION_CONTEXT_STORE.get(execution_id)
    return dict(item) if item is not None else None


def list_executions() -> list[WorkflowExecution]:
    return [e.model_copy(deep=True) for e in _EXECUTION_STORE.values()]


def find_stage_result(execution: WorkflowExecution, stage_id: str) -> StageRunResult | None:
    for item in execution.stage_results:
        if item.stage_id == stage_id:
            return item.model_copy(deep=True)
    return None


def list_execution_logs(
    execution: WorkflowExecution,
    *,
    stage_id: str | None = None,
    level: LogLevel | str | None = None,
) -> list[WorkflowLogEntry]:
    level_value = level.value if isinstance(level, LogLevel) else level
    results: list[WorkflowLogEntry] = []
    for entry in execution.logs:
        if stage_id is not None and entry.stage_id != stage_id:
            continue
        if level_value is not None and entry.level.value != level_value:
            continue
        results.append(entry.model_copy(deep=True))
    return results


def workflow_statistics(execution: WorkflowExecution) -> WorkflowStatistics:
    completed = failed = skipped = blocked = pending = 0
    for item in execution.stage_results:
        if item.status == StageRunStatus.completed:
            completed += 1
        elif item.status == StageRunStatus.failed:
            failed += 1
        elif item.status == StageRunStatus.skipped:
            skipped += 1
        elif item.status == StageRunStatus.blocked:
            blocked += 1
        elif item.status in {StageRunStatus.pending, StageRunStatus.ready, StageRunStatus.running}:
            pending += 1
    return WorkflowStatistics(
        total_stages=len(execution.stage_results),
        completed_stages=completed,
        failed_stages=failed,
        skipped_stages=skipped,
        blocked_stages=blocked,
        pending_stages=pending,
        log_count=len(execution.logs),
        error_count=len(execution.errors),
    )


def workflow_summary(execution: WorkflowExecution) -> WorkflowSummary:
    stats = workflow_statistics(execution)
    return WorkflowSummary(
        execution_id=execution.execution_id,
        workflow_name=execution.workflow_name,
        status=execution.status.value,
        completed_stages=stats.completed_stages,
        failed_stages=stats.failed_stages,
        duration_ms=execution.duration_ms,
        context_key_count=len(execution.context_keys),
    )


def validate_workflow_definition(definition: WorkflowDefinition) -> dict[str, object]:
    """Structural validation for a workflow definition."""
    issues: list[str] = []
    seen_ids: set[str] = set()
    stage_ids = {s.stage_id for s in definition.stages}

    if not definition.stages:
        issues.append("Empty workflow definition")

    for stage in definition.stages:
        if not stage.stage_id:
            issues.append("Stage missing stage_id")
            continue
        if stage.stage_id in seen_ids:
            issues.append(f"Duplicate stage_id: {stage.stage_id}")
        seen_ids.add(stage.stage_id)
        for dep in stage.dependencies:
            if dep not in stage_ids:
                issues.append(f"Missing required dependency: {stage.stage_id} -> {dep}")
        for dep in stage.optional_dependencies:
            if dep not in stage_ids:
                issues.append(f"Missing optional dependency: {stage.stage_id} -> {dep}")
        runner_key = stage.runner_key or stage.stage_id
        if runner_key not in DEFAULT_STAGE_RUNNERS:
            issues.append(f"Unknown runner_key: {runner_key}")

    return {
        "valid": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "workflow_id": definition.workflow_id,
        "stage_count": len(definition.stages),
    }
