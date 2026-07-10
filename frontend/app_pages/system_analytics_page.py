from __future__ import annotations

"""System Analytics (Sprint 8.6)."""

import streamlit as st

from frontend.api.admin_client import AdminClient
from frontend.api.base import friendly_api_error
from frontend.utils.auth_state import is_authenticated, with_auto_refresh
from frontend.utils.workspace_api import get_api_client


def render_system_analytics(client=None) -> None:
    st.header("System Analytics")
    if not is_authenticated():
        st.warning("Please sign in.")
        return
    try:
        stats = with_auto_refresh(lambda t: AdminClient(get_api_client()).statistics(t))
        st.json(stats.get("statistics", {}))
    except Exception as exc:
        st.error(friendly_api_error(exc))
