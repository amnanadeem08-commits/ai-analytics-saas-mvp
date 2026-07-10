from __future__ import annotations

"""Subscription Management (Sprint 8.6)."""

import streamlit as st

from frontend.api.base import friendly_api_error
from frontend.api.billing_client import BillingClient
from frontend.utils.auth_state import is_authenticated, with_auto_refresh
from frontend.utils.workspace_api import get_api_client


def render_subscription_management(client=None) -> None:
    st.header("Subscription Management")
    if not is_authenticated():
        st.warning("Please sign in.")
        return

    billing = BillingClient(get_api_client())
    org_id = st.text_input("Organization ID", value=st.session_state.get("active_organization_id", ""))

    try:
        plans = with_auto_refresh(lambda t: billing.list_plans(t))
        plan_ids = [p["plan_id"] for p in plans.get("plans") or []]
    except Exception as exc:
        st.error(friendly_api_error(exc))
        return

    if org_id and plan_ids:
        plan = st.selectbox("Plan", plan_ids)
        trial = st.checkbox("Start trial", value=False)
        if st.button("Assign plan", type="primary"):
            try:
                result = with_auto_refresh(lambda t: billing.assign_plan(t, org_id, plan_id=plan, start_trial=trial))
                st.success(f"Assigned plan `{plan}`")
                st.json(result.get("subscription", {}))
            except Exception as exc:
                st.error(friendly_api_error(exc))

    if org_id:
        try:
            sub = with_auto_refresh(lambda t: billing.get_subscription(t, org_id))
            st.subheader("Current subscription")
            st.json(sub.get("subscription", {}))
            limits = with_auto_refresh(lambda t: billing.limits(t, org_id))
            st.subheader("Feature limits")
            st.json(limits.get("limits", []))
        except Exception as exc:
            st.caption(friendly_api_error(exc))
