from __future__ import annotations

"""Storage Statistics page (Sprint 8.4)."""

import streamlit as st

from frontend.api.base import friendly_api_error
from frontend.api.storage_client import StorageClient
from frontend.utils.auth_state import is_authenticated, with_auto_refresh
from frontend.utils.session_state import navigate_to
from frontend.utils.workspace_api import get_api_client


def _client() -> StorageClient:
    return StorageClient(get_api_client())


def render_storage_statistics(client=None) -> None:
    st.header("Storage Statistics")
    st.caption("Quota usage and artifact counts from `/api/v1/storage/statistics`.")

    if not is_authenticated():
        st.warning("Please sign in to view storage statistics.")
        if st.button("Go to Login", key="stats_login"):
            navigate_to("Login")
            st.rerun()
        return

    try:
        stats = with_auto_refresh(lambda t: _client().statistics(t)).get("statistics", {})
    except Exception as exc:
        st.error(friendly_api_error(exc))
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total objects", stats.get("total_objects", 0))
    c2.metric("Active", stats.get("active_objects", 0))
    c3.metric("Total bytes", stats.get("total_bytes", 0))
    c4.metric("Provider", stats.get("provider", "local"))

    c5, c6, c7 = st.columns(3)
    c5.metric("Archived", stats.get("archived_objects", 0))
    c6.metric("Versions", stats.get("total_versions", 0))
    c7.metric("Quota used %", stats.get("quota_used_pct", 0.0))

    st.subheader("By artifact type")
    by_type = stats.get("by_artifact_type") or {}
    if by_type:
        st.bar_chart(by_type)
    else:
        st.info("No artifacts stored yet.")
