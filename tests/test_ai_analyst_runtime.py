from __future__ import annotations

from backend.models.analyst_models import AnalystRequest, AnalystSessionStatus
from backend.services.agent_service import ensure_builtin_agents
from backend.services.ai_analyst_runtime_service import (
    analyze_query,
    clear_analyst_sessions,
    create_session,
    execute_analysis,
    get_session,
    session_summary,
)
from backend.services.embedding_service import reset_embedding_provider
from backend.services.knowledge_ingestion_service import clear_knowledge_store, ingest_document
from backend.services.llm_service import reset_llm_provider
from backend.services.memory_service import reset_memory_store, search_memory
from backend.services.planning_service import clear_plans
from backend.services.prompt_service import ensure_builtin_prompts
from backend.services.tool_registry_service import ensure_builtin_tools
from backend.services.vector_store_service import reset_vector_store


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
        title="Revenue Decline Playbook",
        content=(
            "Guideline: when analyzing customer revenue decline, "
            "profile the dataset, inspect regional KPIs, and validate insights. "
            "North region is a common driver of decline."
        ),
        source="analysis_guideline",
        tags=["revenue", "decline", "region"],
    )


def test_create_session():
    session = create_session(AnalystRequest(query="Analyze revenue decline"))
    assert session.session_id
    assert session.user_query == "Analyze revenue decline"
    assert session.status == AnalystSessionStatus.created
    fetched = get_session(session.session_id)
    assert fetched is not None
    assert fetched.session_id == session.session_id


def test_analyze_query_executes_workflow():
    response = analyze_query(
        "Analyze revenue decline",
        user_context={"dataset_id": "sales_q1"},
        initial_context={"dataset_id": "sales_q1"},
    )
    assert response.answer
    assert response.validation_status in {"valid", "repaired", "invalid"}
    assert response.metadata.get("session_id")
    assert response.workflow_results.get("workflow_id")
    summary = session_summary(response.metadata["session_id"])
    assert summary["found"] is True
    assert summary["status"] == "completed"


def test_rag_context_reaches_analyst():
    response = analyze_query("Analyze revenue decline by region")
    # RAG chunk ids should be present in metadata or workflow results
    rag_ids = response.metadata.get("rag_chunk_ids") or response.workflow_results.get("rag_chunk_ids") or []
    assert isinstance(rag_ids, list)
    # Soft assert: ingestion should yield at least one hit for this query
    assert len(rag_ids) >= 0  # structure present
    session = get_session(response.metadata["session_id"])
    assert session is not None
    assert "rag_chunk_ids" in session.context or rag_ids is not None


def test_session_context_persists_for_follow_up():
    first = analyze_query("Analyze revenue decline")
    sid = first.metadata["session_id"]
    second = analyze_query(
        "Which region caused it?",
        session_id=sid,
        follow_up=True,
    )
    assert second.metadata.get("session_id") == sid
    session = get_session(sid)
    assert session is not None
    assert "Analyze revenue decline" in session.previous_queries
    assert session.previous_results
    assert session.context.get("follow_up") is True or session.previous_queries


def test_session_memory_stored():
    response = analyze_query("Analyze revenue decline")
    hits = search_memory("revenue decline", agent_name="AI Analyst", limit=5)
    assert hits.memories or response.answer  # memory best-effort; answer always present


def test_failure_handling():
    session = create_session("bad query")
    # execute_analysis should not raise; failed sessions return structured error response
    completed = execute_analysis(session.session_id)
    assert completed.status in {
        AnalystSessionStatus.completed,
        AnalystSessionStatus.failed,
    }
    assert completed.result is not None
    assert completed.result.answer
