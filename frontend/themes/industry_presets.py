from __future__ import annotations

from frontend.themes.theme_models import ThemeDefinition, ThemeSpacing, ThemeTypography
from frontend.themes.theme_registry import register_theme


def _theme(
    name: str,
    display_name: str,
    category: str,
    mode: str,
    primary: str,
    secondary: str,
    accent: str,
    success: str,
    warning: str,
    error: str,
    background: str,
    card: str,
    surface_alt: str,
    border: str,
    text: str,
    muted: str,
    palette: list[str],
    description: str,
    radius: str = "8px",
    shadow: str = "0 14px 34px rgba(15, 23, 42, 0.08)",
) -> ThemeDefinition:
    return ThemeDefinition(
        name=name,
        display_name=display_name,
        category=category,
        mode=mode,
        primary=primary,
        secondary=secondary,
        accent=accent,
        success=success,
        warning=warning,
        error=error,
        background=background,
        card_background=card,
        surface_alt=surface_alt,
        border=border,
        text=text,
        muted_text=muted,
        subtle_text=muted,
        typography=ThemeTypography(),
        spacing=ThemeSpacing(),
        radius=radius,
        shadow=shadow,
        icon_style="rounded",
        chart_palette=palette,
        description=description,
    )


PRESET_THEMES = [
    _theme("executive", "Executive", "Executive", "light", "#174A7C", "#243B53", "#B88322", "#047857", "#B7791F", "#B91C1C", "#F6F8FB", "#FFFFFF", "#EEF2F6", "#D9E1EA", "#172033", "#5F6B7A", ["#174A7C", "#1F8A89", "#B88322", "#64748B", "#047857", "#B91C1C"], "Boardroom-grade consulting presentation theme."),
    _theme("corporate", "Corporate", "Corporate", "light", "#1D4ED8", "#374151", "#0EA5E9", "#15803D", "#CA8A04", "#DC2626", "#F8FAFC", "#FFFFFF", "#F1F5F9", "#CBD5E1", "#0F172A", "#475569", ["#1D4ED8", "#374151", "#0EA5E9", "#15803D", "#CA8A04", "#DC2626"], "Crisp enterprise dashboard theme."),
    _theme("modern", "Modern", "Modern", "light", "#2563EB", "#7C3AED", "#06B6D4", "#10B981", "#F59E0B", "#EF4444", "#F8FAFF", "#FFFFFF", "#EEF2FF", "#D9E1F2", "#172033", "#667085", ["#2563EB", "#7C3AED", "#06B6D4", "#10B981", "#F97316", "#F43F5E"], "Modern product analytics style."),
    _theme("dark", "Dark", "Executive", "dark", "#60A5FA", "#A78BFA", "#FBBF24", "#34D399", "#F59E0B", "#F87171", "#05070B", "#10131A", "#1B2130", "#374151", "#F9FAFB", "#CBD5E1", ["#60A5FA", "#A78BFA", "#34D399", "#FBBF24", "#F87171", "#22D3EE"], "Dark boardroom display theme.", shadow="0 18px 44px rgba(0, 0, 0, 0.24)"),
    _theme("minimal", "Minimal", "Minimal", "light", "#27272A", "#52525B", "#0EA5E9", "#16A34A", "#CA8A04", "#DC2626", "#FAFAFA", "#FFFFFF", "#F4F4F5", "#D4D4D8", "#18181B", "#71717A", ["#27272A", "#52525B", "#71717A", "#0EA5E9", "#16A34A", "#CA8A04"], "Neutral, restrained analysis theme."),
    _theme("retail", "Retail", "Retail", "light", "#DB2777", "#F97316", "#0EA5E9", "#22C55E", "#F59E0B", "#DC2626", "#FFF7FB", "#FFFFFF", "#FCE7F3", "#FBCFE8", "#172033", "#596579", ["#DB2777", "#F97316", "#0EA5E9", "#22C55E", "#7C3AED", "#F59E0B"], "Retail and merchandising dashboard palette."),
    _theme("finance", "Finance", "Finance", "light", "#047857", "#0F766E", "#84CC16", "#16A34A", "#CA8A04", "#DC2626", "#F7FBF8", "#FFFFFF", "#ECFDF5", "#BBF7D0", "#102A1D", "#527063", ["#047857", "#0F766E", "#84CC16", "#0284C7", "#CA8A04", "#DC2626"], "Controlled finance and KPI reporting theme."),
    _theme("healthcare", "Healthcare", "Healthcare", "light", "#0E7490", "#2563EB", "#14B8A6", "#059669", "#D97706", "#BE123C", "#F8FCFF", "#FFFFFF", "#EAF7F8", "#BBDDE2", "#12323A", "#55717A", ["#0E7490", "#2563EB", "#14B8A6", "#059669", "#F59E0B", "#DC2626"], "Healthcare operations and quality theme."),
    _theme("telecom", "Telecom", "Telecom", "light", "#4338CA", "#0891B2", "#F97316", "#10B981", "#F59E0B", "#EF4444", "#F7F8FF", "#FFFFFF", "#EEF2FF", "#C7D2FE", "#172033", "#596579", ["#4338CA", "#0891B2", "#F97316", "#10B981", "#F59E0B", "#EF4444"], "Network, churn, and service performance theme."),
    _theme("marketing", "Marketing", "Marketing", "light", "#BE185D", "#7C3AED", "#F97316", "#22C55E", "#F59E0B", "#EF4444", "#FFF7FB", "#FFFFFF", "#F5F3FF", "#DDD6FE", "#172033", "#596579", ["#BE185D", "#7C3AED", "#F97316", "#0EA5E9", "#22C55E", "#F59E0B"], "Campaign and growth analytics theme."),
    _theme("manufacturing", "Manufacturing", "Manufacturing", "light", "#475569", "#0F766E", "#EA580C", "#16A34A", "#D97706", "#B91C1C", "#F8FAFC", "#FFFFFF", "#F1F5F9", "#CBD5E1", "#111827", "#64748B", ["#475569", "#0F766E", "#EA580C", "#16A34A", "#D97706", "#B91C1C"], "Operations and manufacturing performance theme."),
]


def register_industry_presets() -> None:
    for theme in PRESET_THEMES:
        register_theme(theme)


register_industry_presets()
