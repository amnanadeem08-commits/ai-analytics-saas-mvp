from __future__ import annotations

"""Spacing and radius tokens — replace ad-hoc padding/margins."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SpacingTokens:
    xxs: str = "0.25rem"  # 4
    xs: str = "0.5rem"  # 8
    sm: str = "0.75rem"  # 12
    md: str = "1rem"  # 16
    lg: str = "1.5rem"  # 24
    xl: str = "2rem"  # 32
    xxl: str = "3rem"  # 48
    section: str = "1.25rem"
    page_gutter: str = "0.5rem"


@dataclass(frozen=True)
class RadiusTokens:
    sm: str = "6px"
    md: str = "10px"
    lg: str = "14px"
    pill: str = "999px"


SPACING = SpacingTokens()
RADIUS = RadiusTokens()


def css_spacing_vars(
    spacing: SpacingTokens | None = None,
    radius: RadiusTokens | None = None,
) -> str:
    s = spacing or SPACING
    r = radius or RADIUS
    return f"""
    --ds-space-xxs: {s.xxs};
    --ds-space-xs: {s.xs};
    --ds-space-sm: {s.sm};
    --ds-space-md: {s.md};
    --ds-space-lg: {s.lg};
    --ds-space-xl: {s.xl};
    --ds-space-xxl: {s.xxl};
    --ds-space-section: {s.section};
    --ds-radius-sm: {r.sm};
    --ds-radius-md: {r.md};
    --ds-radius-lg: {r.lg};
    --ds-radius-pill: {r.pill};
    --theme-radius: {r.md};
    """
