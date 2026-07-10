from __future__ import annotations

"""Dataset Versions page (Sprint 8.4)."""

import streamlit as st

from frontend.api.base import friendly_api_error
from frontend.api.storage_client import StorageClient
from frontend.utils.auth_state import is_authenticated, with_auto_refresh
from frontend.utils.session_state import navigate_to
from frontend.utils.workspace_api import get_api_client


def _client() -> StorageClient:
    return StorageClient(get_api_client())


def render_dataset_versions(client=None) -> None:
    st.header("Dataset Versions")
    st.caption("Inspect version history for dataset storage objects.")

    if not is_authenticated():
        st.warning("Please sign in to view dataset versions.")
        if st.button("Go to Login", key="dsver_login"):
            navigate_to("Login")
            st.rerun()
        return

    storage = _client()
    try:
        listing = with_auto_refresh(lambda t: storage.list_files(t, artifact_type="dataset", mine=True))
        objects = listing.get("objects") or []
    except Exception as exc:
        st.error(friendly_api_error(exc))
        return

    if not objects:
        st.info("No dataset storage objects found. Upload a dataset first.")
        return

    labels = [f"{o.get('name')} ({o.get('object_id')})" for o in objects]
    choice = st.selectbox("Dataset object", options=labels)
    obj = objects[labels.index(choice)]
    st.write(f"Current version: **v{obj.get('current_version')}** · Status: `{obj.get('status')}`")

    versions = obj.get("versions") or []
    for ver in sorted(versions, key=lambda v: v.get("version_number", 0), reverse=True):
        current = " (current)" if ver.get("is_current") else ""
        st.markdown(
            f"- **v{ver.get('version_number')}**{current} — "
            f"{ver.get('size_bytes', 0)} bytes · checksum `{str(ver.get('checksum', {}).get('value', ''))[:12]}…`"
        )

    st.divider()
    rollback_to = st.number_input("Rollback to version", min_value=1, max_value=max(1, obj.get("current_version", 1)), value=1)
    if st.button("Rollback", type="primary"):
        try:
            with_auto_refresh(lambda t: storage.rollback(t, obj["object_id"], version_number=int(rollback_to)))
            st.success(f"Rolled back to v{rollback_to}")
            st.rerun()
        except Exception as exc:
            st.error(friendly_api_error(exc))
