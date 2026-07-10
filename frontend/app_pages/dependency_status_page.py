from __future__ import annotations

"""Dependency Status page (Sprint 8.5)."""

import streamlit as st

from frontend.api.base import friendly_api_error
from frontend.api.monitoring_client import MonitoringClient
from frontend.utils.workspace_api import get_api_client


def render_dependency_status(client=None) -> None:
    st.header("Dependency Status")
    st.caption("Database, storage, queue, worker, and memory probes.")

    try:
        payload = MonitoringClient(get_api_client()).dependencies()
    except Exception as exc:
        st.error(friendly_api_error(exc))
        return

    deps = payload.get("dependencies") or {}
    for name, info in deps.items():
        with st.expander(f"{name} — {info.get('status', 'unknown')}"):
            st.json(info)
