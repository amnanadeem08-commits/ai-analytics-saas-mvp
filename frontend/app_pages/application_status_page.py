from __future__ import annotations

"""Application Status page (Sprint 8.5)."""

import streamlit as st

from frontend.api.base import friendly_api_error
from frontend.api.monitoring_client import MonitoringClient
from frontend.utils.workspace_api import get_api_client


def render_application_status(client=None) -> None:
    st.header("Application Status")
    st.caption("Combined health and runtime metrics from `/api/v1/system/status`.")

    try:
        status = MonitoringClient(get_api_client()).system_status()
    except Exception as exc:
        st.error(friendly_api_error(exc))
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Status", status.get("status", "unknown"))
    c2.metric("App", status.get("app", ""))
    c3.metric("Profile", status.get("profile", ""))

    st.subheader("Details")
    st.json(status)
