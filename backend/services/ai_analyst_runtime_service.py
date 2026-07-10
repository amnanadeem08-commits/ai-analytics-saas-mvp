from __future__ import annotations

from typing import Any

from backend.models.ai_insight_models import utc_now_iso
from backend.models.analyst_models import (
    ANALYST_RUNTIME_SCHEMA_VERSION,
    AnalystRequest,
    AnalystResponse,
    AnalystSession,
    AnalystSessionStatus,
    empty_analyst_runtime_future_extensions,
)
from backend.models.llm_models import LLMRequest
from backend.models.memory_models import MemoryType
from backend.models.workflow_models import WorkflowDefinition, WorkflowStatus

_SESSION_STORE: dict[str, AnalystSession] = {}


def clear_analyst_sessions() -> None:
    global _SESSION_STORE
    _SESSION_STORE = {}


def _new_session_id() -> str:
    stamp = utc_now_iso().replace(":", "").replace("-", "")
    return f"asess_{stamp}_{len(_SESSION_STORE) + 1:04d}"


def create_session(
    request: AnalystRequest | dict[str, Any] | str,
    *,
    session_id: str | None = None,
) -> AnalystSession:
    """Create an AI Analyst runtime session."""
    if isinstance(request, str):
        request = AnalystRequest(query=request)
    elif isinstance(request, dict):
        request = AnalystRequest(**request)

    now = utc_now_iso()
    sid = session_id or request.session_id or _new_session_id()

    # Follow-up: inherit previous session context when session_id already exists.
    previous = _SESSION_STORE.get(sid)
    previous_queries: list[str] = []
    previous_results: list[dict[str, Any]] = []
    inherited_context: dict[str, Any] = {}
    if previous is not None:
        previous_queries = list(previous.previous_queries) + [previous.user_query]
        if previous.result is not None:
            previous_results = list(previous.previous_results) + [
                previous.result.model_dump()
            ]
        inherited_context = dict(previous.context or {})

    context = {
        **inherited_context,
        **dict(request.user_context or {}),
        "user_query": request.query,
        "follow_up": bool(request.follow_up or previous is not None),
        "previous_queries": previous_queries,
        "previous_results": previous_results,
    }

    session = AnalystSession(
        session_id=sid,
        user_query=request.query,
        context=context,
        workflow_id="",
        status=AnalystSessionStatus.created,
        result=None,
        previous_queries=previous_queries,
        previous_results=previous_results,
        created_at=now,
        updated_at=now,
        schema_version=ANALYST_RUNTIME_SCHEMA_VERSION,
        metadata={
            "schema": ANALYST_RUNTIME_SCHEMA_VERSION,
            "future_extensions": empty_analyst_runtime_future_extensions(),
            **dict(request.metadata or {}),
        },
    )
    _SESSION_STORE[sid] = session
    return session.model_copy(deep=True)


def get_session(session_id: str) -> AnalystSession | None:
    item = _SESSION_STORE.get(session_id)
    return item.model_copy(deep=True) if item is not None else None


def session_summary(session_id: str) -> dict[str, Any]:
    session = get_session(session_id)
    if session is None:
        return {"found": False, "session_id": session_id}
    result = session.result
    return {
        "found": True,
        "session_id": session.session_id,
        "status": session.status.value if isinstance(session.status, AnalystSessionStatus) else str(session.status),
        "user_query": session.user_query,
        "workflow_id": session.workflow_id,
        "has_result": result is not None,
        "answer": result.answer if result else "",
        "insight_count": len(result.insights) if result else 0,
        "recommendation_count": len(result.recommendations) if result else 0,
        "previous_query_count": len(session.previous_queries),
        "validation_status": result.validation_status if result else "unchecked",
        "updated_at": session.updated_at,
    }


def _build_analysis_context(session: AnalystSession) -> dict[str, Any]:
    """Retrieve memory + RAG and merge into session context."""
    from backend.services.context_retrieval_service import build_agent_context
    from backend.services.rag_service import build_rag_context

    query = session.user_query
    runtime = dict(session.context or {})

    memory_bundle = build_agent_context(
        query,
        agent_name="AI Analyst",
        runtime_context=runtime,
        limit=8,
    )
    runtime = dict(memory_bundle.merged_context)

    rag_bundle = build_rag_context(
        query,
        agent_name="AI Analyst",
        runtime_context=runtime,
        top_k=5,
    )
    runtime = dict(rag_bundle.merged_context)

    # Conversation foundation: previous analysis for follow-ups
    if session.previous_queries:
        runtime["previous_query"] = session.previous_queries[-1]
    if session.previous_results:
        last = session.previous_results[-1]
        runtime["previous_analysis_result"] = {
            "answer": last.get("answer", ""),
            "insights": last.get("insights", []),
            "recommendations": last.get("recommendations", []),
        }

    runtime["user_query"] = query
    runtime["session_id"] = session.session_id
    return runtime


