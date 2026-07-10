from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any
from collections.abc import Mapping

from backend.models.ai_insight_models import utc_now_iso
from backend.models.memory_models import (
    ALLOWED_MEMORY_SOURCES,
    FORBIDDEN_CONTENT_KEYS,
    MEMORY_SCHEMA_VERSION,
    AgentMemory,
    MemoryQuery,
    MemoryResult,
    MemoryType,
    empty_memory_future_extensions,
)


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _is_expired(memory: AgentMemory, *, now: datetime | None = None) -> bool:
    expiry = _parse_iso(memory.expiry)
    if expiry is None:
        return False
    return expiry <= (now or _now())


def _contains_forbidden(value: Any, *, path: str = "") -> list[str]:
    issues: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_l = str(key).lower()
            if key_l in FORBIDDEN_CONTENT_KEYS or any(f in key_l for f in FORBIDDEN_CONTENT_KEYS):
                issues.append(f"Forbidden key: {path + key if path else key}")
                continue
            issues.extend(_contains_forbidden(item, path=f"{path}{key}."))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            issues.extend(_contains_forbidden(item, path=f"{path}{index}."))
    elif isinstance(value, str):
        lower = value.lower()
        for forbidden in ("password=", "api_key=", "secret=", "bearer "):
            if forbidden in lower:
                issues.append(f"Forbidden content pattern at {path or 'value'}")
                break
    return issues


def sanitize_memory_content(content: Mapping[str, Any] | dict[str, Any]) -> dict[str, Any]:
    """Drop forbidden keys; raise if content is entirely invalid."""
    raw = dict(content or {})
    issues = _contains_forbidden(raw)
    if issues:
        raise ValueError(f"Memory content violates knowledge boundaries: {'; '.join(issues[:5])}")
    cleaned: dict[str, Any] = {}
    for key, value in raw.items():
        key_l = str(key).lower()
        if key_l in FORBIDDEN_CONTENT_KEYS or any(f in key_l for f in FORBIDDEN_CONTENT_KEYS):
            continue
        cleaned[key] = value
    return cleaned


class MemoryStore(ABC):
    """Storage abstraction — in-memory now; future Postgres/Redis/vector backends."""

    @abstractmethod
    def upsert(self, memory: AgentMemory) -> AgentMemory:
        raise NotImplementedError

    @abstractmethod
    def get(self, memory_id: str) -> AgentMemory | None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, memory_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[AgentMemory]:
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        raise NotImplementedError


class InMemoryMemoryStore(MemoryStore):
    """Default process-local store. No DB migration required."""

    def __init__(self) -> None:
        self._items: dict[str, AgentMemory] = {}

    def upsert(self, memory: AgentMemory) -> AgentMemory:
        item = memory.model_copy(deep=True)
        self._items[item.memory_id] = item
        return item.model_copy(deep=True)

    def get(self, memory_id: str) -> AgentMemory | None:
        item = self._items.get(memory_id)
        return item.model_copy(deep=True) if item is not None else None

    def delete(self, memory_id: str) -> bool:
        return self._items.pop(memory_id, None) is not None

    def list_all(self) -> list[AgentMemory]:
        return [item.model_copy(deep=True) for item in self._items.values()]

    def clear(self) -> None:
        self._items.clear()


_STORE: MemoryStore = InMemoryMemoryStore()


def get_memory_store() -> MemoryStore:
    return _STORE


def set_memory_store(store: MemoryStore) -> MemoryStore:
    global _STORE
    _STORE = store
    return store


def reset_memory_store() -> MemoryStore:
    store = InMemoryMemoryStore()
    return set_memory_store(store)


def _score_memory(memory: AgentMemory, query: str) -> float:
    text = " ".join(str(query or "").lower().split())
    if not text:
        return float(memory.relevance_score or 0.0)
    blob_parts = [
        memory.agent_name,
        memory.memory_type.value,
        memory.source,
        " ".join(memory.tags),
        str(memory.content),
    ]
    blob = " ".join(blob_parts).lower()
    score = float(memory.relevance_score or 0.0)
    for token in text.split():
        if len(token) > 2 and token in blob:
            score += 0.5
    if memory.memory_type == MemoryType.KNOWLEDGE_MEMORY:
        score += 0.2
    if memory.memory_type == MemoryType.EXECUTION_HISTORY:
        score += 0.1
    return round(score, 4)


