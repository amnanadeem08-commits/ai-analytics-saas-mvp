from typing import Any

from pydantic import BaseModel, ConfigDict


class ThemeListResponse(BaseModel):
    """Loose schema for theme registry listing."""

    model_config = ConfigDict(extra="allow")

    active_theme: str
    themes: list[dict[str, Any]]


class ThemeResponse(BaseModel):
    """Loose schema for a single analytics theme."""

    model_config = ConfigDict(extra="allow")

    name: str
    display_name: str
    mode: str
    background: str
    surface: str
    surface_alt: str
    text: str
    muted_text: str
    grid: str
    border: str
    primary: str
    secondary: str
    accent: str
    success: str
    warning: str
    danger: str
    neutral: str
    palette: list[str]
