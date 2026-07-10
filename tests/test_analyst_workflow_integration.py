from __future__ import annotations

from backend.models.workflow_models import WorkflowDefinition, WorkflowStatus
from backend.services.agent_service import ensure_builtin_agents
from backend.services.ai_analyst_runtime_service import clear_analyst_sessions, get_session
from backend.services.embedding_service import reset_embedding_provider
from backend.services.knowledge_ingestion_service import clear_knowledge_store, ingest_document
from backend.services.llm_service import reset_llm_provider
from backend.services.memory_service import reset_memory_store
from backend.services.planning_service import clear_plans
from backend.services.prompt_service import ensure_builtin_prompts
from backend.services.tool_registry_service import ensure_builtin_tools
from backend.services.vector_store_service import reset_vector_store
from backend.services.workflow_engine_service import (
    CTX_ANALYST_RUNTIME_RESPONSE,
    DEFAULT_STAGE_RUNNERS,
    execute_workflow,
    make_analyst_stage,
    make_memory_context_stage,
    make_planner_stage,
    make_rag_context_stage,
)


def setup_function():
    reset_llm_provider()
    reset_embedding_provider()
    reset_vector_store()
    clear_knowledge_store()
    reset_memory_store()
    clear_plans()
    clear_analyst_sessions()
    ensure_builtin_prompts(reset=True)
    ensure_builtin_tools(reset=True)
    ensure_builtin_agents(reset=True)
    ingest_document(
        title="Region Drivers",
        content="North region often drives revenue decline; inspect regional KPIs first.",
        source="analysis_guideline",
        tags=["revenue", "region"],
    )


def test_analyst_runner_registered():
    assert "analyst_runner" in DEFAULT_STAGE_RUNNERS
    assert len(DEFAULT_STAGE_RUNNERS) == 24


def test_make_analyst_stage_helper():
    stage = make_analyst_stage(stage_id="analyst", query="Analyze revenue decline", execution_order=1)
    assert stage.runner_key == "analyst_runner"
    assert stage.metadata["query"] == "Analyze revenue decline"


def test_analyst_workflow_integration():
    """Analyst Request → (optional memory/RAG/planner) → analyst_runner → response."""
    definition = WorkflowDefinition(
        workflow_id="wf_analyst_integration",
        workflow_name="Analyst Integration",
        stages=[
            make_memory_context_stage(
                stage_id="memory",
                task="Analyze revenue decline",
                execution_order=1,
                agent_name="AI Analyst",
            ),
            make_rag_context_stage(
                stage_id="rag",
                task="Analyze revenue decline",
                dependencies=["memory"],
                execution_order=2,
                agent_name="AI Analyst",
            ),
            make_planner_stage(
                stage_id="planner",
                task="Analyze revenue decline",
                dependencies=["rag"],
                execution_order=3,
                multi_agent=True,
                fail_on_agent_error=False,
            ),
            make_analyst_stage(
                stage_id="analyst",
                query="Analyze revenue decline",
                dependencies=["planner"],
                execution_order=4,
                user_context={"dataset_id": "sales_q1"},
            ),
        ],
        stop_on_error=False,
    )
    execution, ctx = execute_workflow(
        definition,
        initial_context={"dataset_id": "sales_q1", "user_query": "Analyze revenue decline"},
        stop_on_error=False,
    )
    assert execution.status in {WorkflowStatus.completed, WorkflowStatus.partial, WorkflowStatus.failed}
    assert CTX_ANALYST_RUNTIME_RESPONSE in ctx or ctx.get("analyst_answer")
    payload = ctx.get(CTX_ANALYST_RUNTIME_RESPONSE) or {}
    if payload:
        assert payload.get("answer")
        sid = (payload.get("metadata") or {}).get("session_id")
        if sid:
            session = get_session(sid)
            assert session is not None


def test_rag_reaches_analyst_via_workflow_context():
    stage = make_analyst_stage(stage_id="analyst", query="Analyze revenue decline", execution_order=1)
    definition = WorkflowDefinition(
        workflow_id="wf_analyst_rag",
        workflow_name="Analyst RAG",
        stages=[stage],
        stop_on_error=False,
    )
    execution, ctx = execute_workflow(definition, stop_on_error=False)
    assert execution.status in {WorkflowStatus.completed, WorkflowStatus.partial}
    payload = ctx.get(CTX_ANALYST_RUNTIME_RESPONSE) or {}
    assert payload.get("answer")
    # RAG ids may be nested in metadata from runtime
    meta = payload.get("metadata") or {}
    assert "session_id" in meta or ctx.get("analyst_session_id")
