from __future__ import annotations

"""Layout primitives — page chrome, stacks, section headers."""

import html

import streamlit as st

from frontend.design_system.theme import inject_design_system_css
from frontend.design_system.typography import TYPOGRAPHY


def _esc(value: object) -> str:
    return html.escape(str(value if value is not None else ""))


def page_header(title: str, caption: str | None = None) -> None:
    inject_design_system_css()
    st.markdown(f'<div class="ds-heading">{_esc(title)}</div>', unsafe_allow_html=True)
    if caption:
        st.markdown(f'<div class="ds-caption">{_esc(caption)}</div>', unsafe_allow_html=True)


def display_title(text: str) -> None:
    inject_design_system_css()
    st.markdown(f'<div class="ds-display">{_esc(text)}</div>', unsafe_allow_html=True)


def section_header(title: str, caption: str | None = None) -> None:
    inject_design_system_css()
    st.markdown(f'<div class="ds-subheading">{_esc(title)}</div>', unsafe_allow_html=True)
    if caption:
        st.markdown(f'<div class="ds-caption">{_esc(caption)}</div>', unsafe_allow_html=True)


def divider() -> None:
    st.divider()


def columns_responsive(n: int = 2):
    return st.columns(n)


def stack_start() -> None:
    inject_design_system_css()
    st.markdown('<div class="ds-stack-md">', unsafe_allow_html=True)


def spacer(size: str = "md") -> None:
    """Visual spacer using design tokens via empty markdown."""
    mapping = {"xs": "0.5rem", "sm": "0.75rem", "md": "1rem", "lg": "1.5rem", "xl": "2rem"}
    h = mapping.get(size, "1rem")
    st.markdown(f'<div style="height:{h}"></div>', unsafe_allow_html=True)


# re-export typography hint for docs
FONT_SANS = TYPOGRAPHY.font_sans
