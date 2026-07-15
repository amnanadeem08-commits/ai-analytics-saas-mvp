from __future__ import annotations

"""Aggregated design tokens for Khaldun AI DataBot."""

from frontend.design_system.colors import CHART_PALETTE, COLORS, STATUS_COLORS, css_color_vars
from frontend.design_system.spacing import RADIUS, SPACING, css_spacing_vars
from frontend.design_system.typography import TYPOGRAPHY, css_typography_vars

__all__ = [
    "COLORS",
    "CHART_PALETTE",
    "STATUS_COLORS",
    "SPACING",
    "RADIUS",
    "TYPOGRAPHY",
    "css_root_vars",
    "token_reference",
]


def css_root_vars() -> str:
    return (
        css_color_vars()
        + css_typography_vars()
        + css_spacing_vars()
    )


def token_reference() -> dict:
    """Serializable token dump for docs / debugging."""
    return {
        "colors": COLORS.__dict__,
        "chart_palette": list(CHART_PALETTE),
        "status_colors": dict(STATUS_COLORS),
        "spacing": SPACING.__dict__,
        "radius": RADIUS.__dict__,
        "typography": {
            "font_sans": TYPOGRAPHY.font_sans,
            "font_mono": TYPOGRAPHY.font_mono,
            "display": TYPOGRAPHY.display.__dict__,
            "heading": TYPOGRAPHY.heading.__dict__,
            "subheading": TYPOGRAPHY.subheading.__dict__,
            "body": TYPOGRAPHY.body.__dict__,
            "caption": TYPOGRAPHY.caption.__dict__,
            "code": TYPOGRAPHY.code.__dict__,
            "metric": TYPOGRAPHY.metric.__dict__,
        },
    }
