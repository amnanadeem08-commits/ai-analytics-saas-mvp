from __future__ import annotations

"""Active Dataset context — Power BI–style one dataset, many analyses.

Upload once (Upload / Dataset Manager). All analysis pages consume
``active_dataset_id`` from session. Switch only via the sidebar switcher.
"""

from typing import Any

import streamlit as st

from frontend.utils.session_state import navigate_to, track_recent_dataset


def get_active_dataset_id() -> str | None:
    return st.session_state.get("active_dataset_id") or st.session_state.get("selected_dataset_id")


def get_active_dataset_name() -> str:
    dataset_id = get_active_dataset_id()
    if not dataset_id:
        return "No dataset selected"
    local = st.session_state.get("uploaded_datasets", {}).get(dataset_id, {})
    if local.get("original_filename"):
        return str(local["original_filename"])
    for item in st.session_state.get("recent_datasets", []):
        if item.get("dataset_id") == dataset_id and item.get("filename"):
            return str(item["filename"])
    return str(dataset_id)


def set_active_dataset(dataset_id: str, filename: str | None = None) -> None:
    if not dataset_id:
        return
    st.session_state["active_dataset_id"] = dataset_id
    st.session_state["selected_dataset_id"] = dataset_id
    if filename:
        track_recent_dataset(dataset_id, filename)
    else:
        track_recent_dataset(dataset_id, get_active_dataset_name())


def clear_active_dataset() -> None:
    st.session_state["active_dataset_id"] = None
    st.session_state["selected_dataset_id"] = None


def resolve_active_dataset(client=None) -> str | None:
    """Return active dataset id without showing a page-level picker."""
    from frontend.utils.local_helpers import get_dataset_options

    active = get_active_dataset_id()
    if active:
        return active

    # Auto-pick the only available dataset (local or API) so first run is smoother
    try:
        options = get_dataset_options(client) if client is not None else []
    except Exception:
        options = []
    if len(options) == 1:
        item = options[0]
        did = item.get("dataset_id")
        if did:
            set_active_dataset(did, item.get("original_filename"))
            return did

    local_map = st.session_state.get("local_dataframes", {})
    if isinstance(local_map, dict) and len(local_map) == 1:
        did = next(iter(local_map.keys()))
        set_active_dataset(did)
        return did
    return None


def require_active_dataset(client=None) -> str | None:
    """Resolve active dataset or show empty-state CTA. No selectbox."""
    dataset_id = resolve_active_dataset(client)
    if dataset_id:
        return dataset_id
    from frontend.components.ux_states import empty_state

    empty_state(
        "No active dataset",
        "Upload a CSV or Excel file once, then every page will use it — like Power BI.",
        primary_label="Upload data",
        primary_page="Upload",
        key="require_active_dataset_cta",
    )
    return None


def render_active_dataset_banner(*, show_change_hint: bool = True) -> None:
    """Top-of-page current dataset strip."""
    dataset_id = get_active_dataset_id()
    name = get_active_dataset_name()
    if not dataset_id:
        st.info("No active dataset — upload once from **Upload** or **Dataset Manager**, or pick one in the sidebar.")
        return
    cols = st.columns([4, 1] if show_change_hint else [1])
    with cols[0]:
        st.caption(f"Active dataset · **{name}**")
        st.caption(f"`{dataset_id}`")
    if show_change_hint and len(cols) > 1:
        with cols[1]:
            st.caption("Change in sidebar")


def render_sidebar_dataset_switcher(client) -> None:
    """Power BI–style dataset switcher in the sidebar."""
    from frontend.utils.local_helpers import get_dataset_options

    st.sidebar.markdown("#### Active dataset")
    try:
        options = get_dataset_options(client)
    except Exception:
        options = []

    # Merge recent / local labels
    labels: dict[str, str] = {}
    for item in options:
        did = item.get("dataset_id")
        if not did:
            continue
        name = item.get("original_filename") or did
        labels[f"{name}"] = did
        # Keep unique keys if duplicate names
        if list(labels.values()).count(did) > 1:
            labels[f"{name} ({did[:8]})"] = did

    for item in st.session_state.get("recent_datasets", []):
        did = item.get("dataset_id")
        if did and did not in labels.values():
            labels[item.get("filename") or did] = did

    if not labels:
        st.sidebar.caption("No datasets yet.")
        if st.sidebar.button("Upload data", key="sidebar_upload_cta", use_container_width=True, type="primary"):
            navigate_to("Upload")
            st.rerun()
        return

    active = get_active_dataset_id()
    label_list = list(labels.keys())
    index = 0
    for i, lab in enumerate(label_list):
        if labels[lab] == active:
            index = i
            break

    choice = st.sidebar.selectbox(
        "Dataset",
        options=label_list,
        index=index,
        key="sidebar_active_dataset_switcher",
        help="One active dataset for the whole app — change it here, not on every page.",
    )
    chosen_id = labels[choice]
    if chosen_id != active:
        set_active_dataset(chosen_id, choice)
        st.rerun()

    st.sidebar.caption(f"ID: `{chosen_id}`")
    c1, c2 = st.sidebar.columns(2)
    if c1.button("Upload", key="sidebar_goto_upload", use_container_width=True):
        navigate_to("Upload")
        st.rerun()
    if c2.button("Manage", key="sidebar_goto_manager", use_container_width=True):
        navigate_to("Dataset Manager")
        st.rerun()


def active_dataset_summary_metrics(client=None) -> dict[str, Any]:
    """Best-effort row/column summary for banner enrichment."""
    dataset_id = get_active_dataset_id()
    if not dataset_id:
        return {}
    return {"name": get_active_dataset_name(), "dataset_id": dataset_id}
