from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app
from backend.services.agent_service import ensure_builtin_agents
from backend.services.ai_analyst_runtime_service import clear_analyst_sessions
from backend.services.embedding_service import reset_embedding_provider
from backend.services.evaluation_service import clear_evaluations
from backend.services.knowledge_ingestion_service import clear_knowledge_store, ingest_document
from backend.services.llm_service import reset_llm_provider
from backend.services.memory_service import reset_memory_store
from backend.services.planning_service import clear_plans
from backend.services.prompt_service import ensure_builtin_prompts
from backend.services.tool_registry_service import ensure_builtin_tools
from backend.services.vector_store_service import reset_vector_store
from backend.services.workflow_engine_service import clear_execution_store


def setup_function():
    reset_llm_provider()
    reset_embedding_provider()
    reset_vector_store()
    clear_knowledge_store()
    reset_memory_store()
    clear_plans()
    clear_analyst_sessions()
    clear_evaluations()
    clear_execution_store()
    ensure_builtin_prompts(reset=True)
    ensure_builtin_tools(reset=True)
    ensure_builtin_agents(reset=True)
    ingest_document(
        title="Revenue Decline Playbook",
        content=(
            "Guideline: when analyzing customer revenue decline, "
            "profile the dataset and inspect regional KPIs. "
            "North region is a common driver of decline."
        ),
        source="analysis_guideline",
        tags=["revenue", "decline"],
    )


client = TestClient(app)


def test_analyst_analyze_endpoint():
    response = client.post(
        "/api/v1/analyst/analyze",
        json={"query": "Analyze revenue decline", "user_context": {"dataset_id": "sales_q1"}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["answer"]
    assert body["session_id"]
    assert body.get("evaluation_id")


def test_session_create_get_summary():
    created = client.post(
        "/api/v1/session/create",
        json={"query": "Analyze revenue decline"},
    )
    assert created.status_code == 201
    session_id = created.json()["session_id"]

    detail = client.get(f"/api/v1/session/{session_id}")
    assert detail.status_code == 200
    assert detail.json()["session_id"] == session_id

    summary = client.get(f"/api/v1/session/{session_id}/summary")
    assert summary.status_code == 200
    assert summary.json()["found"] is True

    missing = client.get("/api/v1/session/does_not_exist")
    assert missing.status_code == 404
    assert missing.json()["success"] is False


def test_session_execute_and_evaluation():
    created = client.post(
        "/api/v1/session/create",
        json={"query": "Analyze revenue decline"},
    )
    session_id = created.json()["session_id"]
    executed = client.post(f"/api/v1/session/{session_id}/execute", json={})
    assert executed.status_code == 200
    assert executed.json()["answer"]

    evaluation = client.get(f"/api/v1/session/{session_id}/evaluation")
    assert evaluation.status_code == 200
    assert evaluation.json()["evaluation_id"]
    assert evaluation.json()["grade"] in {"A", "B", "C", "D", "F"}
