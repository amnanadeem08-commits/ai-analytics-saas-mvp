from __future__ import annotations

"""Billing Dashboard (Sprint 8.6 + payment gateway)."""

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
        gateway = with_auto_refresh(lambda t: billing.gateway_status(t))
        gw = gateway.get("gateway") or {}
        st.caption(
            f"Payment gateway: {gw.get('active_provider', 'unknown')} "
            f"({'live' if gw.get('is_live') else 'test/internal'})"
        )

        estimate = with_auto_refresh(lambda t: billing.estimate(t, org_id))
        st.metric("Estimated total (cents)", estimate.get("estimate", {}).get("estimated_total_cents", 0))
        st.json(estimate.get("estimate", {}))

        if st.button("Generate invoice", use_container_width=True):
            created = with_auto_refresh(lambda t: billing.generate_invoice(t, org_id))
            st.success(f"Invoice created: {created.get('invoice', {}).get('invoice_id')}")
            st.rerun()

        invoices = with_auto_refresh(lambda t: billing.list_invoices(t, org_id))
        st.subheader(f"Invoices ({invoices.get('count', 0)})")
        for inv in invoices.get("invoices") or []:
            invoice_id = inv.get("invoice_id")
            status = inv.get("status")
            st.write(f"**{invoice_id}** — {status} — ${inv.get('total_cents', 0) / 100:.2f}")
            if status in {"open", "overdue", "draft"} and invoice_id:
                if st.button(f"Pay {invoice_id}", key=f"pay_{invoice_id}"):
                    checkout = with_auto_refresh(lambda t, iid=invoice_id: billing.start_checkout(t, iid))
                    session = checkout.get("checkout") or {}
                    if session.get("status") == "succeeded":
                        st.success("Invoice paid.")
                        st.rerun()
                    elif session.get("checkout_url"):
                        st.info(f"Complete payment: {session['checkout_url']}")
                    else:
                        st.warning("Checkout started but no URL returned.")
    except Exception as exc:
        st.error(friendly_api_error(exc))
