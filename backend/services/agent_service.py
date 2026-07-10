from __future__ import annotations

from collections.abc import Mapping
from time import perf_counter
from typing import Any

from backend.models.agent_models import (
    AGENT_SCHEMA_VERSION,
    AgentDefinition,
    AgentExecution,
    AgentRegistry,
    AgentResult,
    AgentRole,
    AgentStatus,
    AgentTask,
    empty_agent_future_extensions,
)
from backend.models.ai_insight_models import utc_now_iso
from backend.models.tool_models import ToolExecutionStatus, ToolRequest
from backend.services import llm_service
from backend.services.tool_registry_service import (
    ensure_builtin_tools,
    execute_tool,
    get_tool,
    list_tools,
)

_AGENT_DEFS: dict[str, AgentDefinition] = {}
_AGENT_STATUS: dict[str, AgentStatus] = {}


def register_agent(
    definition: AgentDefinition,
    *,
    replace: bool = True,
) -> AgentDefinition:
    if definition.agent_id in _AGENT_DEFS and not replace:
        return _AGENT_DEFS[definition.agent_id].model_copy(deep=True)
    item = definition.model_copy(deep=True)
    meta = dict(item.metadata)
    meta.setdefault("future_extensions", empty_agent_future_extensions())
    meta.setdefault("schema", AGENT_SCHEMA_VERSION)
    item.metadata = meta
    _AGENT_DEFS[item.agent_id] = item
    _AGENT_STATUS.setdefault(item.agent_id, AgentStatus.created)
    return item.model_copy(deep=True)


def get_agent(agent_id: str) -> AgentDefinition | None:
    item = _AGENT_DEFS.get(agent_id)
    return item.model_copy(deep=True) if item is not None else None


def list_agents(*, enabled_only: bool = False, role: AgentRole | str | None = None) -> list[AgentDefinition]:
    role_value = role.value if isinstance(role, AgentRole) else role
    results: list[AgentDefinition] = []
    for item in _AGENT_DEFS.values():
        if enabled_only and not item.enabled:
            continue
        if role_value is not None and item.role.value != role_value:
            continue
        results.append(item.model_copy(deep=True))
    return sorted(results, key=lambda a: a.agent_id)


def update_agent_status(agent_id: str, status: AgentStatus | str) -> AgentStatus:
    if agent_id not in _AGENT_DEFS:
        raise KeyError(f"Unknown agent: {agent_id}")
    resolved = status if isinstance(status, AgentStatus) else AgentStatus(str(status))
    _AGENT_STATUS[agent_id] = resolved
    return resolved


def get_agent_status(agent_id: str) -> AgentStatus | None:
    return _AGENT_STATUS.get(agent_id)


def validate_agent_definition(definition: AgentDefinition) -> dict[str, object]:
    ensure_builtin_tools()
    issues: list[str] = []
    if not definition.agent_id:
        issues.append("Missing agent_id")
    if not definition.agent_name:
        issues.append("Missing agent_name")
    try:
        if definition.role not in AgentRole:
            issues.append(f"Invalid role: {definition.role}")
    except Exception:
        issues.append(f"Invalid role: {definition.role}")
    if not definition.allowed_tools:
        issues.append("Missing allowed_tools")
    for tool_id in definition.allowed_tools:
        if get_tool(tool_id) is None:
            issues.append(f"Unknown allowed tool: {tool_id}")
    if definition.max_tool_calls < 1:
        issues.append("max_tool_calls must be >= 1")
    return {
        "valid": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "agent_id": definition.agent_id,
    }


