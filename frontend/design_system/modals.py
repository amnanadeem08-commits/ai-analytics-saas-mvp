from __future__ import annotations

"""Dialog / modal patterns using Streamlit expanders and experimental dialogs when available."""

import streamlit as st

from frontend.design_system.buttons import danger_button, primary_button, secondary_button


def confirm_dialog(
    title: str,
    body: str,
    *,
    confirm_label: str = "Confirm",
    cancel_label: str = "Cancel",
    danger: bool = False,
    key: str = "ds_confirm",
) -> bool | None:
    """
    Simple confirmation UI.
    Returns True if confirmed, False if cancelled, None if neither clicked yet.
    """
    with st.expander(title, expanded=True):
        st.write(body)
        c1, c2 = st.columns(2)
        confirmed = False
        cancelled = False
        with c1:
            if danger:
                confirmed = danger_button(confirm_label, key=f"{key}_ok")
            else:
                confirmed = primary_button(confirm_label, key=f"{key}_ok")
        with c2:
            cancelled = secondary_button(cancel_label, key=f"{key}_cancel")
        if confirmed:
            return True
        if cancelled:
            return False
    return None


def details_modal(title: str, content: object, *, expanded: bool = False) -> None:
    """Technical details / secondary content in an accordion-style expander."""
    with st.expander(title, expanded=expanded):
        if isinstance(content, (dict, list)):
            st.json(content)
        else:
            st.write(content)
