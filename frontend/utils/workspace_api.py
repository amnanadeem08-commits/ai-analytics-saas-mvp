from __future__ import annotations

from typing import Any

import streamlit as st

from frontend.api.analyst_client import AnalystClient
from frontend.api.base import ApiClient, ApiError, DEFAULT_API_BASE_URL, friendly_api_error
from frontend.api.dataset_client import DatasetClient
from frontend.api.evaluation_client import EvaluationClient
from frontend.api.knowledge_client import KnowledgeClient
from frontend.api.system_client import SystemClient
from frontend.api.workflow_client import WorkflowClient


def get_api_client(base_url: str | None = None) -> ApiClient:
    url = (base_url or st.session_state.get("api_base_url") or DEFAULT_API_BASE_URL).rstrip("/")
    return ApiClient(base_url=url)


def get_workspace_clients(base_url: str | None = None) -> dict[str, Any]:
    api = get_api_client(base_url)
    return {
        "api": api,
        "analyst": AnalystClient(api),
        "workflow": WorkflowClient(api),
        "evaluation": EvaluationClient(api),
        "knowledge": KnowledgeClient(api),
        "system": SystemClient(api),
        "dataset": DatasetClient(api),
    }


def show_api_error(exc: Exception) -> None:
    st.error(friendly_api_error(exc))
    if isinstance(exc, ApiError) and exc.details and st.session_state.get("show_api_details"):
        st.caption("Details")
        st.json(exc.details)


def remember_session(session_id: str, *, query: str = "", summary: dict[str, Any] | None = None) -> None:
    history: list[dict[str, Any]] = list(st.session_state.get("analyst_session_history", []))
    history = [h for h in history if h.get("session_id") != session_id]
    history.insert(
        0,
        {
            "session_id": session_id,
            "query": query,
            "summary": summary or {},
        },
    )
    st.session_state["analyst_session_history"] = history[:40]
    st.session_state["active_analyst_session_id"] = session_id


def remember_execution(execution_id: str, *, query: str = "", status: str = "") -> None:
    history: list[dict[str, Any]] = list(st.session_state.get("workflow_execution_history", []))
    history = [h for h in history if h.get("execution_id") != execution_id]
    history.insert(0, {"execution_id": execution_id, "query": query, "status": status})
    st.session_state["workflow_execution_history"] = history[:40]
    st.session_state["active_workflow_execution_id"] = execution_id