def agent_summary(agent_id: str | None = None) -> dict[str, Any]:
    if agent_id:
        agent = get_agent(agent_id)
        if agent is None:
            return {"agent_id": agent_id, "found": False}
        return {
            "found": True,
            "agent_id": agent.agent_id,
            "agent_name": agent.agent_name,
            "role": agent.role.value,
            "status": (_AGENT_STATUS.get(agent_id) or AgentStatus.created).value,
            "allowed_tools": list(agent.allowed_tools),
            "enabled": agent.enabled,
        }
    agents = list_agents()
    return {
        "agent_count": len(agents),
        "roles": sorted({a.role.value for a in agents}),
        "enabled_count": sum(1 for a in agents if a.enabled),
        "tool_universe": sorted({t for a in agents for t in a.allowed_tools}),
    }


def assign_task(
    agent_id: str,
    *,
    objective: str,
    payload: dict[str, Any] | None = None,
    input_context_keys: list[str] | None = None,
    priority: int = 0,
) -> AgentTask:
    if get_agent(agent_id) is None:
        raise KeyError(f"Unknown agent: {agent_id}")
    now = utc_now_iso()
    task = AgentTask(
        task_id=f"task_{agent_id}_{now.replace(':', '').replace('-', '')}",
        agent_id=agent_id,
        objective=objective,
        input_context_keys=list(input_context_keys or []),
        payload=dict(payload or {}),
        priority=priority,
        created_at=now,
    )
    update_agent_status(agent_id, AgentStatus.assigned)
    return task


def analyze_task(
    task: str,
    *,
    agent_id: str | None = None,
    context: Mapping[str, Any] | None = None,
) -> TaskAnalysis:
    """Structured task understanding — no hidden chain-of-thought."""
    from backend.models.planning_models import TaskAnalysis
    from backend.services.tool_selection_service import rank_tools

    ensure_builtin_agents()
    agent = get_agent(agent_id) if agent_id else None
    role = agent.role.value if agent else None
    allowed = list(agent.allowed_tools) if agent else None
    ranked = rank_tools(
        task,
        agent_role=role,
        allowed_tools=allowed,
        context=context,
        limit=5,
    )
    llm = llm_service.structured_generate(
        f"Analyze task: {task}. Context keys={sorted((context or {}).keys())}",
        schema={
            "type": "object",
            "properties": {
                "intent": {"type": "string"},
                "understanding": {"type": "string"},
                "suggested_tools": {"type": "array"},
                "suggested_agents": {"type": "array"},
                "confidence": {"type": "number"},
            },
        },
        system=(agent.system_prompt if agent else "You are a task analyst."),
        metadata={"agent_id": agent_id or ""},
    )
    data = llm.get("data") if isinstance(llm, dict) else {}
    if not isinstance(data, dict):
        data = {}
    suggested_tools = [r["tool_id"] for r in ranked]
    raw_tools = data.get("suggested_tools") or []
    if isinstance(raw_tools, list) and raw_tools:
        filtered = [str(t) for t in raw_tools if not allowed or str(t) in allowed]
        if filtered:
            suggested_tools = filtered
    suggested_agents = []
    if agent:
        suggested_agents = [agent.agent_id]
    else:
        # Map intent-ish keywords to builtin agents.
        text = task.lower()
        if "valid" in text:
            suggested_agents.append("validation_agent")
        if "insight" in text or "business" in text:
            suggested_agents.append("insight_agent")
        if "kpi" in text or "profile" in text or "analy" in text:
            suggested_agents.append("data_analyst_agent")
        if "report" in text or "govern" in text or "forecast" in text:
            suggested_agents.append("reporting_agent")
        if not suggested_agents:
            suggested_agents = ["data_analyst_agent"]

    return TaskAnalysis(
        task=task,
        intent=str(data.get("intent") or (ranked[0]["reason"] if ranked else "general_analysis")),
        understanding=str(
            data.get("understanding")
            or f"Task requires tools: {', '.join(suggested_tools[:3]) or 'none'}"
        ),
        suggested_agents=suggested_agents,
        suggested_tools=suggested_tools,
        required_inputs=sorted((context or {}).keys())[:12],
        confidence=float(data.get("confidence") or (0.8 if ranked else 0.4)),
        metadata={"ranked_tools": ranked},
    )


