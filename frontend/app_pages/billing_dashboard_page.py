from __future__ import annotations

"""Billing Dashboard (Sprint 8.6)."""

import streamlit as st

from frontend.api.base import friendly_api_error
from frontend.api.billing_client import BillingClient
from frontend.utils.auth_state import is_authenticated, with_auto_refresh
from frontend.utils.session_state import navigate_to
from frontend.utils.workspace_api import get_api_client


def render_billing_dashboard(client=None) -> None:
    st.header("Billing Dashboard")
    if not is_authenticated():
        st.warning("Please sign in.")
        if st.button("Go to Login"):
            navigate_to("Login")
            st.rerun()
        return

    billing = BillingClient(get_api_client())
    org_id = st.text_input("Organization ID", value=st.session_state.get("active_organization_id", ""))
    if not org_id:
        st.info("Enter an organization ID to view billing.")
        return

    try:
        estimate = with_auto_refresh(lambda t: billing.estimate(t, org_id))
        st.metric("Estimated total (cents)", estimate.get("estimate", {}).get("estimated_total_cents", 0))
        st.json(estimate.get("estimate", {}))
        invoices = with_auto_refresh(lambda t: billing.list_invoices(t, org_id))
        st.subheader(f"Invoices ({invoices.get('count', 0)})")
        for inv in invoices.get("invoices") or []:
            st.write(f"**{inv.get('invoice_id')}** — {inv.get('status')} — ${inv.get('total_cents', 0) / 100:.2f}")
    except Exception as exc:
        st.error(friendly_api_error(exc))
