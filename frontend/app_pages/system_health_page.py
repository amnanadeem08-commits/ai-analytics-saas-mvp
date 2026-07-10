from __future__ import annotations

"""System Health page (Sprint 8.5)."""

import streamlit as st

from frontend.api.base import friendly_api_error
from frontend.api.monitoring_client import MonitoringClient
from frontend.utils.workspace_api import get_api_client


def _client() -> MonitoringClient:
    return MonitoringClient(get_api_client())


def render_system_health(client=None) -> None:
    st.header("System Health")
    st.caption("Liveness, readiness, and operational health from the monitoring API.")

    mon = _client()
    try:
        live = mon.live()
        ready = mon.ready()
        health = mon.health()
    except Exception as exc:
        st.error(friendly_api_error(exc))
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Liveness", live.get("status", "unknown"))
    c2.metric("Readiness", "ready" if ready.get("ready") else "not ready")
    c3.metric("Overall", health.get("status", "unknown"))

    st.subheader("Dependencies")
    deps = health.get("dependencies") or {}
    for name, info in deps.items():
        st.write(f"**{name}** — `{info.get('status', 'unknown')}`")
        if info.get("error"):
            st.caption(str(info["error"]))
