from __future__ import annotations

"""Admin Dashboard (Sprint 8.6)."""

import streamlit as st

from frontend.api.admin_client import AdminClient
from frontend.api.base import friendly_api_error
from frontend.utils.auth_state import is_authenticated, with_auto_refresh
from frontend.utils.workspace_api import get_api_client


def render_admin_dashboard(client=None) -> None:
    st.header("Admin Dashboard")
    if not is_authenticated():
        st.warning("Please sign in.")
        return
    try:
        data = with_auto_refresh(lambda t: AdminClient(get_api_client()).dashboard(t))
        dash = data.get("dashboard", {})
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Plans", dash.get("plans", 0))
        c2.metric("Subscriptions", dash.get("active_subscriptions", 0))
        c3.metric("API Keys", dash.get("api_keys", 0))
        c4.metric("Invoices", dash.get("invoices", 0))
        st.json(dash)
    except Exception as exc:
        st.error(friendly_api_error(exc))
