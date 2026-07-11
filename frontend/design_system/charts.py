from __future__ import annotations

"""Chart theming — accessible palette, consistent fonts/padding/legends."""

from typing import Any  # noqa: F401 — reserved for future chart helpers

import plotly.graph_objects as go
import streamlit as st

from frontend.design_system.colors import CHART_PALETTE, COLORS
from frontend.design_system.typography import TYPOGRAPHY


def chart_palette(n: int | None = None) -> list[str]:
    colors = list(CHART_PALETTE)
    if n is None:
        return colors
    if n <= len(colors):
        return colors[:n]
    # Cycle if more series than palette entries
    out: list[str] = []
    while len(out) < n:
        out.extend(colors)
    return out[:n]


def apply_chart_layout(fig: go.Figure, *, title: str | None = None) -> go.Figure:
    """Power BI–style readability: clear legend, padding, accessible fonts."""
    existing = None
    if fig.layout.title and fig.layout.title.text:
        existing = fig.layout.title.text
    resolved_title = title if title is not None else existing
    fig.update_layout(
        title=dict(
            text=resolved_title,
            font=dict(family=TYPOGRAPHY.font_sans, size=16, color=COLORS.text),
        ),
        font=dict(family=TYPOGRAPHY.font_sans, size=12, color=COLORS.text),
        paper_bgcolor=COLORS.surface,
        plot_bgcolor=COLORS.background,
        margin=dict(l=48, r=24, t=56 if resolved_title else 40, b=48),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=11, color=COLORS.muted),
            bgcolor="rgba(255,255,255,0.85)",
        ),
        colorway=list(CHART_PALETTE),
        hoverlabel=dict(font=dict(family=TYPOGRAPHY.font_sans, size=12)),
    )
    fig.update_xaxes(
        showgrid=True,
        gridcolor=COLORS.border,
        zeroline=False,
        title_font=dict(size=12, color=COLORS.muted),
        tickfont=dict(size=11, color=COLORS.muted),
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor=COLORS.border,
        zeroline=False,
        title_font=dict(size=12, color=COLORS.muted),
        tickfont=dict(size=11, color=COLORS.muted),
    )
    return fig


def render_chart(fig: go.Figure, *, title: str | None = None, key: str | None = None) -> None:
    apply_chart_layout(fig, title=title)
    st.plotly_chart(fig, use_container_width=True, key=key)


def ensure_session_palette() -> list[str]:
    """Seed session chart_palette from design system if empty."""
    existing = st.session_state.get("chart_palette")
    if existing:
        return list(existing)
    palette = list(CHART_PALETTE)
    st.session_state["chart_palette"] = palette
    return palette
