from __future__ import annotations

"""API Key Manager (Sprint 8.6)."""

import streamlit as st

from frontend.api.apikey_client import ApiKeyClient
from frontend.api.base import friendly_api_error
from frontend.utils.auth_state import is_authenticated, with_auto_refresh
from frontend.utils.workspace_api import get_api_client


def render_api_key_manager(client=None) -> None:
    st.header("API Key Manager")
    if not is_authenticated():
        st.warning("Please sign in.")
        return

    keys = ApiKeyClient(get_api_client())
    org_id = st.text_input("Organization ID", value=st.session_state.get("active_organization_id", ""))
    name = st.text_input("Key name", value="Integration key")
    scopes = st.multiselect("Scopes", ["read", "write", "ai_analyst", "workflows", "knowledge", "storage", "jobs"], default=["read"])

    if st.button("Create API key", type="primary") and org_id:
        try:
            result = with_auto_refresh(lambda t: keys.create(t, name=name, organization_id=org_id, scopes=scopes))
            st.success("API key created — copy the secret now.")
            st.code(result.get("secret", ""))
        except Exception as exc:
            st.error(friendly_api_error(exc))

    try:
        listing = with_auto_refresh(lambda t: keys.list(t, organization_id=org_id or None, mine=not bool(org_id)))
        for key in listing.get("keys") or []:
            cols = st.columns([3, 2, 1, 1])
            cols[0].write(f"**{key.get('name')}**")
            cols[1].caption(key.get("key_prefix", ""))
            kid = key.get("key_id")
            if cols[2].button("Rotate", key=f"rot_{kid}"):
                with_auto_refresh(lambda t: keys.rotate(t, kid))
                st.rerun()
            if cols[3].button("Revoke", key=f"rev_{kid}"):
                with_auto_refresh(lambda t: keys.revoke(t, kid))
                st.rerun()
    except Exception as exc:
        st.error(friendly_api_error(exc))
