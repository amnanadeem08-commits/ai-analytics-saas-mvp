from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from backend.models.ai_insight_models import utc_now_iso
from backend.models.planning_models import (
    PLANNING_SCHEMA_VERSION,
    AgentPlan,
    PlanExecutionResult,
    PlanStatus,
    PlanStep,
    PlanStepStatus,
    TaskAnalysis,
    empty_planning_future_extensions,
)
from backend.models.tool_models import ToolExecutionStatus, ToolRequest
from backend.services import llm_service
from backend.services.tool_registry_service import ensure_builtin_tools, execute_tool, get_tool
from backend.services.tool_selection_service import (
    select_tool,
    suggest_alternative_tools,
    validate_tool_selection,
)

_PLANS: dict[str, AgentPlan] = {}


def _stamp(now: str | None = None) -> str:
    value = now or utc_now_iso()
    return value.replace(":", "").replace("-", "")


def create_plan(
    task: str,
    *,
    agent_name: str = "planner",
    agent_role: str = "",
    available_tools: list[str] | None = None,
    steps: list[PlanStep] | None = None,
    context: Mapping[str, Any] | None = None,
    plan_id: str | None = None,
) -> AgentPlan:
    """Create an executable plan from a task (LLM planner + tool availability)."""
    ensure_builtin_tools()
    now = utc_now_iso()
    tools = list(available_tools or [])
    if not tools:
        from backend.services.tool_registry_service import list_tools

        tools = [t.tool_id for t in list_tools(enabled_only=True)]

    if steps is None:
        llm_plan = llm_service.generate_plan(
            task,
            available_tools=tools,
            agent_name=agent_name,
            agent_role=agent_role,
            metadata={"context_keys": sorted((context or {}).keys())},
        )
        built_steps: list[PlanStep] = []
        for index, raw in enumerate(llm_plan.get("steps") or [], start=1):
            tool_name = str(raw.get("tool_name") or "")
            # Dynamic selection refinement per step description.
            selection = select_tool(
                str(raw.get("description") or task),
                agent_role=agent_role or None,
                allowed_tools=tools,
                context=context,
                fallback=tool_name or None,
            )
            chosen = selection.get("tool_id") or tool_name
            alts = suggest_alternative_tools(
                str(chosen),
                task=str(raw.get("description") or task),
                agent_role=agent_role or None,
                allowed_tools=tools,
            )
            built_steps.append(
                PlanStep(
                    step_id=f"step_{index}",
                    description=str(raw.get("description") or f"Step {index}"),
                    agent_name=str(raw.get("agent_name") or agent_name),
                    tool_name=str(chosen),
                    input_data=dict(raw.get("input_data") or {}),
                    expected_output=str(raw.get("expected_output") or "tool_result"),
                    status=PlanStepStatus.pending,
                    alternative_tools=alts,
                    metadata={"selection": selection},
                )
            )
        understanding = str(llm_plan.get("understanding") or "")
        intent = str(llm_plan.get("intent") or "")
    else:
        built_steps = [s.model_copy(deep=True) for s in steps]
        understanding = f"Caller-supplied plan for: {task}"
        intent = "custom"

    plan = AgentPlan(
        plan_id=plan_id or f"plan_{_stamp(now)}",
        task=task,
        agent_name=agent_name,
        steps=built_steps,
        status=PlanStatus.ready if built_steps else PlanStatus.draft,
        created_at=now,
        updated_at=now,
        task_understanding=understanding,
        intent=intent,
        schema_version=PLANNING_SCHEMA_VERSION,
        metadata={
            "future_extensions": empty_planning_future_extensions(),
            "available_tools": tools,
            "agent_role": agent_role,
        },
    )
    _PLANS[plan.plan_id] = plan.model_copy(deep=True)
    return plan.model_copy(deep=True)


