from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from backend.models.agent_models import AgentRole
from backend.models.tool_models import ToolDefinition
from backend.services import llm_service
from backend.services.tool_registry_service import ensure_builtin_tools, get_tool, list_tools

# Keyword → preferred tools (deterministic ranking signals).
_TASK_TOOL_HINTS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("kpi", "metric", "key performance", "important kpi"), "kpi_detection"),
    (("profile", "profiling", "schema", "column", "dataset quality"), "data_profiling"),
    (("chart", "visual", "visualization", "plot", "graph"), "visualization_recommendation"),
    (("insight", "business insight", "finding", "narrative"), "insight_generation"),
    (("validate", "validation", "quality check", "consistency"), "validation"),
    (("forecast explain", "explain forecast", "explanation", "explainability"), "forecast_explanation"),
    (("governance", "compliance", "audit", "owner", "retention"), "governance_validation"),
    (("revenue decline", "customer revenue", "analyze"), "data_profiling"),
)

_ROLE_TOOL_AFFINITY: dict[str, list[str]] = {
    AgentRole.data_analyst.value: ["data_profiling", "kpi_detection", "visualization_recommendation"],
    AgentRole.insight.value: ["insight_generation"],
    AgentRole.validation.value: ["validation"],
    AgentRole.reporting.value: ["forecast_explanation", "governance_validation", "insight_generation"],
    AgentRole.custom.value: [],
}


def _normalize_task(task: str) -> str:
    return " ".join(str(task or "").lower().split())


def _score_tool(
    tool: ToolDefinition,
    *,
    task: str,
    agent_role: str | None,
    available_context_keys: set[str],
    allowed_tools: set[str] | None,
) -> float:
    if allowed_tools is not None and tool.tool_id not in allowed_tools:
        return -1.0
    if not tool.enabled:
        return -1.0

    score = 0.0
    text = _normalize_task(task)
    tool_blob = f"{tool.tool_id} {tool.name} {tool.description} {' '.join(tool.tags)}".lower()

    for keywords, preferred in _TASK_TOOL_HINTS:
        if preferred == tool.tool_id and any(k in text for k in keywords):
            score += 5.0

    # Lexical overlap with tool identity.
    for token in text.split():
        if len(token) > 3 and token in tool_blob:
            score += 0.35

    if agent_role:
        affinity = _ROLE_TOOL_AFFINITY.get(agent_role, [])
        if tool.tool_id in affinity:
            score += 2.5 + max(0, 3 - affinity.index(tool.tool_id)) * 0.25

    # Soft input-requirement awareness (dataframe tools prefer dataframe presence).
    needs_df = "dataframe" in str(tool.input_schema).lower()
    if needs_df:
        if {"dataframe", "df"} & available_context_keys:
            score += 1.0
        else:
            score -= 0.2  # still usable in context-only mode

    if tool.permission_flag.startswith("internal"):
        score += 0.1

    return score


def rank_tools(
    task: str,
    *,
    agent_role: str | AgentRole | None = None,
    available_tools: list[str] | list[ToolDefinition] | None = None,
    context: Mapping[str, Any] | None = None,
    allowed_tools: list[str] | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Rank tools for a task. Returns [{tool_id, score, reason}, ...] descending."""
    ensure_builtin_tools()
    role = agent_role.value if isinstance(agent_role, AgentRole) else agent_role
    ctx_keys = set((context or {}).keys())
    allow = set(allowed_tools) if allowed_tools is not None else None

    candidates: list[ToolDefinition] = []
    if available_tools:
        for item in available_tools:
            if isinstance(item, ToolDefinition):
                candidates.append(item)
            else:
                found = get_tool(str(item))
                if found is not None:
                    candidates.append(found)
    else:
        candidates = list_tools(enabled_only=True)

    ranked: list[dict[str, Any]] = []
    for tool in candidates:
        score = _score_tool(
            tool,
            task=task,
            agent_role=role,
            available_context_keys=ctx_keys,
            allowed_tools=allow,
        )
        if score < 0:
            continue
        reason_parts = []
        if role and tool.tool_id in _ROLE_TOOL_AFFINITY.get(role, []):
            reason_parts.append(f"role_affinity:{role}")
        for keywords, preferred in _TASK_TOOL_HINTS:
            if preferred == tool.tool_id and any(k in _normalize_task(task) for k in keywords):
                reason_parts.append(f"task_hint:{keywords[0]}")
                break
        ranked.append(
            {
                "tool_id": tool.tool_id,
                "name": tool.name,
                "score": round(score, 4),
                "reason": ", ".join(reason_parts) or "general_match",
            }
        )

    ranked.sort(key=lambda r: (-r["score"], r["tool_id"]))
    return ranked[: max(1, limit)]


def select_tool(
    task: str,
    *,
    agent_role: str | AgentRole | None = None,
    available_tools: list[str] | list[ToolDefinition] | None = None,
    context: Mapping[str, Any] | None = None,
    allowed_tools: list[str] | None = None,
    fallback: str | None = None,
) -> dict[str, Any]:
    """Select the best tool for a task. Uses ranking + optional LLM action hint."""
    ranked = rank_tools(
        task,
        agent_role=agent_role,
        available_tools=available_tools,
        context=context,
        allowed_tools=allowed_tools,
        limit=8,
    )
    candidate_ids = [r["tool_id"] for r in ranked]

    llm_action = llm_service.select_action(
        task,
        candidate_ids,
        agent_role=agent_role.value if isinstance(agent_role, AgentRole) else agent_role,
        metadata={"mode": "tool_selection"},
    )
    chosen = None
    if isinstance(llm_action, dict):
        action = llm_action.get("action") or llm_action.get("tool_id")
        if action in candidate_ids:
            chosen = action

    if chosen is None and ranked:
        chosen = ranked[0]["tool_id"]
    if chosen is None:
        chosen = fallback

    validation = validate_tool_selection(
        chosen,
        task=task,
        allowed_tools=allowed_tools or candidate_ids,
    )
    return {
        "tool_id": chosen,
        "valid": validation["valid"],
        "issues": validation["issues"],
        "ranked": ranked,
        "llm_action": llm_action,
        "score": next((r["score"] for r in ranked if r["tool_id"] == chosen), 0.0),
    }


def validate_tool_selection(
    tool_id: str | None,
    *,
    task: str = "",
    allowed_tools: list[str] | None = None,
) -> dict[str, object]:
    issues: list[str] = []
    if not tool_id:
        issues.append("No tool selected")
        return {"valid": False, "issues": issues, "issue_count": len(issues), "tool_id": tool_id}

    ensure_builtin_tools()
    tool = get_tool(tool_id)
    if tool is None:
        issues.append(f"Unknown tool: {tool_id}")
    elif not tool.enabled:
        issues.append(f"Tool disabled: {tool_id}")
    if allowed_tools is not None and tool_id not in allowed_tools:
        issues.append(f"Tool not allowed for selection: {tool_id}")

    return {
        "valid": not issues,
        "issues": issues,
        "issue_count": len(issues),
        "tool_id": tool_id,
        "task": task,
    }


def suggest_alternative_tools(
    tool_id: str,
    *,
    task: str,
    agent_role: str | AgentRole | None = None,
    allowed_tools: list[str] | None = None,
    limit: int = 3,
) -> list[str]:
    ranked = rank_tools(
        task,
        agent_role=agent_role,
        allowed_tools=allowed_tools,
        limit=limit + 1,
    )
    return [r["tool_id"] for r in ranked if r["tool_id"] != tool_id][:limit]
