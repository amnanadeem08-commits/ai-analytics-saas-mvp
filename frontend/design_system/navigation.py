from __future__ import annotations

"""Navigation helpers — tabs, accordions, workflow stepper, top bar caption."""

import html

import streamlit as st

from frontend.design_system.theme import inject_design_system_css

DEFAULT_WORKFLOW_STEPS: tuple[str, ...] = (
    "Upload",
    "Prepare",
    "Analyze",
    "Visualize",
    "Insights",
    "Export",
)


def _esc(value: object) -> str:
    return html.escape(str(value if value is not None else ""))


def tabs(labels: list[str]):
    """Thin wrapper for consistent tab usage."""
    return st.tabs(labels)


def accordion(title: str, *, expanded: bool = False):
    return st.expander(title, expanded=expanded)


def workflow_stepper(
    steps: tuple[str, ...] | list[str] | None = None,
    active_index: int = 0,
) -> None:
    """Horizontal analyst workflow indicator (Power BI–inspired path)."""
    inject_design_system_css()
    labels = list(steps or DEFAULT_WORKFLOW_STEPS)
    parts: list[str] = [
        '<div style="display:flex;flex-wrap:wrap;gap:0.35rem;align-items:center;margin:0.5rem 0 1rem;">'
    ]
    for i, name in enumerate(labels):
        if i > 0:
            parts.append('<span style="color:var(--ds-muted);font-weight:700;">→</span>')
        if i < active_index:
            style = (
                "padding:0.35rem 0.7rem;border-radius:999px;font-size:0.8rem;font-weight:700;"
                "background:color-mix(in srgb, var(--ds-success) 14%, transparent);"
                "border:1px solid var(--ds-success);color:var(--ds-success);"
            )
        elif i == active_index:
            style = (
                "padding:0.35rem 0.7rem;border-radius:999px;font-size:0.8rem;font-weight:700;"
                "background:color-mix(in srgb, var(--ds-primary) 18%, transparent);"
                "border:1px solid var(--ds-primary);color:var(--ds-primary);"
            )
        else:
            style = (
                "padding:0.35rem 0.7rem;border-radius:999px;font-size:0.8rem;font-weight:700;"
                "border:1px solid var(--ds-border);color:var(--ds-muted);background:transparent;"
            )
        parts.append(f'<span style="{style}">{i + 1}. {_esc(name)}</span>')
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def top_nav_caption(product: str = "Khaldun AI DataBot", context: str | None = None) -> None:
    inject_design_system_css()
    extra = f" · {_esc(context)}" if context else ""
    st.markdown(
        f'<div class="ds-caption" style="margin-bottom:0.25rem;">{_esc(product)}{extra}</div>',
        unsafe_allow_html=True,
    )


def sidebar_section_label(text: str) -> None:
    st.sidebar.caption(text)
