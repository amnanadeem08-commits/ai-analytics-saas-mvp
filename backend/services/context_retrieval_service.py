from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from backend.models.memory_models import (
    AgentContextBundle,
    MemoryQuery,
    MemoryResult,
    MemoryType,
)
from backend.services.memory_service import search_memory


def retrieve_relevant_context(
    task: str,
    *,
    agent_name: str = "",
    memory_types: list[MemoryType] | None = None,
    limit: int = 8,
    tags: list[str] | None = None,
) -> MemoryResult:
    """Retrieve memories relevant to a task for an agent."""
    types = memory_types or [
        MemoryType.TASK_MEMORY,
        MemoryType.KNOWLEDGE_MEMORY,
        MemoryType.EXECUTION_HISTORY,
        MemoryType.SHORT_TERM,
    ]
    return search_memory(
        MemoryQuery(
            agent_name=agent_name,
            query=task,
            memory_types=types,
            limit=limit,
            tags=list(tags or []),
        )
    )


def merge_context(
    runtime_context: Mapping[str, Any] | None,
    memory_result: MemoryResult,
    *,
    task: str = "",
    agent_name: str = "",
) -> dict[str, Any]:
    """Merge runtime workflow context with retrieved memory snippets."""
    merged = dict(runtime_context or {})
    snippets: list[dict[str, Any]] = []
    for memory, score in zip(memory_result.memories, memory_result.relevance, strict=False):
        snippets.append(
            {
                "memory_id": memory.memory_id,
                "memory_type": memory.memory_type.value,
                "source": memory.source,
                "relevance": score,
                "content": dict(memory.content),
                "tags": list(memory.tags),
            }
        )
    # Pad relevance if lengths differ.
    while len(snippets) < len(memory_result.memories):
        memory = memory_result.memories[len(snippets)]
        snippets.append(
            {
                "memory_id": memory.memory_id,
                "memory_type": memory.memory_type.value,
                "source": memory.source,
                "relevance": memory.relevance_score,
                "content": dict(memory.content),
                "tags": list(memory.tags),
            }
        )

    merged["memory_snippets"] = snippets
    merged["memory_ids"] = [s["memory_id"] for s in snippets]
    if task:
        merged.setdefault("planning_task", task)
        # Soft hints for planners from prior successful tools.
        prior_tools: list[str] = []
        for snippet in snippets:
            tools = snippet.get("content", {}).get("tool_calls")
            if isinstance(tools, list):
                prior_tools.extend(str(t) for t in tools)
        if prior_tools:
            # Preserve order, unique.
            seen: set[str] = set()
            ordered: list[str] = []
            for tool in prior_tools:
                if tool not in seen:
                    seen.add(tool)
                    ordered.append(tool)
            merged["memory_suggested_tools"] = ordered
    if agent_name:
        merged["memory_agent_name"] = agent_name
    return merged


def build_agent_context(
    task: str,
    *,
    agent_name: str = "",
    runtime_context: Mapping[str, Any] | None = None,
    memory_types: list[MemoryType] | None = None,
    limit: int = 8,
) -> AgentContextBundle:
    """
    Task → Retrieve relevant memory → Add context.

    Returns a bundle ready for planning/execution.
    """
    memory_result = retrieve_relevant_context(
        task,
        agent_name=agent_name,
        memory_types=memory_types,
        limit=limit,
    )
    merged = merge_context(
        runtime_context,
        memory_result,
        task=task,
        agent_name=agent_name,
    )
    snippets = list(merged.get("memory_snippets") or [])
    return AgentContextBundle(
        agent_name=agent_name,
        task=task,
        runtime_context=dict(runtime_context or {}),
        memory_result=memory_result,
        memory_snippets=snippets,
        merged_context=merged,
        metadata={
            "memory_count": len(memory_result.memories),
            "source_information": memory_result.source_information,
        },
    )
