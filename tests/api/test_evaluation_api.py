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
        title="Eval Playbook",
        content="When analyzing revenue decline, inspect regional KPIs and validate insights.",
        source="analysis_guideline",
        tags=["revenue"],
    )


client = TestClient(app)


def test_evaluation_retrieval_and_export():
    analyzed = client.post(
        "/api/v1/analyst/analyze",
        json={"query": "Analyze revenue decline"},
    )
    assert analyzed.status_code == 200
    session_id = analyzed.json()["session_id"]
    evaluation_id = analyzed.json()["evaluation_id"]
    workflow_id = analyzed.json()["workflow_id"]
    assert evaluation_id

    by_session = client.get(f"/api/v1/evaluation/session/{session_id}")
    assert by_session.status_code == 200
    assert by_session.json()["evaluation_id"] == evaluation_id

    if workflow_id:
        by_workflow = client.get(f"/api/v1/evaluation/workflow/{workflow_id}")
        assert by_workflow.status_code == 200

    report = client.get(f"/api/v1/evaluation/report/{evaluation_id}")
    assert report.status_code == 200
    assert report.json()["report"]
    assert report.json()["metrics"]

    export = client.get(f"/api/v1/evaluation/export/{evaluation_id}")
    assert export.status_code == 200
    payload = export.json()["export"]
    assert "metrics_summary" in payload
    assert "score_breakdown" in payload
    assert payload.get("read_only") is True


def test_evaluation_run_endpoint():
    created = client.post("/api/v1/session/create", json={"query": "Analyze revenue decline"})
    session_id = created.json()["session_id"]
    client.post(f"/api/v1/session/{session_id}/execute", json={})
    rerun = client.post("/api/v1/evaluation/run", json={"session_id": session_id})
    assert rerun.status_code == 200
    assert rerun.json()["grade"] in {"A", "B", "C", "D", "F"}
