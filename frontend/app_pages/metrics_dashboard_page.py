from __future__ import annotations

"""Metrics Dashboard page (Sprint 8.5)."""

import streamlit as st

from frontend.api.base import friendly_api_error
from frontend.api.monitoring_client import MonitoringClient
from frontend.utils.workspace_api import get_api_client


def render_metrics_dashboard(client=None) -> None:
    st.header("Metrics Dashboard")
    st.caption("In-process counters, gauges, and timers from `/api/v1/metrics`.")

    try:
        payload = MonitoringClient(get_api_client()).metrics()
    except Exception as exc:
        st.error(friendly_api_error(exc))
        return

    if not payload.get("enabled", True):
        st.warning("Metrics collection is disabled.")
        return

    metrics = payload.get("metrics") or {}
    counters = metrics.get("counters") or {}
    gauges = metrics.get("gauges") or {}
    timers = metrics.get("timers") or {}

    st.subheader("Counters")
    if counters:
        st.bar_chart(counters)
    else:
        st.info("No counters recorded yet.")

    st.subheader("Gauges")
    st.json(gauges)

    st.subheader("Timers")
    st.json(timers)
