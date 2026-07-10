from __future__ import annotations

"""Usage Dashboard (Sprint 8.6)."""

import streamlit as st

from frontend.api.base import friendly_api_error
from frontend.api.billing_client import BillingClient
from frontend.utils.auth_state import is_authenticated, with_auto_refresh
from frontend.utils.workspace_api import get_api_client


def render_usage_dashboard(client=None) -> None:
    st.header("Usage Dashboard")
    if not is_authenticated():
        st.warning("Please sign in.")
        return
    org_id = st.text_input("Organization ID", value=st.session_state.get("active_organization_id", ""))
    if not org_id:
        return
    try:
        usage = with_auto_refresh(lambda t: BillingClient(get_api_client()).usage(t, org_id))
        totals = usage.get("totals") or {}
        if totals:
            st.bar_chart(totals)
        else:
            st.info("No usage recorded yet.")
        st.json(usage)
    except Exception as exc:
        st.error(friendly_api_error(exc))
