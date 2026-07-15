from __future__ import annotations

"""Standardized Streamlit buttons."""

from typing import Literal

import streamlit as st

ButtonKind = Literal["primary", "secondary", "danger", "success"]


def ds_button(
    label: str,
    *,
    kind: ButtonKind = "primary",
    key: str | None = None,
    use_container_width: bool = False,
    disabled: bool = False,
    help: str | None = None,
) -> bool:
    """Render a semantic button. Danger/success use Streamlit type + caption hint."""
    st_type = "primary" if kind in {"primary", "danger", "success"} else "secondary"
    clicked = st.button(
        label,
        key=key,
        type=st_type,
        use_container_width=use_container_width,
        disabled=disabled,
        help=help or (f"{kind.title()} action" if kind != "secondary" else None),
    )
    if kind == "danger":
        st.caption("Destructive action — confirm before continuing.")
    return clicked


def primary_button(label: str, **kwargs) -> bool:
    return ds_button(label, kind="primary", **kwargs)


def secondary_button(label: str, **kwargs) -> bool:
    return ds_button(label, kind="secondary", **kwargs)


def danger_button(label: str, **kwargs) -> bool:
    return ds_button(label, kind="danger", **kwargs)


def success_button(label: str, **kwargs) -> bool:
    return ds_button(label, kind="success", **kwargs)
