from __future__ import annotations

"""Artifact Browser page (Sprint 8.4)."""

import streamlit as st

from frontend.api.base import friendly_api_error
from frontend.api.storage_client import StorageClient
from frontend.utils.auth_state import is_authenticated, with_auto_refresh
from frontend.utils.session_state import navigate_to
from frontend.utils.workspace_api import get_api_client


ARTIFACT_TYPES = [
    "dataset",
    "knowledge_document",
    "report",
    "evaluation_export",
    "workflow_artifact",
    "temporary_upload",
    "ai_export",
]


def _client() -> StorageClient:
    return StorageClient(get_api_client())


def render_artifact_browser(client=None) -> None:
    st.header("Artifact Browser")
    st.caption("Browse stored artifacts by type and inspect metadata.")

    if not is_authenticated():
        st.warning("Please sign in to browse artifacts.")
        if st.button("Go to Login", key="art_login"):
            navigate_to("Login")
            st.rerun()
        return

    storage = _client()
    artifact_type = st.selectbox("Filter by artifact type", ["(all)"] + ARTIFACT_TYPES)
    status = st.selectbox("Filter by status", ["(all)", "active", "archived", "deleted"])

    params_type = None if artifact_type == "(all)" else artifact_type
    params_status = None if status == "(all)" else status

    try:
        listing = with_auto_refresh(
            lambda t: storage.list_files(t, artifact_type=params_type, status=params_status, mine=True)
        )
        objects = listing.get("objects") or []
    except Exception as exc:
        st.error(friendly_api_error(exc))
        return

    st.metric("Matching artifacts", len(objects))
    for obj in objects:
        with st.expander(f"{obj.get('name')} — {obj.get('artifact_type')}"):
            st.json(obj)
            oid = obj.get("object_id")
            if st.button("Verify checksum", key=f"verify_{oid}"):
                try:
                    result = with_auto_refresh(lambda t: storage.verify(t, oid))
                    st.success(f"Checksum valid: {result.get('valid')}")
                except Exception as exc:
                    st.error(friendly_api_error(exc))