def _llm_understanding(query: str, context: dict[str, Any]) -> dict[str, Any]:
    from backend.services.llm_service import complete_llm_request, get_llm_provider
    from backend.services.prompt_service import get_prompt_by_type, render_prompt

    prompt_tmpl = get_prompt_by_type("analyst_prompt")
    rendered = render_prompt(
        prompt_tmpl.prompt_id if prompt_tmpl else "analyst_default",
        {
            "user_query": query,
            "context": {
                "memory_snippets": context.get("memory_snippets") or [],
                "previous_query": context.get("previous_query"),
                "previous_analysis_result": context.get("previous_analysis_result"),
                "dataset_id": context.get("dataset_id"),
            },
            "retrieved_knowledge": context.get("rag_context_text")
            or context.get("rag_snippets")
            or "",
            "workflow_results": {},
        },
    )

    schema = {
        "type": "object",
        "properties": {
            "understanding": {"type": "string"},
            "intent": {"type": "string"},
            "summary": {"type": "string"},
        },
        "required": ["understanding"],
    }
    response = complete_llm_request(
        LLMRequest(
            prompt=rendered.rendered_text,
            context={"session_id": context.get("session_id")},
            output_schema=schema,
            system="You are an AI Analyst. Return structured JSON only.",
            metadata={"stage": "understanding"},
        )
    )
    provider = get_llm_provider()
    return {
        "understanding": response.structured_output.get("understanding")
        or response.structured_output.get("summary")
        or response.content,
        "intent": response.structured_output.get("intent") or "",
        "provider": response.provider or getattr(provider, "provider_id", "mock_llm"),
        "llm_response": response.model_dump(),
        "rendered_prompt_id": rendered.prompt_id,
    }


def _build_analyst_workflow(query: str) -> WorkflowDefinition:
    from backend.services.workflow_engine_service import (
        make_memory_context_stage,
        make_planner_stage,
        make_rag_context_stage,
    )
    from backend.models.workflow_models import WorkflowStageDefinition

    now = utc_now_iso()
    stages = [
        make_memory_context_stage(
            stage_id="memory",
            task=query,
            execution_order=1,
            agent_name="AI Analyst",
        ),
        make_rag_context_stage(
            stage_id="rag",
            task=query,
            dependencies=["memory"],
            execution_order=2,
            agent_name="AI Analyst",
        ),
        make_planner_stage(
            stage_id="planner",
            task=query,
            dependencies=["rag"],
            execution_order=3,
            multi_agent=True,
            fail_on_agent_error=False,
        ),
        WorkflowStageDefinition(
            stage_id="agents",
            stage_name="Agent Execution",
            dependencies=["planner"],
            execution_order=4,
            enabled=True,
            required=True,
            runner_key="agent_runner",
            metadata={"task": query, "multi_agent": True, "use_memory": True, "use_rag": True},
        ),
        WorkflowStageDefinition(
            stage_id="validation",
            stage_name="Validation",
            dependencies=["agents"],
            execution_order=5,
            enabled=True,
            required=False,
            runner_key="validation",
            metadata={},
        ),
        WorkflowStageDefinition(
            stage_id="governance",
            stage_name="Governance",
            dependencies=["validation"],
            execution_order=6,
            enabled=True,
            required=False,
            runner_key="governance",
            metadata={},
        ),
    ]
    return WorkflowDefinition(
        workflow_id=f"analyst_wf_{now.replace(':', '').replace('-', '')}",
        workflow_name="AI Analyst Runtime Pipeline",
        stages=stages,
        stop_on_error=False,
        created_at=now,
        metadata={
            "schema": "1.0.0",
            "kind": "ai_analyst_runtime",
            "query": query,
        },
    )


