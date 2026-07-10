from __future__ import annotations

"""Centralized service accessors for the Sprint 7.8 API gateway.

Routes should obtain services through this module to avoid duplicated
initialization. No business logic lives here.
"""

from typing import Any


def get_analyst_runtime():
    from backend.services import ai_analyst_runtime_service as svc

    return svc


def get_ai_analyst_service():
    from backend.services import ai_analyst_service as svc

    return svc


def get_workflow_engine():
    from backend.services import workflow_engine_service as svc

    return svc


def get_evaluation_service():
    from backend.services import evaluation_service as svc

    return svc


def get_knowledge_ingestion():
    from backend.services import knowledge_ingestion_service as svc

    return svc


def get_rag_service():
    from backend.services import rag_service as svc

    return svc


def get_memory_service():
    from backend.services import memory_service as svc

    return svc


def get_llm_service():
    from backend.services import llm_service as svc

    return svc


def ensure_runtime_ready() -> dict[str, Any]:
    """Idempotent bootstrap for agents/tools/prompts used by analyst/workflow APIs."""
    from backend.services.agent_service import ensure_builtin_agents
    from backend.services.prompt_service import ensure_builtin_prompts
    from backend.services.tool_registry_service import ensure_builtin_tools

    ensure_builtin_prompts()
    ensure_builtin_tools()
    ensure_builtin_agents()
    return {"agents": True, "tools": True, "prompts": True}
