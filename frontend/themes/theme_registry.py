from __future__ import annotations

from frontend.themes.theme_models import ThemeDefinition


THEME_REGISTRY: dict[str, ThemeDefinition] = {}


def register_theme(theme: ThemeDefinition) -> ThemeDefinition:
    THEME_REGISTRY[theme.name] = theme
    return theme


def get_theme(name: str | None = None) -> ThemeDefinition:
    if name and name in THEME_REGISTRY:
        return THEME_REGISTRY[name]
    return THEME_REGISTRY.get("executive", next(iter(THEME_REGISTRY.values())))


def list_themes() -> list[ThemeDefinition]:
    return list(THEME_REGISTRY.values())


def theme_options() -> list[dict]:
    return [theme.to_dict() for theme in list_themes()]
