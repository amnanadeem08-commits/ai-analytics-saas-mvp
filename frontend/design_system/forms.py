from __future__ import annotations

"""Form helpers — consistent labels, search, progress."""

import streamlit as st

from frontend.design_system.theme import inject_design_system_css


def search_box(
    label: str = "Search",
    *,
    key: str = "ds_search",
    placeholder: str = "Search…",
    value: str = "",
) -> str:
    inject_design_system_css()
    return st.text_input(
        label,
        value=value,
        key=key,
        placeholder=placeholder,
        help="Type to filter results",
    )


def labeled_text_input(label: str, *, key: str, value: str = "", help: str | None = None) -> str:
    return st.text_input(label, value=value, key=key, help=help)


def labeled_select(label: str, options: list[str], *, key: str, index: int = 0) -> str:
    return st.selectbox(label, options=options, index=index, key=key)


def progress_indicator(percent: float, *, message: str = "") -> None:
    pct = max(0.0, min(100.0, float(percent)))
    st.progress(pct / 100.0)
    if message:
        st.caption(message)
    else:
        st.caption(f"{pct:.0f}% complete")


def tooltip_caption(text: str) -> None:
    """Streamlit has limited native tooltips; captions provide accessible hints."""
    st.caption(text)
