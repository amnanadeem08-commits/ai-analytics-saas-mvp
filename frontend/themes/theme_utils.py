from __future__ import annotations

from typing import Any

from frontend.themes.industry_presets import register_industry_presets  # noqa: F401
from frontend.themes.theme_models import ThemeDefinition
from frontend.themes.theme_registry import get_theme


def css_variables(theme: ThemeDefinition, branding: dict[str, Any] | None = None) -> dict[str, str]:
    branding = branding or {}
    primary = str(branding.get("primary_color") or theme.primary)
    secondary = str(branding.get("secondary_color") or theme.secondary)
    accent = str(branding.get("accent_color") or theme.accent)
    return {
        "--brand-primary": primary,
        "--brand-secondary": secondary,
        "--brand-accent": accent,
        "--brand-font": theme.typography.font_family,
        "--ui-surface": theme.background,
        "--surface-card": theme.card_background,
        "--surface-alt": theme.surface_alt,
        "--surface-border": theme.border,
        "--text-color": theme.text,
        "--text-subtle": theme.subtle_text,
        "--text-muted": theme.muted_text,
        "--text-muted-soft": theme.muted_text,
        "--ui-success": theme.success,
        "--ui-success-strong": theme.success,
        "--ui-info": primary,
        "--ui-info-strong": secondary,
        "--ui-warning": theme.warning,
        "--ui-warning-strong": theme.warning,
        "--ui-danger": theme.error,
        "--ui-danger-strong": theme.error,
        "--ui-accent": accent,
        "--ui-accent-strong": accent,
        "--theme-radius": theme.radius,
        "--theme-shadow": theme.shadow,
        "--theme-spacing-sm": theme.spacing.sm,
        "--theme-spacing-md": theme.spacing.md,
        "--theme-spacing-lg": theme.spacing.lg,
    }


def css_variable_block(theme_name: str | None, branding: dict[str, Any] | None = None) -> str:
    theme = get_theme(theme_name)
    variables = css_variables(theme, branding)
    return "\n".join(f"            {key}: {value};" for key, value in variables.items())


def legacy_preset(theme: ThemeDefinition) -> dict[str, Any]:
    return {
        "name": theme.name,
        "display_name": theme.display_name,
        "background": theme.background,
        "palette": theme.palette,
        "description": theme.description,
        "primary": theme.primary,
        "secondary": theme.secondary,
        "accent": theme.accent,
        "mode": theme.mode,
        "category": theme.category,
    }
