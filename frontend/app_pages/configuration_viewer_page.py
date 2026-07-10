from __future__ import annotations

"""Configuration Viewer (read-only) — Sprint 8.5."""

import streamlit as st

from frontend.api.base import friendly_api_error
from frontend.api.monitoring_client import MonitoringClient
from frontend.utils.workspace_api import get_api_client


def render_configuration_viewer(client=None) -> None:
    st.header("Configuration Viewer")
    st.caption("Read-only redacted configuration from `/api/v1/system/config`.")

    try:
        payload = MonitoringClient(get_api_client()).system_config()
    except Exception as exc:
        st.error(friendly_api_error(exc))
        return

    st.json(payload.get("config") or {})
