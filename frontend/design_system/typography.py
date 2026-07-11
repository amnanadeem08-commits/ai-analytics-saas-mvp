from __future__ import annotations

"""Typography scale for Khaldun AI DataBot design system."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TypeStyle:
    size: str
    weight: int
    line_height: str
    letter_spacing: str = "0"


@dataclass(frozen=True)
class TypographyScale:
    font_sans: str = (
        "'Segoe UI', 'Source Sans 3', 'Helvetica Neue', Arial, sans-serif"
    )
    font_mono: str = (
        "'Cascadia Code', 'Source Code Pro', Consolas, 'Courier New', monospace"
    )
    display: TypeStyle = TypeStyle("2rem", 800, "1.2", "-0.02em")
    heading: TypeStyle = TypeStyle("1.35rem", 800, "1.3", "-0.01em")
    subheading: TypeStyle = TypeStyle("1.1rem", 700, "1.35")
    body: TypeStyle = TypeStyle("0.95rem", 400, "1.5")
    caption: TypeStyle = TypeStyle("0.8rem", 500, "1.4")
    code: TypeStyle = TypeStyle("0.85rem", 500, "1.45")
    metric: TypeStyle = TypeStyle("1.5rem", 800, "1.2", "-0.01em")


TYPOGRAPHY = TypographyScale()


def css_typography_vars(scale: TypographyScale | None = None) -> str:
    t = scale or TYPOGRAPHY
    return f"""
    --ds-font-sans: {t.font_sans};
    --ds-font-mono: {t.font_mono};
    --ds-display-size: {t.display.size};
    --ds-heading-size: {t.heading.size};
    --ds-subheading-size: {t.subheading.size};
    --ds-body-size: {t.body.size};
    --ds-caption-size: {t.caption.size};
    --ds-metric-size: {t.metric.size};
    """