def add_plan_step(
    plan: AgentPlan,
    step: PlanStep,
    *,
    replace: bool = True,
) -> AgentPlan:
    copy = plan.model_copy(deep=True)
    steps = list(copy.steps)
    idx = next((i for i, s in enumerate(steps) if s.step_id == step.step_id), None)
    item = step.model_copy(deep=True)
    if idx is None:
        steps.append(item)
    elif replace:
        steps[idx] = item
    else:
        return copy
    copy.steps = steps
    copy.updated_at = utc_now_iso()
    if copy.status == PlanStatus.draft and steps:
        copy.status = PlanStatus.ready
    _PLANS[copy.plan_id] = copy.model_copy(deep=True)
    return copy


def validate_plan(plan: AgentPlan) -> dict[str, object]:
    issues: list[str] = []
    if not plan.plan_id:
        issues.append("Missing plan_id")
    if not plan.task:
        issues.append("Missing task")
    if not plan.steps:
        issues.append("Empty plan")
    seen: set[str] = set()
    for step in plan.steps:
        if not step.step_id:
            issues.append("Step missing step_id")
            continue
        if step.step_id in seen:
            issues.append(f"Duplicate step_id: {step.step_id}")
        seen.add(step.step_id)
        if not step.tool_name:
            issues.append(f"Step missing tool_name: {step.step_id}")
        else:
            selection = validate_tool_selection(step.tool_name)
            if not selection["valid"]:
                issues.extend(f"{step.step_id}: {i}" for i in selection["issues"])  # type: ignore[arg-type]
        if not step.description:
            issues.append(f"Step missing description: {step.step_id}")
    return {
        "valid": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "plan_id": plan.plan_id,
        "step_count": len(plan.steps),
    }


def get_plan(plan_id: str) -> AgentPlan | None:
    item = _PLANS.get(plan_id)
    return item.model_copy(deep=True) if item is not None else None


def get_plan_status(plan_id: str) -> PlanStatus | None:
    item = _PLANS.get(plan_id)
    return item.status if item is not None else None


def plan_summary(plan: AgentPlan | str) -> dict[str, Any]:
    if isinstance(plan, str):
        found = get_plan(plan)
        if found is None:
            return {"plan_id": plan, "found": False}
        plan = found
    return {
        "found": True,
        "plan_id": plan.plan_id,
        "task": plan.task,
        "agent_name": plan.agent_name,
        "status": plan.status.value,
        "step_count": len(plan.steps),
        "intent": plan.intent,
        "task_understanding": plan.task_understanding,
        "tools": [s.tool_name for s in plan.steps],
        "step_statuses": {s.step_id: s.status.value for s in plan.steps},
    }


def _merge_step_output_into_context(
    context: dict[str, Any],
    tool_id: str,
    result: dict[str, Any],
) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    if tool_id == "validation":
        if result.get("validated_insight") is not None:
            updates["agent_validated_insight"] = result["validated_insight"]
        if result.get("validation_report") is not None:
            updates["agent_validation_report"] = result["validation_report"]
            reports = list(context.get("validations") or [])
            reports.append(result["validation_report"])
            updates["validations"] = reports
    elif tool_id == "insight_generation":
        if result.get("analyst_response") is not None:
            updates["analyst_response"] = result["analyst_response"]
            updates["agent_insight_response"] = result["analyst_response"]
    elif tool_id == "forecast_explanation":
        if result.get("explanation") is not None:
            updates["explanation"] = result["explanation"]
    elif tool_id == "governance_validation":
        if result.get("governance") is not None:
            updates["governance"] = result["governance"]
    elif tool_id == "data_profiling":
        updates["agent_profile"] = result.get("profile")
    elif tool_id == "kpi_detection":
        updates["agent_kpi"] = {
            k: result.get(k) for k in ("kpi_cards", "kpi_titles", "mode")
        }
    elif tool_id == "visualization_recommendation":
        updates["agent_visualizations"] = result.get("chart_specs") or result.get("recommendations")
    for key, value in updates.items():
        context[key] = value
    return updates


