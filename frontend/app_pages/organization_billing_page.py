from __future__ import annotations

"""Organization Billing (Sprint 8.6)."""

import streamlit as st

from frontend.api.base import friendly_api_error
from frontend.api.billing_client import BillingClient
from frontend.utils.auth_state import is_authenticated, with_auto_refresh
from frontend.utils.workspace_api import get_api_client


def render_organization_billing(client=None) -> None:
    st.header("Organization Billing")
    if not is_authenticated():
        st.warning("Please sign in.")
        return
    org_id = st.text_input("Organization ID", value=st.session_state.get("active_organization_id", ""))
    if not org_id:
        return
    billing = BillingClient(get_api_client())
    try:
        if st.button("Generate invoice"):
            inv = with_auto_refresh(lambda t: billing.generate_invoice(t, org_id))
            st.success(f"Invoice {inv.get('invoice', {}).get('invoice_id')} created")
        estimate = with_auto_refresh(lambda t: billing.estimate(t, org_id))
        st.subheader("Estimate")
        st.json(estimate.get("estimate", {}))
    except Exception as exc:
        st.error(friendly_api_error(exc))