def create_execution_plan(
    task: str,
    *,
    agent_id: str | None = None,
    context: Mapping[str, Any] | None = None,
    multi_agent: bool = False,
) -> Any:
    """Create an executable AgentPlan for a task (optionally multi-agent)."""
    from backend.services.planning_service import create_plan

    ensure_builtin_agents()
    analysis = analyze_task(task, agent_id=agent_id, context=context)
    agent = get_agent(agent_id) if agent_id else None
    if agent is None and analysis.suggested_agents:
        agent = get_agent(analysis.suggested_agents[0])

    if multi_agent or agent is None:
        # Broad plan across available tools / agents.
        from backend.services.tool_registry_service import list_tools

        tools = [t.tool_id for t in list_tools(enabled_only=True)]
        plan = create_plan(
            task,
            agent_name="multi_agent_planner",
            agent_role="",
            available_tools=tools,
            context=context,
        )
    else:
        plan = create_plan(
            task,
            agent_name=agent.agent_name,
            agent_role=agent.role.value,
            available_tools=list(agent.allowed_tools),
            context=context,
        )
    plan.task_understanding = analysis.understanding or plan.task_understanding
    plan.intent = analysis.intent or plan.intent
    plan.metadata["task_analysis"] = analysis.model_dump()
    return plan


