from __future__ import annotations

"""Dataset Manager — upload/preview via FastAPI HTTP only."""

import pandas as pd
import streamlit as st

from frontend.components.active_dataset import set_active_dataset
from frontend.utils.workspace_api import get_workspace_clients, show_api_error


def render_dataset_manager(client=None) -> None:
    from frontend.components.ux_states import empty_state, page_intro, render_status_badge, section_header

    page_intro(
        "Dataset Manager",
        "Upload and activate datasets through the API — like adding a data source in Power BI.",
        workflow_index=0,
    )

    clients = get_workspace_clients()
    dataset_api = clients["dataset"]

    section_header("Upload", "CSV or Excel files are validated on the server.")
    uploaded = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx", "xls"], help="Required for new datasets.")
    if uploaded is not None and st.button("Upload to API", type="primary"):
        with st.spinner("Uploading via `/upload`…"):
            try:
                content_type = uploaded.type or "application/octet-stream"
                result = dataset_api.upload(uploaded.name, uploaded.getvalue(), content_type)
                dataset_id = result.get("dataset_id") or result.get("id")
                if dataset_id:
                    set_active_dataset(dataset_id, uploaded.name)
                    st.success(f"Uploaded and activated `{dataset_id}`")
                else:
                    st.warning("Upload completed but no dataset_id was returned.")
                    st.json(result)
            except Exception as exc:
                show_api_error(exc)

    st.divider()
    section_header("Available datasets", "Select a dataset to preview status and rows.")
    try:
        datasets = dataset_api.list_datasets()
    except Exception as exc:
        show_api_error(exc)
        datasets = []

    if not datasets:
        empty_state(
            "No datasets yet",
            "Upload a CSV or Excel file above to create your first dataset.",
            key="dm_empty",
        )
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
        set_active_dataset(dataset_id, (selected or {}).get("filename") or dataset_id)
        st.success(f"Active dataset set to `{dataset_id}`")

    tabs = st.tabs(["Overview", "Preview", "Status"])
    with tabs[0]:
        try:
            overview = dataset_api.overview(dataset_id)
            m1, m2, m3 = st.columns(3)
            m1.metric("Rows", overview.get("row_count", "—"))
            m2.metric("Columns", overview.get("column_count", "—"))
            m3.metric("Duplicates", overview.get("duplicate_rows", "—"))
            with st.expander("Raw overview", expanded=False):
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
                empty_state("No preview rows", "This dataset returned an empty preview payload.")
                with st.expander("Raw preview", expanded=False):
                    st.json(preview)
        except Exception as exc:
            show_api_error(exc)
    with tabs[2]:
        try:
            status = dataset_api.status(dataset_id)
            kind = str(status.get("status") or status.get("state") or "ready")
            render_status_badge(kind.title(), kind)
            with st.expander("Raw status", expanded=False):
                st.json(status)
        except Exception as exc:
            show_api_error(exc)
