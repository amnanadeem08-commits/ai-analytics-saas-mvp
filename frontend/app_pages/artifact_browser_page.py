from __future__ import annotations

"""Artifact Browser page (Sprint 8.4)."""

import streamlit as st

from frontend.api.base import friendly_api_error
from frontend.api.storage_client import StorageClient
from frontend.utils.auth_state import is_authenticated, with_auto_refresh
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
    from frontend.components.ux_states import empty_state, page_intro, render_status_badge, section_header

    page_intro(
        "Artifact Browser",
        "Browse stored artifacts by type and inspect metadata.",
    )

    if not is_authenticated():
        empty_state(
            "Sign in to browse artifacts",
            "Artifact browsing requires an authenticated session.",
            primary_label="Go to Login",
            primary_page="Login",
            key="art_login",
        )
        return

    storage = _client()
    section_header("Filters", "Narrow by type and status")
    f1, f2 = st.columns(2)
    with f1:
        artifact_type = st.selectbox("Filter by artifact type", ["(all)"] + ARTIFACT_TYPES)
    with f2:
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
    if not objects:
        empty_state(
            "No matching artifacts",
            "Adjust filters or upload an artifact from Storage Manager.",
            primary_label="Open Storage Manager",
            primary_page="Storage Manager",
            key="art_empty",
        )
        return
    for obj in objects:
        with st.expander(f"{obj.get('name')} — {obj.get('artifact_type')}"):
            render_status_badge(str(obj.get("status") or "active"), obj.get("status"))
            st.json(obj)
            oid = obj.get("object_id")
            if st.button("Verify checksum", key=f"verify_{oid}"):
                try:
                    result = with_auto_refresh(lambda t: storage.verify(t, oid))
                    st.success(f"Checksum valid: {result.get('valid')}")
                except Exception as exc:
                    st.error(friendly_api_error(exc))