def execute_reasoning_loop(
    task: str,
    *,
    agent_id: str | None = None,
    context: Mapping[str, Any] | None = None,
    multi_agent: bool = True,
    stop_on_error: bool = True,
    payload: dict[str, Any] | None = None,
    use_memory: bool = True,
    use_rag: bool = True,
    store_memory: bool = True,
    rag_top_k: int = 5,
) -> AgentExecution:
    """
    Receive Task → Retrieve Memory → Knowledge Retrieval (RAG) → Context Merge →
    Analyze Intent → Create Plan → Select Tools → Execute Tools → Validate Output →
    Store Execution Memory → Return Result.

    Stores only structured artifacts (understanding, plan, decisions, results).
    Never stores hidden chain-of-thought or secrets.
    """
    from backend.services.context_retrieval_service import build_agent_context
    from backend.services.memory_service import store_execution_memories
    from backend.services.planning_service import execute_plan, validate_plan
    from backend.services.rag_service import build_rag_context

    ensure_builtin_agents()
    ensure_builtin_tools()
    ctx = dict(context or {})
    payload = dict(payload or {})

    # Resolve agent early for memory/RAG scoping when provided.
    provisional_agent_id = agent_id
    memory_bundle = None
    rag_bundle = None
    if use_memory:
        agent_for_memory = get_agent(provisional_agent_id) if provisional_agent_id else None
        memory_agent_name = (
            agent_for_memory.agent_name if agent_for_memory else (provisional_agent_id or "")
        )
        memory_bundle = build_agent_context(
            task,
            agent_name=memory_agent_name,
            runtime_context=ctx,
        )
        ctx = dict(memory_bundle.merged_context)

    if use_rag:
        agent_for_rag = get_agent(provisional_agent_id) if provisional_agent_id else None
        rag_agent_name = agent_for_rag.agent_name if agent_for_rag else (provisional_agent_id or "")
        rag_bundle = build_rag_context(
            task,
            agent_name=rag_agent_name,
            runtime_context=ctx,
            top_k=rag_top_k,
            filters=dict(payload.get("rag_filters") or {}),
        )
        ctx = dict(rag_bundle.merged_context)

    analysis = analyze_task(task, agent_id=agent_id, context=ctx)
    resolved_agent_id = agent_id or (analysis.suggested_agents[0] if analysis.suggested_agents else "data_analyst_agent")
    agent = get_agent(resolved_agent_id)
    if agent is None:
        raise KeyError(f"Unknown agent: {resolved_agent_id}")

    # If agent was unknown at memory time, refresh memory with resolved agent name.
    if use_memory and (memory_bundle is None or not memory_bundle.agent_name):
        memory_bundle = build_agent_context(
            task,
            agent_name=agent.agent_name,
            runtime_context=dict(context or {}),
        )
        ctx = dict(memory_bundle.merged_context)
        if use_rag:
            rag_bundle = build_rag_context(
                task,
                agent_name=agent.agent_name,
                runtime_context=ctx,
                top_k=rag_top_k,
                filters=dict(payload.get("rag_filters") or {}),
            )
            ctx = dict(rag_bundle.merged_context)

    agent_task = assign_task(
        resolved_agent_id,
        objective=task,
        payload=payload,
        input_context_keys=sorted(ctx.keys()),
    )
    now = utc_now_iso()
    execution = AgentExecution(
        execution_id=f"agentexec_{resolved_agent_id}_{now.replace(':', '').replace('-', '')}",
        agent_id=resolved_agent_id,
        task_id=agent_task.task_id,
        status=AgentStatus.assigned,
        started_at=now,
        logs=[f"Task assigned: {task}", f"Intent: {analysis.intent}"],
        metadata={
            "future_extensions": empty_agent_future_extensions(),
            "task_analysis": analysis.model_dump(),
            "reasoning_loop": True,
            "memory_enabled": use_memory,
            "rag_enabled": use_rag,
        },
    )
    if memory_bundle is not None:
        execution.logs.append(
            f"Memory retrieved: {len(memory_bundle.memory_result.memories)} items"
        )
        execution.metadata["memory_ids"] = list(memory_bundle.merged_context.get("memory_ids") or [])
        execution.metadata["memory_count"] = len(memory_bundle.memory_result.memories)
    if rag_bundle is not None:
        execution.logs.append(f"RAG retrieved: {len(rag_bundle.rag_snippets)} chunks")
        execution.metadata["rag_chunk_ids"] = list(rag_bundle.merged_context.get("rag_chunk_ids") or [])
        execution.metadata["rag_count"] = len(rag_bundle.rag_snippets)
    t0 = perf_counter()

    try:
        update_agent_status(resolved_agent_id, AgentStatus.running)
        execution.status = AgentStatus.running
        plan = create_execution_plan(
            task,
            agent_id=None if multi_agent else resolved_agent_id,
            context=ctx,
            multi_agent=multi_agent,
        )
        validation = validate_plan(plan)
        execution.logs.append(f"Plan created: {plan.plan_id} ({len(plan.steps)} steps)")
        execution.metadata["plan_id"] = plan.plan_id
        execution.metadata["plan_validation"] = validation
        if not validation["valid"]:
            raise RuntimeError(f"Invalid plan: {validation['issues']}")

        update_agent_status(resolved_agent_id, AgentStatus.tool_execution)
        execution.status = AgentStatus.tool_execution
        tool_args = dict(payload.get("tool_arguments") or {})
        for key in ("dataframe", "dataset_id", "question", "forecast_id", "owner", "insight"):
            if key in payload:
                for tool_id in {s.tool_name for s in plan.steps}:
                    tool_args.setdefault(tool_id, {})
                    tool_args[tool_id].setdefault(key, payload[key])

        updated_plan, plan_result = execute_plan(
            plan,
            context=ctx,
            stop_on_error=stop_on_error,
            allow_alternatives=True,
            tool_arguments=tool_args,
        )
        for step in updated_plan.steps:
            execution.logs.append(f"Step {step.step_id}:{step.tool_name} -> {step.status.value}")
            if step.tool_name:
                execution.tool_request_ids.append(f"{updated_plan.plan_id}:{step.step_id}:{step.tool_name}")

        for key, value in plan_result.context_updates.items():
            ctx[key] = value

        evaluation = llm_service.evaluate_result(
            task,
            {
                "status": plan_result.status.value,
                "completed": plan_result.completed_steps,
                "failed": plan_result.failed_steps,
                "error_message": plan_result.error_message,
            },
        )
        execution.logs.append(f"Evaluation: passed={evaluation.get('passed')}")

        status = (
            AgentStatus.completed
            if plan_result.status.value in {"completed", "partial"} and plan_result.completed_steps
            else AgentStatus.failed
        )
        if plan_result.status.value == "failed":
            status = AgentStatus.failed

        summary = llm_service.generate(
            f"Summarize plan result for '{task}': completed={plan_result.completed_steps}, "
            f"failed={plan_result.failed_steps}",
            system=agent.system_prompt,
        )
        summary_text = str(summary.get("text") or evaluation.get("summary") or "Reasoning loop finished")
        findings = [
            analysis.understanding,
            f"Plan {plan.plan_id} status={plan_result.status.value}",
            *[f"{sid} completed" for sid in plan_result.completed_steps],
            *[f"{sid} failed" for sid in plan_result.failed_steps],
        ]
        tool_calls = [s.tool_name for s in updated_plan.steps if s.tool_name]

        stored_memory_ids: list[str] = []
        if store_memory and status == AgentStatus.completed:
            stored = store_execution_memories(
                agent_name=agent.agent_name,
                task=task,
                execution_id=execution.execution_id,
                tool_calls=tool_calls,
                plan_status=plan_result.status.value,
                summary=summary_text,
                findings=findings,
                validation_passed=bool(evaluation.get("passed")),
                context_keys=sorted(ctx.keys()),
            )
            stored_memory_ids = [m.memory_id for m in stored]
            execution.logs.append(f"Stored memories: {len(stored_memory_ids)}")

        context_updates = dict(plan_result.context_updates)
        if memory_bundle is not None:
            context_updates.setdefault(
                "memory_snippets",
                list(memory_bundle.merged_context.get("memory_snippets") or []),
            )
            context_updates.setdefault(
                "memory_ids",
                list(memory_bundle.merged_context.get("memory_ids") or []),
            )
        if rag_bundle is not None:
            context_updates.setdefault(
                "rag_snippets",
                list(rag_bundle.merged_context.get("rag_snippets") or []),
            )
            context_updates.setdefault(
                "rag_chunk_ids",
                list(rag_bundle.merged_context.get("rag_chunk_ids") or []),
            )
            if rag_bundle.merged_context.get("rag_context_text"):
                context_updates.setdefault(
                    "rag_context_text",
                    rag_bundle.merged_context["rag_context_text"],
                )

        result = AgentResult(
            result_id=f"agentres_{execution.execution_id}",
            agent_id=resolved_agent_id,
            task_id=agent_task.task_id,
            status=status,
            summary=summary_text,
            findings=findings,
            tool_calls=tool_calls,
            outputs={
                "plan": updated_plan.model_dump(),
                "plan_result": plan_result.model_dump(),
                "evaluation": evaluation,
                "task_analysis": analysis.model_dump(),
                "memory": {
                    "retrieved_ids": list((memory_bundle.merged_context if memory_bundle else {}).get("memory_ids") or []),
                    "stored_ids": stored_memory_ids,
                },
                "rag": {
                    "chunk_ids": list((rag_bundle.merged_context if rag_bundle else {}).get("rag_chunk_ids") or []),
                    "sources": list((rag_bundle.retrieval.sources if rag_bundle else [])),
                    "snippet_count": len(rag_bundle.rag_snippets) if rag_bundle else 0,
                },
            },
            context_updates=context_updates,
            error_message=plan_result.error_message,
            metadata={"plan_id": plan.plan_id, "stored_memory_ids": stored_memory_ids},
        )
        finished = utc_now_iso()
        execution.status = status
        execution.result = result
        execution.finished_at = finished
        execution.duration_ms = round((perf_counter() - t0) * 1000, 3)
        execution.error_message = result.error_message
        execution.logs.append(f"Reasoning loop finished: {status.value}")
        update_agent_status(resolved_agent_id, status)
        return execution
    except Exception as exc:  # noqa: BLE001
        finished = utc_now_iso()
        message = str(exc) or type(exc).__name__
        execution.status = AgentStatus.failed
        execution.finished_at = finished
        execution.duration_ms = round((perf_counter() - t0) * 1000, 3)
        execution.error_message = message
        execution.logs.append(f"Reasoning loop failed: {message}")
        execution.result = AgentResult(
            result_id=f"agentres_{execution.execution_id}",
            agent_id=resolved_agent_id,
            task_id=agent_task.task_id,
            status=AgentStatus.failed,
            summary="Reasoning loop failed",
            error_message=message,
            metadata={"task_analysis": analysis.model_dump()},
        )
        update_agent_status(resolved_agent_id, AgentStatus.failed)
        return execution


