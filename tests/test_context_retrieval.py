from __future__ import annotations

from backend.models.memory_models import MemoryType
from backend.services.context_retrieval_service import (
    build_agent_context,
    merge_context,
    retrieve_relevant_context,
)
from backend.services.memory_service import reset_memory_store, store_memory


def setup_function():
    reset_memory_store()


def test_retrieve_relevant_context():
    store_memory(
        agent_name="Data Analyst Agent",
        content={"task": "Analyze customer revenue decline", "tool_calls": ["data_profiling"]},
        memory_type=MemoryType.EXECUTION_HISTORY,
        source="tool_result",
        relevance_score=0.8,
    )
    result = retrieve_relevant_context(
        "Analyze customer revenue decline",
        agent_name="Data Analyst Agent",
    )
    assert result.memories
    assert result.relevance


def test_merge_and_build_agent_context():
    store_memory(
        agent_name="Data Analyst Agent",
        content={
            "task": "Analyze customer revenue decline",
            "tool_calls": ["data_profiling", "kpi_detection"],
            "summary": "Prior run found North decline",
        },
        memory_type=MemoryType.KNOWLEDGE_MEMORY,
        source="business_insight",
        relevance_score=0.85,
        tags=["revenue"],
    )
    bundle = build_agent_context(
        "Analyze customer revenue decline",
        agent_name="Data Analyst Agent",
        runtime_context={"dataset_id": "sales_q1", "domain": "Sales"},
    )
    assert bundle.merged_context["dataset_id"] == "sales_q1"
    assert bundle.memory_snippets
    assert "memory_suggested_tools" in bundle.merged_context
    assert "data_profiling" in bundle.merged_context["memory_suggested_tools"]

    merged = merge_context(
        {"dataset_id": "sales_q1"},
        bundle.memory_result,
        task="Analyze customer revenue decline",
        agent_name="Data Analyst Agent",
    )
    assert merged["memory_ids"]
