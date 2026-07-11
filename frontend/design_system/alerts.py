from __future__ import annotations

"""Alerts, notifications, badges, tags, status chips."""

import html

import streamlit as st

from frontend.design_system.colors import STATUS_COLORS
from frontend.design_system.theme import inject_design_system_css


def _esc(value: object) -> str:
    return html.escape(str(value if value is not None else ""))


def alert(message: str, *, kind: str = "info", title: str | None = None) -> None:
    inject_design_system_css()
    kind = kind if kind in {"success", "warning", "danger", "info"} else "info"
    head = f"<strong>{_esc(title)}</strong><br/>" if title else ""
    st.markdown(
        f'<div class="ds-alert ds-alert-{kind}">{head}{_esc(message)}</div>',
        unsafe_allow_html=True,
    )


def notify_success(message: str) -> None:
    st.success(message)


def notify_error(message: str) -> None:
    st.error(message)


def notify_warning(message: str) -> None:
    st.warning(message)


def notify_info(message: str) -> None:
    st.info(message)


def badge_html(label: str, *, color: str | None = None, kind: str | None = None) -> str:
    inject_design_system_css()
    bg = color or STATUS_COLORS.get((kind or label or "").lower().replace(" ", "_"), "#64748B")
    return f'<span class="ds-badge" style="background:{bg};">{_esc(label)}</span>'


def render_badge(label: str, *, kind: str | None = None, color: str | None = None) -> None:
    st.markdown(badge_html(label, color=color, kind=kind), unsafe_allow_html=True)


def tag(label: str) -> None:
    inject_design_system_css()
    st.markdown(f'<span class="ds-tag">{_esc(label)}</span>', unsafe_allow_html=True)


def status_chip(status: str) -> None:
    raw = (status or "pending").strip().lower().replace(" ", "_")
    pretty = (status or "Unknown").replace("_", " ").title()
    render_badge(pretty, kind=raw)