def _select_tools(
    agent: AgentDefinition,
    task: AgentTask,
    context: Mapping[str, Any],
) -> list[str]:
    """Dynamic tool selection constrained to allowed_tools."""
    from backend.services.tool_selection_service import rank_tools, select_tool

    available = [tid for tid in agent.allowed_tools if get_tool(tid) is not None]
    if not available:
        return []

    force = task.payload.get("tools")
    if isinstance(force, list) and force:
        selected = [str(t) for t in force if str(t) in available]
        if selected:
            return selected[: max(1, agent.max_tool_calls)]

    ranked = rank_tools(
        task.objective,
        agent_role=agent.role,
        allowed_tools=available,
        context=context,
        limit=agent.max_tool_calls,
    )
    selected = [r["tool_id"] for r in ranked if r["score"] > 0]
    if not selected:
        choice = select_tool(
            task.objective,
            agent_role=agent.role,
            allowed_tools=available,
            context=context,
            fallback=available[0],
        )
        if choice.get("tool_id"):
            selected = [str(choice["tool_id"])]
    if not selected:
        selected = available[:1]
    return selected[: max(1, agent.max_tool_calls)]


def _merge_tool_outputs(role: AgentRole, tool_results: list[dict[str, Any]]) -> dict[str, Any]:
    context_updates: dict[str, Any] = {}
    findings: list[str] = []
    outputs: dict[str, Any] = {"tool_results": tool_results}

    for item in tool_results:
        tool_id = item.get("tool_id")
        result = item.get("result") or {}
        if not item.get("ok"):
            findings.append(f"{tool_id} failed: {item.get('error_message')}")
            continue
        findings.append(f"{tool_id} completed")
        if tool_id == "validation":
            if result.get("validated_insight") is not None:
                context_updates.setdefault("agent_validated_insight", result["validated_insight"])
            if result.get("validation_report") is not None:
                context_updates.setdefault("agent_validation_report", result["validation_report"])
                # Also help workflow stages that expect validations list.
                reports = context_updates.get("validations")
                if not isinstance(reports, list):
                    reports = []
                reports.append(result["validation_report"])
                context_updates["validations"] = reports
        elif tool_id == "insight_generation":
            if result.get("analyst_response") is not None:
                context_updates["analyst_response"] = result["analyst_response"]
                context_updates["agent_insight_response"] = result["analyst_response"]
        elif tool_id == "forecast_explanation":
            if result.get("explanation") is not None:
                context_updates["explanation"] = result["explanation"]
        elif tool_id == "governance_validation":
            if result.get("governance") is not None:
                context_updates["governance"] = result["governance"]
            outputs["governance_validation"] = result.get("validation")
        elif tool_id == "data_profiling":
            outputs["profile"] = result.get("profile")
            context_updates["agent_profile"] = result.get("profile")
        elif tool_id == "kpi_detection":
            outputs["kpi"] = {k: result.get(k) for k in ("kpi_cards", "kpi_titles", "mode")}
            context_updates["agent_kpi"] = outputs["kpi"]
        elif tool_id == "visualization_recommendation":
            outputs["visualizations"] = result.get("chart_specs") or result.get("recommendations")
            context_updates["agent_visualizations"] = outputs["visualizations"]

    outputs["role"] = role.value
    return {"findings": findings, "outputs": outputs, "context_updates": context_updates}


