from __future__ import annotations

from collections.abc import Callable, Mapping
from time import perf_counter
from typing import Any

from backend.models.ai_insight_models import UniversalAIInsight, UniversalAIInsightCollection, utc_now_iso
from backend.models.tool_models import (
    TOOL_SCHEMA_VERSION,
    ToolDefinition,
    ToolExecutionStatus,
    ToolRequest,
    ToolResponse,
    empty_tool_future_extensions,
)

ToolHandler = Callable[[dict[str, Any], Mapping[str, Any]], dict[str, Any]]

_TOOL_DEFS: dict[str, ToolDefinition] = {}
_TOOL_HANDLERS: dict[str, ToolHandler] = {}


def _serialize(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        try:
            return value.model_dump()
        except Exception:
            return str(value)
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {str(k): _serialize(v) for k, v in value.items()}
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def register_tool(
    definition: ToolDefinition,
    handler: ToolHandler,
    *,
    replace: bool = True,
) -> ToolDefinition:
    """Register a tool definition with an execution handler."""
    if definition.tool_id in _TOOL_DEFS and not replace:
        return _TOOL_DEFS[definition.tool_id].model_copy(deep=True)
    item = definition.model_copy(deep=True)
    _TOOL_DEFS[item.tool_id] = item
    _TOOL_HANDLERS[item.tool_id] = handler
    return item.model_copy(deep=True)


def get_tool(tool_id: str) -> ToolDefinition | None:
    item = _TOOL_DEFS.get(tool_id)
    return item.model_copy(deep=True) if item is not None else None


def list_tools(*, enabled_only: bool = False, tag: str | None = None) -> list[ToolDefinition]:
    results: list[ToolDefinition] = []
    for item in _TOOL_DEFS.values():
        if enabled_only and not item.enabled:
            continue
        if tag is not None and tag not in item.tags:
            continue
        results.append(item.model_copy(deep=True))
    return sorted(results, key=lambda t: t.tool_id)


def validate_tool(definition: ToolDefinition) -> dict[str, object]:
    issues: list[str] = []
    if not definition.tool_id:
        issues.append("Missing tool_id")
    if not definition.name:
        issues.append("Missing name")
    if not isinstance(definition.input_schema, dict):
        issues.append("Invalid input_schema")
    if not isinstance(definition.output_schema, dict):
        issues.append("Invalid output_schema")
    if not definition.permission_flag:
        issues.append("Missing permission_flag")
    if definition.tool_id and definition.tool_id not in _TOOL_HANDLERS:
        issues.append(f"No handler registered for tool_id: {definition.tool_id}")
    return {
        "valid": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "tool_id": definition.tool_id,
    }


def execute_tool(
    request: ToolRequest | str,
    *,
    arguments: dict[str, Any] | None = None,
    context: Mapping[str, Any] | None = None,
    caller: str = "",
) -> ToolResponse:
    """Execute a registered tool handler. Never invents engines — wrappers only."""
    now = utc_now_iso()
    if isinstance(request, str):
        req = ToolRequest(
            request_id=f"toolreq_{now.replace(':', '').replace('-', '')}",
            tool_id=request,
            arguments=dict(arguments or {}),
            caller=caller,
            context_keys=sorted((context or {}).keys()),
        )
    else:
        req = request.model_copy(deep=True)
        if arguments:
            req.arguments = {**req.arguments, **arguments}
        if caller and not req.caller:
            req.caller = caller
        if not req.request_id:
            req.request_id = f"toolreq_{now.replace(':', '').replace('-', '')}"
        if context is not None and not req.context_keys:
            req.context_keys = sorted(context.keys())

    definition = _TOOL_DEFS.get(req.tool_id)
    handler = _TOOL_HANDLERS.get(req.tool_id)
    started = utc_now_iso()
    t0 = perf_counter()

    if definition is None or handler is None:
        return ToolResponse(
            response_id=f"toolresp_{req.request_id}",
            request_id=req.request_id,
            tool_id=req.tool_id,
            status=ToolExecutionStatus.failed,
            error_message=f"Unknown tool: {req.tool_id}",
            started_at=started,
            finished_at=utc_now_iso(),
            duration_ms=round((perf_counter() - t0) * 1000, 3),
        )

    if not definition.enabled:
        return ToolResponse(
            response_id=f"toolresp_{req.request_id}",
            request_id=req.request_id,
            tool_id=req.tool_id,
            status=ToolExecutionStatus.denied,
            error_message=f"Tool disabled: {req.tool_id}",
            started_at=started,
            finished_at=utc_now_iso(),
            duration_ms=round((perf_counter() - t0) * 1000, 3),
        )

    try:
        raw = handler(dict(req.arguments), context or {})
        if not isinstance(raw, dict):
            raise TypeError("Tool handler must return a dict")
        finished = utc_now_iso()
        return ToolResponse(
            response_id=f"toolresp_{req.request_id}",
            request_id=req.request_id,
            tool_id=req.tool_id,
            status=ToolExecutionStatus.completed,
            # Keep live objects for agents/workflow; include a JSON-safe snapshot too.
            result=raw,
            started_at=started,
            finished_at=finished,
            duration_ms=round((perf_counter() - t0) * 1000, 3),
            metadata={
                "permission_flag": definition.permission_flag,
                "result_snapshot": _serialize(raw),
            },
        )
    except Exception as exc:  # noqa: BLE001
        return ToolResponse(
            response_id=f"toolresp_{req.request_id}",
            request_id=req.request_id,
            tool_id=req.tool_id,
            status=ToolExecutionStatus.failed,
            error_message=str(exc) or type(exc).__name__,
            started_at=started,
            finished_at=utc_now_iso(),
            duration_ms=round((perf_counter() - t0) * 1000, 3),
        )


def clear_tool_registry() -> None:
    """Test helper — clears registered tools."""
    _TOOL_DEFS.clear()
    _TOOL_HANDLERS.clear()


def _ctx_get(context: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in context and context[key] is not None:
            return context[key]
    return None


def _require_insight(arguments: dict[str, Any], context: Mapping[str, Any]) -> UniversalAIInsight:
    if "insight" in arguments and isinstance(arguments["insight"], UniversalAIInsight):
        return arguments["insight"]
    insights = _ctx_get(context, "insights", "raw_insights")
    if isinstance(insights, UniversalAIInsightCollection) and insights.insights:
        return insights.insights[0]
    if isinstance(insights, list) and insights:
        first = insights[0]
        if isinstance(first, UniversalAIInsight):
            return first
    raise ValueError("Insight tool requires an insight in arguments or context")


# ---- Built-in tool handlers (wrap existing services) ----


def _tool_data_profiling(arguments: dict[str, Any], context: Mapping[str, Any]) -> dict[str, Any]:
    from backend.services.data_insights_service import build_data_insights

    df = arguments.get("dataframe") or _ctx_get(context, "dataframe", "df")
    result = build_data_insights(df)
    return {
        "tool": "data_profiling",
        "has_dataframe": df is not None,
        "profile": result,
        "dataset_id": arguments.get("dataset_id") or _ctx_get(context, "dataset_id"),
    }


def _tool_kpi_detection(arguments: dict[str, Any], context: Mapping[str, Any]) -> dict[str, Any]:
    from backend.services.kpi_service import compute_kpi_cards

    df = arguments.get("dataframe") or _ctx_get(context, "dataframe", "df")
    if df is None:
        # Context-only KPI summary from insights / predictions when no frame.
        insights = _ctx_get(context, "insights")
        titles = []
        if isinstance(insights, UniversalAIInsightCollection):
            titles = [i.title for i in insights.insights]
        return {
            "tool": "kpi_detection",
            "mode": "context",
            "kpi_titles": titles,
            "dataset_id": arguments.get("dataset_id") or _ctx_get(context, "dataset_id"),
        }
    cards = compute_kpi_cards(df)
    return {"tool": "kpi_detection", "mode": "dataframe", "kpi_cards": cards}


def _tool_visualization_recommendation(arguments: dict[str, Any], context: Mapping[str, Any]) -> dict[str, Any]:
    from backend.services.chart_service import generate_chart_specs

    df = arguments.get("dataframe") or _ctx_get(context, "dataframe", "df")
    if df is None:
        return {
            "tool": "visualization_recommendation",
            "mode": "context",
            "recommendations": [
                {"chart_type": "bar", "reason": "Default categorical comparison without dataframe."},
                {"chart_type": "line", "reason": "Default trend fallback without dataframe."},
            ],
        }
    specs = generate_chart_specs(df, theme_name=arguments.get("theme_name"))
    return {"tool": "visualization_recommendation", "mode": "dataframe", "chart_specs": specs}


def _tool_insight_generation(arguments: dict[str, Any], context: Mapping[str, Any]) -> dict[str, Any]:
    from backend.services.ai_insight_mapper_service import build_insight_collection
    from backend.services.ai_analyst_service import build_ai_response

    insights = _ctx_get(context, "insights", "raw_insights")
    collection = insights
    if isinstance(insights, list):
        collection = build_insight_collection(
            [i for i in insights if isinstance(i, UniversalAIInsight)],
            dataset_id=_ctx_get(context, "dataset_id"),
            domain=_ctx_get(context, "domain"),
        )
    response = build_ai_response(
        question=str(arguments.get("question", "Generate business insights from available intelligence.")),
        bundle=_ctx_get(context, "bundle"),
        registry=_ctx_get(context, "registry"),
        storyboard=_ctx_get(context, "storyboard"),
        reasonings=_ctx_get(context, "reasonings"),
        decisions=_ctx_get(context, "decisions"),
        root_causes=_ctx_get(context, "root_causes"),
        validations=_ctx_get(context, "validations") or [],
        insights=collection if isinstance(collection, UniversalAIInsightCollection) else None,
        dataset_id=_ctx_get(context, "dataset_id"),
        domain=_ctx_get(context, "domain"),
    )
    return {
        "tool": "insight_generation",
        "response_id": getattr(response, "response_id", None) or getattr(response, "id", None),
        "headline": getattr(getattr(response, "explanation", None), "headline", "") if response else "",
        "analyst_response": response,
    }


def _tool_validation(arguments: dict[str, Any], context: Mapping[str, Any]) -> dict[str, Any]:
    from backend.services.ai_validation_service import validate_insight

    insight = _require_insight(arguments, context)
    validated, report = validate_insight(insight)
    return {
        "tool": "validation",
        "insight_id": validated.id,
        "validation_status": validated.validation_status.value,
        "validated_insight": validated,
        "validation_report": report,
    }


def _tool_forecast_explanation(arguments: dict[str, Any], context: Mapping[str, Any]) -> dict[str, Any]:
    from backend.services.forecast_explainability_service import build_explanation

    predictions = _ctx_get(context, "predictions")
    prediction_id = arguments.get("prediction_id")
    if prediction_id is None and predictions is not None and getattr(predictions, "predictions", None):
        prediction_id = predictions.predictions[0].prediction_id
    scenarios = _ctx_get(context, "scenario_registry")
    scenario_id = arguments.get("scenario_id")
    if scenario_id is None and scenarios is not None and getattr(scenarios, "scenarios", None):
        scenario_id = scenarios.scenarios[0].scenario_id
    adapters = _ctx_get(context, "forecast_adapters")
    adapter_id = arguments.get("adapter_id")
    if adapter_id is None and adapters is not None and getattr(adapters, "adapters", None):
        adapter_id = adapters.adapters[0].adapter_id

    explanation = build_explanation(
        prediction_id=prediction_id,
        dataset_id=arguments.get("dataset_id") or _ctx_get(context, "dataset_id"),
        scenario_id=scenario_id,
        adapter_id=adapter_id,
        summary=str(arguments.get("summary", "Agent-requested forecast explanation.")),
        forecast_horizon=str(arguments.get("forecast_horizon", "")),
        confidence_level=str(arguments.get("confidence_level", "")),
        assumptions=["Tool wrapper; no model attribution."],
        limitations=["Metadata explanation only."],
    )
    return {"tool": "forecast_explanation", "explanation": explanation}


def _tool_governance_validation(arguments: dict[str, Any], context: Mapping[str, Any]) -> dict[str, Any]:
    from backend.services.forecast_governance_service import build_governance, validate_governance

    governance = _ctx_get(context, "governance")
    if governance is None:
        governance = build_governance(
            forecast_id=str(arguments.get("forecast_id") or "agent_forecast"),
            dataset_id=arguments.get("dataset_id") or _ctx_get(context, "dataset_id"),
            owner=str(arguments.get("owner", "agent_framework")),
            tags=["agent"],
        )
    result = validate_governance(governance)
    return {"tool": "governance_validation", "validation": result, "governance": governance}


_BUILTIN_SPECS: tuple[tuple[ToolDefinition, ToolHandler], ...] = (
    (
        ToolDefinition(
            tool_id="data_profiling",
            name="Data Profiling",
            description="Profile dataset context via existing data insights service.",
            input_schema={"dataframe": "optional", "dataset_id": "optional"},
            output_schema={"profile": "object"},
            permission_flag="internal.read",
            tags=["analysis", "profiling"],
        ),
        _tool_data_profiling,
    ),
    (
        ToolDefinition(
            tool_id="kpi_detection",
            name="KPI Detection",
            description="Detect KPIs from a dataframe or summarize insight titles from context.",
            input_schema={"dataframe": "optional", "dataset_id": "optional"},
            output_schema={"kpi_cards": "array"},
            permission_flag="internal.read",
            tags=["analysis", "kpi"],
        ),
        _tool_kpi_detection,
    ),
    (
        ToolDefinition(
            tool_id="visualization_recommendation",
            name="Visualization Recommendation",
            description="Recommend chart specs using the chart service when a dataframe is present.",
            input_schema={"dataframe": "optional", "theme_name": "optional"},
            output_schema={"chart_specs": "array"},
            permission_flag="internal.read",
            tags=["visualization"],
        ),
        _tool_visualization_recommendation,
    ),
    (
        ToolDefinition(
            tool_id="insight_generation",
            name="Insight Generation",
            description="Generate an analyst response from existing intelligence via AI Analyst service.",
            input_schema={"question": "optional"},
            output_schema={"analyst_response": "object"},
            permission_flag="internal.write",
            tags=["insight", "analyst"],
        ),
        _tool_insight_generation,
    ),
    (
        ToolDefinition(
            tool_id="validation",
            name="Validation",
            description="Validate a UniversalAIInsight via the AI validation engine.",
            input_schema={"insight": "optional"},
            output_schema={"validated_insight": "object", "validation_report": "object"},
            permission_flag="internal.write",
            tags=["validation"],
        ),
        _tool_validation,
    ),
    (
        ToolDefinition(
            tool_id="forecast_explanation",
            name="Forecast Explanation",
            description="Build a forecast explanation object via the explainability service.",
            input_schema={"prediction_id": "optional", "summary": "optional"},
            output_schema={"explanation": "object"},
            permission_flag="internal.write",
            tags=["forecast", "explainability"],
        ),
        _tool_forecast_explanation,
    ),
    (
        ToolDefinition(
            tool_id="governance_validation",
            name="Governance Validation",
            description="Validate forecast governance metadata via the governance service.",
            input_schema={"forecast_id": "optional", "owner": "optional"},
            output_schema={"validation": "object"},
            permission_flag="internal.read",
            tags=["governance"],
        ),
        _tool_governance_validation,
    ),
)


def ensure_builtin_tools(*, reset: bool = False) -> list[ToolDefinition]:
    """Register built-in tools that wrap existing engines."""
    if reset:
        clear_tool_registry()
    if _TOOL_DEFS and not reset:
        # Ensure builtins present without wiping custom tools.
        registered = set(_TOOL_DEFS)
        for definition, handler in _BUILTIN_SPECS:
            if definition.tool_id not in registered:
                register_tool(definition, handler)
        return list_tools()
    for definition, handler in _BUILTIN_SPECS:
        register_tool(definition, handler)
    # Attach future extension placeholders on first bootstrap
    for tool_id, definition in list(_TOOL_DEFS.items()):
        meta = dict(definition.metadata)
        meta.setdefault("future_extensions", empty_tool_future_extensions())
        meta.setdefault("schema", TOOL_SCHEMA_VERSION)
        _TOOL_DEFS[tool_id] = definition.model_copy(update={"metadata": meta})
    return list_tools()


# Bootstrap builtins on import so agents can rely on them.
ensure_builtin_tools()