def store_memory(
    *,
    agent_name: str,
    content: Mapping[str, Any] | dict[str, Any],
    memory_type: MemoryType | str = MemoryType.TASK_MEMORY,
    source: str = "manual",
    relevance_score: float = 0.5,
    expiry: str | None = None,
    ttl_seconds: int | None = None,
    tags: list[str] | None = None,
    memory_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AgentMemory:
    """Persist an approved memory record after boundary checks."""
    if source not in ALLOWED_MEMORY_SOURCES:
        raise ValueError(f"Memory source not allowed: {source}")
    cleaned = sanitize_memory_content(content)
    if not cleaned:
        raise ValueError("Memory content is empty after sanitization")

    mtype = memory_type if isinstance(memory_type, MemoryType) else MemoryType(str(memory_type))
    now = utc_now_iso()
    resolved_expiry = expiry
    if resolved_expiry is None and ttl_seconds is not None:
        resolved_expiry = (_now() + timedelta(seconds=int(ttl_seconds))).isoformat().replace("+00:00", "Z")
    if resolved_expiry is None and mtype == MemoryType.SHORT_TERM:
        resolved_expiry = (_now() + timedelta(hours=1)).isoformat().replace("+00:00", "Z")

    memory = AgentMemory(
        memory_id=memory_id or f"mem_{now.replace(':', '').replace('-', '')}_{mtype.value.lower()}",
        agent_name=agent_name,
        memory_type=mtype,
        content=cleaned,
        source=source,
        relevance_score=float(relevance_score),
        created_at=now,
        expiry=resolved_expiry,
        tags=list(tags or []),
        metadata={
            **dict(metadata or {}),
            "schema": MEMORY_SCHEMA_VERSION,
            "future_extensions": empty_memory_future_extensions(),
        },
    )
    return get_memory_store().upsert(memory)


def retrieve_memory(memory_id: str) -> AgentMemory | None:
    item = get_memory_store().get(memory_id)
    if item is None:
        return None
    if _is_expired(item):
        return None
    return item


def search_memory(query: MemoryQuery | str, **kwargs: Any) -> MemoryResult:
    if isinstance(query, str):
        q = MemoryQuery(query=query, **kwargs)
    else:
        q = query.model_copy(deep=True)
        for key, value in kwargs.items():
            setattr(q, key, value)

    now = _now()
    matches: list[tuple[float, AgentMemory]] = []
    for item in get_memory_store().list_all():
        if not q.include_expired and _is_expired(item, now=now):
            continue
        if q.agent_name and item.agent_name and item.agent_name != q.agent_name:
            # Allow shared/global memories with empty agent_name.
            if item.agent_name not in {"", "*", "shared"}:
                continue
        if q.memory_types and item.memory_type not in q.memory_types:
            continue
        if q.tags and not set(q.tags).intersection(item.tags):
            continue
        score = _score_memory(item, q.query)
        if q.query and score <= float(item.relevance_score or 0.0) and q.query.lower() not in str(item.content).lower():
            # Require at least some lexical hit when a query is provided.
            if score < 0.1:
                continue
        matches.append((score, item))

    matches.sort(key=lambda pair: (-pair[0], pair[1].created_at))
    limited = matches[: max(1, q.limit)]
    return MemoryResult(
        memories=[m for _, m in limited],
        relevance=[s for s, _ in limited],
        source_information={
            "query": q.query,
            "agent_name": q.agent_name,
            "total_candidates": len(matches),
            "returned": len(limited),
            "store": type(get_memory_store()).__name__,
        },
    )


def update_memory(
    memory_id: str,
    *,
    content: Mapping[str, Any] | None = None,
    relevance_score: float | None = None,
    expiry: str | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> AgentMemory:
    existing = get_memory_store().get(memory_id)
    if existing is None:
        raise KeyError(f"Unknown memory: {memory_id}")
    data = existing.model_dump()
    if content is not None:
        data["content"] = sanitize_memory_content(content)
    if relevance_score is not None:
        data["relevance_score"] = float(relevance_score)
    if expiry is not None:
        data["expiry"] = expiry
    if tags is not None:
        data["tags"] = list(tags)
    if metadata is not None:
        data["metadata"] = {**existing.metadata, **metadata}
    updated = AgentMemory.model_validate(data)
    return get_memory_store().upsert(updated)


def delete_memory(memory_id: str) -> bool:
    return get_memory_store().delete(memory_id)


def clear_expired_memory() -> list[str]:
    removed: list[str] = []
    now = _now()
    for item in get_memory_store().list_all():
        if _is_expired(item, now=now):
            get_memory_store().delete(item.memory_id)
            removed.append(item.memory_id)
    return removed


def memory_summary(agent_name: str | None = None) -> dict[str, Any]:
    items = get_memory_store().list_all()
    if agent_name:
        items = [m for m in items if m.agent_name in {agent_name, "", "*", "shared"}]
    by_type: dict[str, int] = {}
    expired = 0
    now = _now()
    for item in items:
        by_type[item.memory_type.value] = by_type.get(item.memory_type.value, 0) + 1
        if _is_expired(item, now=now):
            expired += 1
    return {
        "total": len(items),
        "expired": expired,
        "by_type": by_type,
        "agent_name": agent_name,
        "store": type(get_memory_store()).__name__,
        "schema": MEMORY_SCHEMA_VERSION,
    }


def store_execution_memories(
    *,
    agent_name: str,
    task: str,
    execution_id: str,
    tool_calls: list[str],
    plan_status: str,
    summary: str,
    findings: list[str] | None = None,
    validation_passed: bool | None = None,
    context_keys: list[str] | None = None,
) -> list[AgentMemory]:
    """Store approved execution artifacts after a reasoning loop."""
    stored: list[AgentMemory] = []
    stored.append(
        store_memory(
            agent_name=agent_name,
            memory_type=MemoryType.TASK_MEMORY,
            source="task_summary",
            relevance_score=0.8,
            tags=["task", "summary"],
            content={
                "task": task,
                "summary": summary,
                "execution_id": execution_id,
                "plan_status": plan_status,
            },
        )
    )
    if tool_calls:
        stored.append(
            store_memory(
                agent_name=agent_name,
                memory_type=MemoryType.EXECUTION_HISTORY,
                source="tool_result",
                relevance_score=0.7,
                tags=["tools", "execution"],
                content={
                    "task": task,
                    "tool_calls": list(tool_calls),
                    "execution_id": execution_id,
                },
            )
        )
    if validation_passed is not None:
        stored.append(
            store_memory(
                agent_name=agent_name,
                memory_type=MemoryType.KNOWLEDGE_MEMORY,
                source="validation_result",
                relevance_score=0.75,
                tags=["validation"],
                content={
                    "task": task,
                    "validation_passed": bool(validation_passed),
                    "execution_id": execution_id,
                },
            )
        )
    if findings:
        stored.append(
            store_memory(
                agent_name=agent_name,
                memory_type=MemoryType.KNOWLEDGE_MEMORY,
                source="business_insight",
                relevance_score=0.65,
                tags=["insight"],
                content={
                    "task": task,
                    "findings": list(findings)[:12],
                    "context_keys": list(context_keys or [])[:20],
                },
            )
        )
    # Short-term scratch for immediate follow-ups.
    stored.append(
        store_memory(
            agent_name=agent_name,
            memory_type=MemoryType.SHORT_TERM,
            source="execution_history",
            relevance_score=0.55,
            ttl_seconds=3600,
            tags=["short_term"],
            content={
                "task": task,
                "execution_id": execution_id,
                "recent": True,
            },
        )
    )
    return stored