def execute_agent(
    agent_id: str,
    task: AgentTask | None = None,
    *,
    context: Mapping[str, Any] | None = None,
    objective: str | None = None,
    payload: dict[str, Any] | None = None,
) -> AgentExecution:
    """Run an agent: assign → running → tool_execution → completed/failed."""
    ensure_builtin_tools()
    agent = get_agent(agent_id)
    if agent is None:
        raise KeyError(f"Unknown agent: {agent_id}")
    if not agent.enabled:
        raise RuntimeError(f"Agent disabled: {agent_id}")

    ctx = dict(context or {})
    if task is None:
        task = assign_task(
            agent_id,
            objective=objective or f"Execute {agent.role.value} agent",
            payload=payload,
            input_context_keys=sorted(ctx.keys()),
        )
    else:
        update_agent_status(agent_id, AgentStatus.assigned)

    now = utc_now_iso()
    execution = AgentExecution(
        execution_id=f"agentexec_{agent_id}_{now.replace(':', '').replace('-', '')}",
        agent_id=agent_id,
        task_id=task.task_id,
        status=AgentStatus.assigned,
        started_at=now,
        logs=[f"Task assigned: {task.objective}"],
        metadata={"future_extensions": empty_agent_future_extensions()},
    )
    t0 = perf_counter()

    try:
        update_agent_status(agent_id, AgentStatus.running)
        execution.status = AgentStatus.running
        execution.logs.append("Agent running")

        selected_tools = _select_tools(agent, task, ctx)
        execution.logs.append(f"Selected tools: {selected_tools}")

        update_agent_status(agent_id, AgentStatus.tool_execution)
        execution.status = AgentStatus.tool_execution

        tool_results: list[dict[str, Any]] = []
        for tool_id in selected_tools:
            args = dict(task.payload.get("tool_arguments", {}).get(tool_id, {}))
            # Share common payload fields.
            for key in ("dataframe", "dataset_id", "question", "forecast_id", "owner", "insight"):
                if key in task.payload and key not in args:
                    args[key] = task.payload[key]
            req = ToolRequest(
                request_id=f"toolreq_{execution.execution_id}_{tool_id}",
                tool_id=tool_id,
                arguments=args,
                caller=agent_id,
                context_keys=sorted(ctx.keys()),
            )
            response = execute_tool(req, context=ctx, caller=agent_id)
            execution.tool_request_ids.append(response.request_id)
            tool_results.append(
                {
                    "tool_id": tool_id,
                    "ok": response.status == ToolExecutionStatus.completed,
                    "status": response.status.value,
                    "result": response.result,
                    "error_message": response.error_message,
                    "request_id": response.request_id,
                }
            )
            execution.logs.append(f"Tool {tool_id} -> {response.status.value}")
            if response.status != ToolExecutionStatus.completed and task.payload.get("fail_fast"):
                raise RuntimeError(response.error_message or f"Tool failed: {tool_id}")

        merged = _merge_tool_outputs(agent.role, tool_results)
        llm_summary = llm_service.generate(
            f"Summarize agent {agent.agent_name} results for objective: {task.objective}. "
            f"Findings: {merged['findings']}",
            system=agent.system_prompt,
            metadata={"agent_id": agent_id, "task_id": task.task_id},
        )
        summary_text = str(llm_summary.get("text") or merged["findings"][:1] or "Agent completed")

        failed_tools = [t for t in tool_results if not t["ok"]]
        status = AgentStatus.failed if failed_tools and not any(t["ok"] for t in tool_results) else AgentStatus.completed
        if failed_tools and any(t["ok"] for t in tool_results):
            status = AgentStatus.completed  # partial tool success still yields agent completion

        result = AgentResult(
            result_id=f"agentres_{execution.execution_id}",
            agent_id=agent_id,
            task_id=task.task_id,
            status=status,
            summary=summary_text,
            findings=list(merged["findings"]),
            tool_calls=[t["tool_id"] for t in tool_results],
            outputs=dict(merged["outputs"]),
            context_updates=dict(merged["context_updates"]),
            error_message="; ".join(t["error_message"] for t in failed_tools if t["error_message"]),
            metadata={"llm": {"provider": llm_summary.get("provider"), "mode": llm_summary.get("mode")}},
        )
        finished = utc_now_iso()
        execution.status = status
        execution.result = result
        execution.finished_at = finished
        execution.duration_ms = round((perf_counter() - t0) * 1000, 3)
        execution.error_message = result.error_message
        execution.logs.append(f"Agent finished: {status.value}")
        update_agent_status(agent_id, status)
        return execution
    except Exception as exc:  # noqa: BLE001
        finished = utc_now_iso()
        message = str(exc) or type(exc).__name__
        execution.status = AgentStatus.failed
        execution.finished_at = finished
        execution.duration_ms = round((perf_counter() - t0) * 1000, 3)
        execution.error_message = message
        execution.logs.append(f"Agent failed: {message}")
        execution.result = AgentResult(
            result_id=f"agentres_{execution.execution_id}",
            agent_id=agent_id,
            task_id=task.task_id,
            status=AgentStatus.failed,
            summary="Agent execution failed",
            error_message=message,
        )
        update_agent_status(agent_id, AgentStatus.failed)
        return execution


