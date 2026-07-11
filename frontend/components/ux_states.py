from __future__ import annotations

"""Shared Streamlit UX primitives (Sprint 8.8) — backed by design system tokens (8.9).

Frontend-only helpers. No backend imports.
"""

from typing import Callable

import streamlit as st

from frontend.design_system.alerts import badge_html, notify_success
from frontend.design_system.colors import STATUS_COLORS
from frontend.design_system.layout import page_header, section_header as ds_section_header
from frontend.design_system.navigation import (
    DEFAULT_WORKFLOW_STEPS,
    workflow_stepper as ds_workflow_stepper,
)
from frontend.design_system.theme import inject_design_system_css

_STATUS_STYLES: dict[str, tuple[str, str]] = {
    key: (color, key.replace("_", " ").title()) for key, color in STATUS_COLORS.items()
}


def inject_ux_css() -> None:
    """Ensure design-system CSS is present; keep legacy class aliases."""
    inject_design_system_css()
    if st.session_state.get("_ux_css_injected"):
        return
    st.markdown(
        """
        <style>
        .ux-empty {
            border: 1px dashed color-mix(in srgb, var(--ds-primary) 35%, var(--ds-border));
            border-radius: var(--ds-radius-lg);
            padding: var(--ds-space-lg) var(--ds-space-md);
            background: color-mix(in srgb, var(--ds-primary) 5%, transparent);
            margin: var(--ds-space-sm) 0 var(--ds-space-md);
        }
        .ux-empty h3 { margin: 0 0 0.35rem; font-size: var(--ds-subheading-size); }
        .ux-empty p { margin: 0; color: var(--ds-muted); font-size: var(--ds-body-size); }
        .ux-section-title { font-size: var(--ds-subheading-size); font-weight: 800; margin: var(--ds-space-section) 0 var(--ds-space-xxs); color: var(--ds-text); }
        .ux-section-caption { color: var(--ds-muted); font-size: var(--ds-caption-size); margin: 0 0 var(--ds-space-sm); }
        .ux-badge { display: inline-block; padding: 0.15rem 0.55rem; border-radius: var(--ds-radius-pill); font-size: 0.75rem; font-weight: 700; color: #fff; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.session_state["_ux_css_injected"] = True


def section_header(title: str, caption: str | None = None) -> None:
    inject_ux_css()
    ds_section_header(title, caption)


def empty_state(
    title: str,
    body: str,
    *,
    primary_label: str | None = None,
    primary_page: str | None = None,
    key: str = "ux_empty_cta",
) -> bool:
    """Render guidance when there is nothing to show. Returns True if CTA clicked."""
    inject_ux_css()
    st.markdown(
        f'<div class="ux-empty"><h3>{title}</h3><p>{body}</p></div>',
        unsafe_allow_html=True,
    )
    if primary_label and primary_page:
        if st.button(primary_label, key=key, type="primary"):
            from frontend.utils.session_state import navigate_to

            navigate_to(primary_page)
            st.rerun()
            return True
    return False


def loading_block(message: str = "Working on it…") -> None:
    st.info(f"⏳ {message}")


def error_panel(
    message: str,
    *,
    suggestion: str | None = None,
    retry_key: str | None = None,
    on_retry: Callable[[], None] | None = None,
) -> None:
    st.error(message)
    if suggestion:
        st.caption(f"Tip: {suggestion}")
    cols = st.columns([1, 1, 4])
    with cols[0]:
        if st.button("Go to Home", key=f"{retry_key or 'err'}_home"):
            from frontend.utils.session_state import navigate_to

            navigate_to("Home")
            st.rerun()
    with cols[1]:
        if retry_key and st.button("Retry", key=retry_key, type="primary"):
            if on_retry:
                on_retry()
            st.rerun()


def success_banner(message: str) -> None:
    notify_success(message)


def status_badge(label: str | None, kind: str | None = None) -> str:
    """Return HTML badge. Also accepts raw status strings as kind."""
    inject_ux_css()
    raw = (kind or label or "pending").strip().lower().replace(" ", "_")
    pretty = (label or kind or "Unknown")
    if not label and raw in _STATUS_STYLES:
        pretty = _STATUS_STYLES[raw][1]
    return badge_html(str(pretty), kind=raw)


def render_status_badge(label: str | None, kind: str | None = None) -> None:
    st.markdown(status_badge(label, kind), unsafe_allow_html=True)


def workflow_stepper(
    steps: tuple[str, ...] | list[str] | None = None,
    active_index: int = 0,
) -> None:
    inject_ux_css()
    ds_workflow_stepper(steps, active_index)


def page_intro(title: str, caption: str, *, workflow_index: int | None = None) -> None:
    """Standard page title + optional workflow context."""
    inject_ux_css()
    page_header(title, caption)
    if workflow_index is not None:
        workflow_stepper(active_index=workflow_index)
