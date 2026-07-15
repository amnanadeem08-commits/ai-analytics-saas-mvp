from __future__ import annotations

"""Khaldun AI DataBot — design system color tokens (Sprint 8.9).

Inspired by Power BI workflow clarity and Fluent consistency patterns.
Does not copy Microsoft Fluent visual branding.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ColorTokens:
    primary: str = "#174A7C"
    primary_hover: str = "#123A63"
    primary_muted: str = "#E8F1F8"
    secondary: str = "#243B53"
    accent: str = "#B88322"
    success: str = "#15803D"
    warning: str = "#B45309"
    danger: str = "#B91C1C"
    info: str = "#0369A1"
    background: str = "#F5F7FA"
    surface: str = "#FFFFFF"
    surface_raised: str = "#FFFFFF"
    border: str = "#CBD5E1"
    muted: str = "#64748B"
    text: str = "#0F172A"
    text_inverse: str = "#FFFFFF"
    focus_ring: str = "#174A7C"


COLORS = ColorTokens()

# Semantic aliases for status chips / alerts
STATUS_COLORS: dict[str, str] = {
    "queued": COLORS.muted,
    "pending": COLORS.muted,
    "running": COLORS.info,
    "in_progress": COLORS.info,
    "completed": COLORS.success,
    "success": COLORS.success,
    "failed": COLORS.danger,
    "error": COLORS.danger,
    "cancelled": COLORS.warning,
    "canceled": COLORS.warning,
    "warning": COLORS.warning,
    "archived": COLORS.secondary,
    "ready": COLORS.success,
    "info": COLORS.info,
}

# Accessible chart series (colorblind-friendly order; high contrast on light bg)
CHART_PALETTE: tuple[str, ...] = (
    "#174A7C",  # primary navy
    "#B88322",  # accent gold
    "#15803D",  # green
    "#B91C1C",  # red
    "#0369A1",  # cyan-blue
    "#7C3AED",  # violet (categorical only)
    "#0F766E",  # teal
    "#C2410C",  # orange
)


def css_color_vars(colors: ColorTokens | None = None) -> str:
    c = colors or COLORS
    return f"""
    --ds-primary: {c.primary};
    --ds-primary-hover: {c.primary_hover};
    --ds-primary-muted: {c.primary_muted};
    --ds-secondary: {c.secondary};
    --ds-accent: {c.accent};
    --ds-success: {c.success};
    --ds-warning: {c.warning};
    --ds-danger: {c.danger};
    --ds-info: {c.info};
    --ds-bg: {c.background};
    --ds-surface: {c.surface};
    --ds-border: {c.border};
    --ds-muted: {c.muted};
    --ds-text: {c.text};
    --ds-text-inverse: {c.text_inverse};
    --ds-focus: {c.focus_ring};
    --brand-primary: {c.primary};
    --brand-secondary: {c.secondary};
    --brand-accent: {c.accent};
    --text-color: {c.text};
    --text-muted: {c.muted};
    --surface-border: {c.border};
    --ui-surface: {c.surface};
    """
