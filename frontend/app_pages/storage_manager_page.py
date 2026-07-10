from __future__ import annotations

"""Storage Manager page (Sprint 8.4) — upload/list via `/api/v1/storage` only."""

import streamlit as st

from frontend.api.base import friendly_api_error
from frontend.api.storage_client import StorageClient
from frontend.utils.auth_state import get_access_token, is_authenticated, with_auto_refresh
from frontend.utils.session_state import navigate_to
from frontend.utils.workspace_api import get_api_client


def _client() -> StorageClient:
    return StorageClient(get_api_client())


def _error(exc: Exception) -> None:
    st.error(friendly_api_error(exc))


def render_storage_manager(client=None) -> None:
    st.header("Storage Manager")
    st.caption("Upload and manage artifacts through the FastAPI `/api/v1/storage` gateway.")

    if not is_authenticated():
        st.warning("Please sign in to manage storage.")
        if st.button("Go to Login", key="storage_login"):
            navigate_to("Login")
            st.rerun()
        return

    storage = _client()

    st.subheader("Upload artifact")
    with st.form("storage_upload_form"):
        uploaded = st.file_uploader("Choose a file", key="storage_upload_file")
        artifact_type = st.selectbox(
            "Artifact type",
            [
                "dataset",
                "knowledge_document",
                "report",
                "evaluation_export",
                "workflow_artifact",
                "temporary_upload",
                "ai_export",
            ],
        )
        allow_duplicate = st.checkbox("Allow duplicate content", value=True)
        submitted = st.form_submit_button("Upload", type="primary")

    if submitted and uploaded is not None:
        try:
            result = with_auto_refresh(
                lambda t: storage.upload(
                    t,
                    filename=uploaded.name,
                    content=uploaded.getvalue(),
                    content_type=uploaded.type or "application/octet-stream",
                    artifact_type=artifact_type,
                    allow_duplicate=allow_duplicate,
                )
            )
            obj = result.get("object", {})
            st.success(f"Uploaded `{obj.get('name')}` — object `{obj.get('object_id')}`")
        except Exception as exc:
            _error(exc)

    st.divider()
    st.subheader("Stored objects")
    try:
        listing = with_auto_refresh(lambda t: storage.list_files(t, mine=True))
        objects = listing.get("objects") or []
        if not objects:
            st.info("No storage objects found.")
            return
        for obj in objects:
            cols = st.columns([3, 2, 2, 1, 1, 1])
            cols[0].write(f"**{obj.get('name')}**")
            cols[1].caption(obj.get("artifact_type"))
            cols[2].caption(f"v{obj.get('current_version')} · {obj.get('status')}")
            oid = obj.get("object_id")
            if cols[3].button("Archive", key=f"arch_{oid}"):
                try:
                    with_auto_refresh(lambda t: storage.archive(t, oid))
                    st.rerun()
                except Exception as exc:
                    _error(exc)
            if cols[4].button("Restore", key=f"rest_{oid}"):
                try:
                    with_auto_refresh(lambda t: storage.restore(t, oid))
                    st.rerun()
                except Exception as exc:
                    _error(exc)
            if cols[5].button("Delete", key=f"del_{oid}"):
                try:
                    with_auto_refresh(lambda t: storage.delete(t, oid))
                    st.rerun()
                except Exception as exc:
                    _error(exc)
    except Exception as exc:
        _error(exc)