def _generate_structured_response(
    query: str,
    context: dict[str, Any],
    workflow_results: dict[str, Any],
    *,
    understanding: dict[str, Any] | None = None,
) -> AnalystResponse:
    from backend.services.llm_service import complete_llm_request
    from backend.services.output_validation_service import parse_structured_response
    from backend.services.prompt_service import render_prompt

    rendered = render_prompt(
        "analyst_default",
        {
            "user_query": query,
            "context": {
                "understanding": (understanding or {}).get("understanding"),
                "previous_query": context.get("previous_query"),
                "previous_analysis_result": context.get("previous_analysis_result"),
            },
            "retrieved_knowledge": context.get("rag_context_text") or "",
            "workflow_results": {
                "agent_results": workflow_results.get("agent_results"),
                "plan_result": workflow_results.get("plan_result"),
                "status": workflow_results.get("status"),
            },
        },
    )

    schema = {
        "type": "object",
        "properties": {
            "answer": {"type": "string"},
            "insights": {"type": "array"},
            "recommendations": {"type": "array"},
        },
        "required": ["answer", "insights", "recommendations"],
    }
    llm_resp = complete_llm_request(
        LLMRequest(
            prompt=rendered.rendered_text,
            context={"workflow_status": workflow_results.get("status")},
            output_schema=schema,
            system="Return final analyst JSON with answer, insights, recommendations.",
            metadata={"stage": "structured_response"},
        )
    )
    parsed = parse_structured_response(
        llm_resp.structured_output or llm_resp.content,
        schema=schema,
    )
    data = parsed.get("data") if isinstance(parsed.get("data"), dict) else {}
    answer = str(data.get("answer") or parsed.get("final_answer") or llm_resp.content or "")
    insights = data.get("insights") if isinstance(data.get("insights"), list) else []
    recommendations = (
        data.get("recommendations") if isinstance(data.get("recommendations"), list) else []
    )
    # Enrich from workflow agent results when mock returns placeholders
    if not insights and isinstance(workflow_results.get("agent_results"), dict):
        insights = [
            f"Agent result: {k}"
            for k in list(workflow_results["agent_results"].keys())[:3]
        ]
    if not answer:
        answer = f"Analysis complete for: {query}"

    return AnalystResponse(
        answer=answer,
        insights=[str(i) for i in insights],
        recommendations=[str(r) for r in recommendations],
        workflow_results=workflow_results,
        structured_output=data,
        validation_status=str(parsed.get("validation_status") or llm_resp.validation_status),
        provider=llm_resp.provider,
        metadata={
            "repaired": bool(parsed.get("repaired")),
            "understanding": (understanding or {}).get("understanding"),
            "rag_chunk_ids": list(context.get("rag_chunk_ids") or []),
            "memory_ids": list(context.get("memory_ids") or []),
        },
    )


def _store_session_memory(session: AnalystSession, response: AnalystResponse) -> None:
    from backend.services.memory_service import store_memory

    try:
        store_memory(
            agent_name="AI Analyst",
            content={
                "session_id": session.session_id,
                "query": session.user_query,
                "answer": response.answer,
                "insights": response.insights[:5],
                "recommendations": response.recommendations[:5],
                "validation_status": response.validation_status,
            },
            memory_type=MemoryType.TASK_MEMORY,
            source="business_insight",
            relevance_score=0.8,
            tags=["ai_analyst", "session", session.session_id],
            metadata={"workflow_id": session.workflow_id},
        )
    except Exception:
        # Memory storage must not fail the analyst session.
        pass


