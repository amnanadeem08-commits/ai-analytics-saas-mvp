from __future__ import annotations

"""Dataset Manager — upload/preview via FastAPI HTTP only."""

import pandas as pd
import streamlit as st

from frontend.utils.session_state import track_recent_dataset
from frontend.utils.workspace_api import get_workspace_clients, show_api_error


def render_dataset_manager(client=None) -> None:
    st.header("Dataset Manager")
    st.caption("Upload and preview datasets through the FastAPI upload/dataset endpoints.")

    clients = get_workspace_clients()
    dataset_api = clients["dataset"]

    uploaded = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx", "xls"])
    if uploaded is not None and st.button("Upload to API", type="primary"):
        with st.spinner("Uploading via `/upload`…"):
            try:
                content_type = uploaded.type or "application/octet-stream"
                result = dataset_api.upload(uploaded.name, uploaded.getvalue(), content_type)
                dataset_id = result.get("dataset_id") or result.get("id")
                if dataset_id:
                    st.session_state["active_dataset_id"] = dataset_id
                    st.session_state["selected_dataset_id"] = dataset_id
                    track_recent_dataset(dataset_id, uploaded.name)
                    st.success(f"Uploaded dataset `{dataset_id}`")
                else:
                    st.warning("Upload completed but no dataset_id was returned.")
                    st.json(result)
            except Exception as exc:
                show_api_error(exc)

    st.divider()
    st.subheader("Available datasets")
    try:
        datasets = dataset_api.list_datasets()
    except Exception as exc:
        show_api_error(exc)
        datasets = []

    if not datasets:
        st.info("No datasets found. Upload a file to get started.")
        return

    labels = []
    for item in datasets:
        did = item.get("dataset_id") or item.get("id") or ""
        name = item.get("filename") or item.get("name") or did
        labels.append(f"{name} ({did})")
    choice = st.selectbox("Select dataset", options=labels)
    selected = datasets[labels.index(choice)] if choice else None
    dataset_id = (selected or {}).get("dataset_id") or (selected or {}).get("id")
    if not dataset_id:
        return

    if st.button("Set as active dataset", use_container_width=True):
        st.session_state["active_dataset_id"] = dataset_id
        st.session_state["selected_dataset_id"] = dataset_id
        track_recent_dataset(dataset_id, (selected or {}).get("filename") or dataset_id)
        st.success(f"Active dataset set to `{dataset_id}`")

    tabs = st.tabs(["Overview", "Preview", "Status"])
    with tabs[0]:
        try:
            overview = dataset_api.overview(dataset_id)
            st.json(overview)
        except Exception as exc:
            show_api_error(exc)
    with tabs[1]:
        try:
            preview = dataset_api.preview(dataset_id, limit=25)
            rows = preview.get("preview") or preview.get("rows") or preview.get("data") or []
            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True)
            else:
                st.json(preview)
        except Exception as exc:
            show_api_error(exc)
    with tabs[2]:
        try:
            st.json(dataset_api.status(dataset_id))
        except Exception as exc:
            show_api_error(exc)
