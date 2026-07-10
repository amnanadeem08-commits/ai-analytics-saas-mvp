from __future__ import annotations

import pytest

from backend.models.memory_models import MemoryType
from backend.services.memory_service import (
    clear_expired_memory,
    delete_memory,
    memory_summary,
    reset_memory_store,
    retrieve_memory,
    search_memory,
    store_memory,
    update_memory,
)


def setup_function():
    reset_memory_store()


def test_store_and_retrieve_memory():
    memory = store_memory(
        agent_name="Data Analyst Agent",
        content={"task": "Analyze revenue", "summary": "North declined"},
        memory_type=MemoryType.TASK_MEMORY,
        source="task_summary",
        relevance_score=0.9,
        tags=["revenue"],
    )
    assert memory.memory_id
    found = retrieve_memory(memory.memory_id)
    assert found is not None
    assert found.content["summary"] == "North declined"


def test_search_memory_relevance():
    store_memory(
        agent_name="Insight Agent",
        content={"task": "KPI review", "tool_calls": ["kpi_detection"]},
        memory_type=MemoryType.EXECUTION_HISTORY,
        source="tool_result",
        tags=["kpi"],
    )
    store_memory(
        agent_name="Insight Agent",
        content={"task": "Unrelated weather note", "summary": "rain"},
        memory_type=MemoryType.TASK_MEMORY,
        source="task_summary",
        relevance_score=0.1,
    )
    result = search_memory("Find important KPIs", agent_name="Insight Agent", limit=5)
    assert result.memories
    assert any("kpi" in str(m.content).lower() or "KPI" in str(m.content) for m in result.memories)


def test_update_delete_and_summary():
    memory = store_memory(
        agent_name="Validation Agent",
        content={"validation_passed": True, "task": "validate"},
        source="validation_result",
        memory_type=MemoryType.KNOWLEDGE_MEMORY,
    )
    updated = update_memory(memory.memory_id, relevance_score=0.95, tags=["validated"])
    assert updated.relevance_score == 0.95
    assert "validated" in updated.tags
    summary = memory_summary("Validation Agent")
    assert summary["total"] >= 1
    assert delete_memory(memory.memory_id) is True
    assert retrieve_memory(memory.memory_id) is None


def test_expired_memory_cleanup():
    memory = store_memory(
        agent_name="Reporting Agent",
        content={"task": "temp", "summary": "short lived"},
        source="execution_history",
        memory_type=MemoryType.SHORT_TERM,
        ttl_seconds=-1,  # already expired
    )
    assert retrieve_memory(memory.memory_id) is None
    removed = clear_expired_memory()
    assert memory.memory_id in removed
    assert memory_summary()["expired"] == 0


def test_forbidden_content_rejected():
    with pytest.raises(ValueError):
        store_memory(
            agent_name="Data Analyst Agent",
            content={"password": "secret123", "task": "hack"},
            source="task_summary",
        )
    with pytest.raises(ValueError):
        store_memory(
            agent_name="Data Analyst Agent",
            content={"summary": "ok"},
            source="not_allowed_source",
        )
