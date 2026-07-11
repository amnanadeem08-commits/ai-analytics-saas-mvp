from __future__ import annotations

"""Card primitives — section, KPI, metric."""

import html

import streamlit as st

from frontend.design_system.theme import inject_design_system_css


def _esc(value: object) -> str:
    return html.escape(str(value if value is not None else ""))


def section_card(title: str, body: str | None = None, *, caption: str | None = None) -> None:
    inject_design_system_css()
    cap = f'<div class="ds-caption">{_esc(caption)}</div>' if caption else ""
    content = f'<div class="ds-body">{_esc(body)}</div>' if body else ""
    st.markdown(
        f'<div class="ds-card ds-card-section"><div class="ds-subheading">{_esc(title)}</div>{cap}{content}</div>',
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value: object, *, hint: str | None = None) -> None:
    inject_design_system_css()
    hint_html = f'<div class="ds-caption">{_esc(hint)}</div>' if hint else ""
    st.markdown(
        f"""
        <div class="ds-kpi">
          <div class="ds-kpi-label">{_esc(label)}</div>
          <div class="ds-metric-value">{_esc(value)}</div>
          {hint_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_cards(items: list[tuple[str, object, str | None]]) -> None:
    """items: (label, value, help_text?)."""
    if not items:
        return
    cols = st.columns(len(items))
    for col, (label, value, help_text) in zip(cols, items):
        with col:
            col.metric(label, value, help=help_text)


def card_container(title: str | None = None) -> None:
    inject_design_system_css()
    if title:
        st.markdown(f'<div class="ds-card"><div class="ds-subheading">{_esc(title)}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="ds-card">', unsafe_allow_html=True)