def clear_agent_registry() -> None:
    _AGENT_DEFS.clear()
    _AGENT_STATUS.clear()


_BUILTIN_AGENTS: tuple[AgentDefinition, ...] = (
    AgentDefinition(
        agent_id="data_analyst_agent",
        agent_name="Data Analyst Agent",
        role=AgentRole.data_analyst,
        description="Analyze dataset context and request existing analysis engines.",
        allowed_tools=["data_profiling", "kpi_detection", "visualization_recommendation"],
        system_prompt="You are a data analyst. Prefer profiling, KPI, and visualization tools.",
        max_tool_calls=3,
    ),
    AgentDefinition(
        agent_id="insight_agent",
        agent_name="Insight Agent",
        role=AgentRole.insight,
        description="Convert analytical outputs into business insights using existing services.",
        allowed_tools=["insight_generation"],
        system_prompt="You are an insight agent. Use insight generation tools only.",
        max_tool_calls=2,
    ),
    AgentDefinition(
        agent_id="validation_agent",
        agent_name="Validation Agent",
        role=AgentRole.validation,
        description="Validate generated outputs for quality and consistency.",
        allowed_tools=["validation"],
        system_prompt="You are a validation agent. Check quality via the validation tool.",
        max_tool_calls=2,
    ),
    AgentDefinition(
        agent_id="reporting_agent",
        agent_name="Reporting Agent",
        role=AgentRole.reporting,
        description="Prepare structured executive output and governance checks.",
        allowed_tools=["forecast_explanation", "governance_validation", "insight_generation"],
        system_prompt="You are a reporting agent. Produce executive-ready structured outputs.",
        max_tool_calls=3,
    ),
)


def ensure_builtin_agents(*, reset: bool = False) -> AgentRegistry:
    ensure_builtin_tools()
    if reset:
        clear_agent_registry()
    now = utc_now_iso()
    for definition in _BUILTIN_AGENTS:
        if reset or definition.agent_id not in _AGENT_DEFS:
            register_agent(definition)
    return AgentRegistry(
        registry_id=f"agent_registry_{now.replace(':', '').replace('-', '')}",
        agents=list_agents(),
        generated_at=now,
        metadata={"future_extensions": empty_agent_future_extensions()},
    )


def build_agent_registry(*, reset: bool = False) -> AgentRegistry:
    return ensure_builtin_agents(reset=reset)


# Bootstrap builtins on import.
ensure_builtin_agents()