def execute_analysis(
    session_or_id: AnalystSession | str,
    *,
    initial_context: dict[str, Any] | None = None,
) -> AnalystSession:
    """
    Full runtime flow:
    Create/load session → Memory → RAG → Build context → LLM understanding →
    Workflow → Structured response → Store session memory.
    """
    from backend.services.agent_service import ensure_builtin_agents
    from backend.services.tool_registry_service import ensure_builtin_tools
    from backend.services.workflow_engine_service import execute_workflow

    ensure_builtin_agents()
    ensure_builtin_tools()

    if isinstance(session_or_id, str):
        session = _SESSION_STORE.get(session_or_id)
        if session is None:
            raise KeyError(f"Analyst session not found: {session_or_id}")
    else:
        session = _SESSION_STORE.get(session_or_id.session_id) or session_or_id

    session.status = AnalystSessionStatus.running
    session.updated_at = utc_now_iso()
    _SESSION_STORE[session.session_id] = session

    try:
        context = _build_analysis_context(session)
        if initial_context:
            context.update(initial_context)

        understanding = _llm_understanding(session.user_query, context)
        context["llm_understanding"] = understanding

        definition = _build_analyst_workflow(session.user_query)
        session.workflow_id = definition.workflow_id

        execution, final_ctx = execute_workflow(
            definition,
            initial_context=context,
            dataset_id=context.get("dataset_id"),
            domain=context.get("domain"),
            stop_on_error=False,
        )

        workflow_results = {
            "workflow_id": definition.workflow_id,
            "execution_id": getattr(execution, "execution_id", ""),
            "status": execution.status.value
            if isinstance(execution.status, WorkflowStatus)
            else str(execution.status),
            "agent_results": final_ctx.get("agent_results") or {},
            "agent_executions": [
                e.model_dump() if hasattr(e, "model_dump") else e
                for e in (final_ctx.get("agent_executions") or [])
            ],
            "plan_result": final_ctx.get("plan_result")
            if not hasattr(final_ctx.get("plan_result"), "model_dump")
            else final_ctx.get("plan_result").model_dump(),
            "rag_chunk_ids": list(final_ctx.get("rag_chunk_ids") or context.get("rag_chunk_ids") or []),
            "memory_ids": list(final_ctx.get("memory_ids") or context.get("memory_ids") or []),
            "stage_count": len(getattr(execution, "stage_results", []) or []),
        }

        # Prefer workflow-enriched context for response generation
        merged_ctx = {**context, **{k: v for k, v in final_ctx.items() if k not in {"raw_insights"}}}
        response = _generate_structured_response(
            session.user_query,
            merged_ctx,
            workflow_results,
            understanding=understanding,
        )

        session.context = {
            **session.context,
            "rag_chunk_ids": workflow_results["rag_chunk_ids"],
            "memory_ids": workflow_results["memory_ids"],
            "llm_understanding": understanding,
        }
        session.result = response
        session.status = AnalystSessionStatus.completed
        session.updated_at = utc_now_iso()
        _SESSION_STORE[session.session_id] = session
        _store_session_memory(session, response)

        # Sprint 7.7 — read-only evaluation after completion (never mutates result).
        try:
            from backend.services.evaluation_service import evaluate_session

            evaluation = evaluate_session(session, execution=execution)
            session.metadata = {
                **dict(session.metadata or {}),
                "evaluation_id": evaluation.evaluation_id,
                "evaluation_score": evaluation.overall_score,
                "evaluation_grade": evaluation.grade,
            }
            # Attach exportable evaluation to response metadata only — do not alter answer.
            if session.result is not None:
                session.result.metadata = {
                    **dict(session.result.metadata or {}),
                    "evaluation_id": evaluation.evaluation_id,
                    "evaluation_score": evaluation.overall_score,
                    "evaluation_grade": evaluation.grade,
                    "evaluation_export": evaluation.export,
                }
            _SESSION_STORE[session.session_id] = session
        except Exception:
            pass

        return session.model_copy(deep=True)
    except Exception as exc:  # noqa: BLE001
        session.status = AnalystSessionStatus.failed
        session.result = AnalystResponse(
            answer=f"Analysis failed: {exc}",
            insights=[],
            recommendations=["Retry the analysis with a clearer query."],
            workflow_results={"error": str(exc)},
            validation_status="invalid",
            metadata={"error_type": type(exc).__name__},
        )
        session.updated_at = utc_now_iso()
        _SESSION_STORE[session.session_id] = session
        return session.model_copy(deep=True)


def analyze_query(
    query: str | AnalystRequest,
    *,
    user_context: dict[str, Any] | None = None,
    session_id: str | None = None,
    follow_up: bool = False,
    initial_context: dict[str, Any] | None = None,
) -> AnalystResponse:
    """Convenience entry: create session (or follow-up) and execute analysis."""
    if isinstance(query, AnalystRequest):
        request = query
        if session_id:
            request.session_id = session_id
        if follow_up:
            request.follow_up = True
        if user_context:
            request.user_context = {**request.user_context, **user_context}
    else:
        request = AnalystRequest(
            query=str(query),
            user_context=dict(user_context or {}),
            session_id=session_id,
            follow_up=follow_up,
        )
    session = create_session(request)
    completed = execute_analysis(session, initial_context=initial_context)
    if completed.result is None:
        return AnalystResponse(
            answer="",
            validation_status="invalid",
            metadata={"session_id": completed.session_id, "status": completed.status.value},
        )
    result = completed.result.model_copy(deep=True)
    result.metadata = {
        **result.metadata,
        "session_id": completed.session_id,
        "workflow_id": completed.workflow_id,
        "status": completed.status.value
        if isinstance(completed.status, AnalystSessionStatus)
        else str(completed.status),
        "evaluation_id": completed.metadata.get("evaluation_id"),
        "evaluation_score": completed.metadata.get("evaluation_score"),
        "evaluation_grade": completed.metadata.get("evaluation_grade"),
    }
    return result