def execute_plan(
    plan: AgentPlan,
    *,
    context: Mapping[str, Any] | None = None,
    stop_on_error: bool = True,
    allow_alternatives: bool = True,
    tool_arguments: dict[str, dict[str, Any]] | None = None,
) -> tuple[AgentPlan, PlanExecutionResult]:
    """Execute plan steps with retry + alternative tool recovery."""
    ensure_builtin_tools()
    working = plan.model_copy(deep=True)
    working.status = PlanStatus.running
    working.updated_at = utc_now_iso()
    ctx = dict(context or {})
    completed: list[str] = []
    failed: list[str] = []
    skipped: list[str] = []
    outputs: dict[str, Any] = {}
    context_updates: dict[str, Any] = {}
    args_by_tool = dict(tool_arguments or {})

    for index, step in enumerate(working.steps):
        step.status = PlanStepStatus.running
        tool_candidates = [step.tool_name] + (
            list(step.alternative_tools) if allow_alternatives else []
        )
        # Deduplicate while preserving order.
        seen_tools: set[str] = set()
        ordered_tools: list[str] = []
        for tool_id in tool_candidates:
            if tool_id and tool_id not in seen_tools:
                seen_tools.add(tool_id)
                ordered_tools.append(tool_id)

        success = False
        last_error = ""
        max_attempts = max(1, step.max_retries + 1)

        for tool_id in ordered_tools:
            if success:
                break
            if get_tool(tool_id) is None:
                last_error = f"Unknown tool: {tool_id}"
                continue
            attempts = 0
            while attempts < max_attempts and not success:
                attempts += 1
                args = dict(step.input_data)
                args.update(args_by_tool.get(tool_id, {}))
                for key in ("dataframe", "dataset_id", "question", "forecast_id", "owner", "insight"):
                    if key in ctx and key not in args:
                        args[key] = ctx[key]
                response = execute_tool(
                    ToolRequest(
                        request_id=f"plan_{working.plan_id}_{step.step_id}_{tool_id}_{attempts}",
                        tool_id=tool_id,
                        arguments=args,
                        caller=working.agent_name or "planner",
                        context_keys=sorted(ctx.keys()),
                    ),
                    context=ctx,
                    caller=working.agent_name or "planner",
                )
                if response.status == ToolExecutionStatus.completed:
                    step.tool_name = tool_id
                    step.status = PlanStepStatus.completed if attempts == 1 else PlanStepStatus.retried
                    step.retry_count = attempts - 1
                    step.output = dict(response.result)
                    step.error_message = ""
                    outputs[step.step_id] = response.result
                    updates = _merge_step_output_into_context(ctx, tool_id, response.result)
                    context_updates.update(updates)
                    completed.append(step.step_id)
                    success = True
                    evaluation = llm_service.evaluate_result(
                        working.task,
                        {"step_id": step.step_id, "tool_id": tool_id, "result_keys": list(response.result.keys())},
                    )
                    step.metadata["evaluation"] = evaluation
                else:
                    last_error = response.error_message or f"Tool failed: {tool_id}"
                    step.retry_count = attempts - 1
                    if attempts >= max_attempts:
                        break

        if not success:
            step.status = PlanStepStatus.failed
            step.error_message = last_error or "Step failed"
            failed.append(step.step_id)
            if stop_on_error:
                for remaining in working.steps[index + 1 :]:
                    remaining.status = PlanStepStatus.skipped
                    skipped.append(remaining.step_id)
                break

    if failed and completed:
        status = PlanStatus.partial
    elif failed and not completed:
        status = PlanStatus.failed
    elif completed:
        status = PlanStatus.completed
    else:
        status = PlanStatus.failed

    working.status = status
    working.updated_at = utc_now_iso()
    _PLANS[working.plan_id] = working.model_copy(deep=True)

    result = PlanExecutionResult(
        plan_id=working.plan_id,
        completed_steps=completed,
        failed_steps=failed,
        skipped_steps=skipped,
        outputs=outputs,
        final_result={
            "task": working.task,
            "intent": working.intent,
            "status": status.value,
            "completed_count": len(completed),
            "failed_count": len(failed),
            "tools_used": [s.tool_name for s in working.steps if s.step_id in completed],
        },
        context_updates=context_updates,
        status=status,
        error_message="; ".join(
            s.error_message for s in working.steps if s.step_id in failed and s.error_message
        ),
        metadata={"stop_on_error": stop_on_error, "allow_alternatives": allow_alternatives},
    )
    return working, result


def clear_plans() -> None:
    _PLANS.clear()
