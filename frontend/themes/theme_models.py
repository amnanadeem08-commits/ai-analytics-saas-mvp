from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class ThemeTypography:
    font_family: str = "Inter, Segoe UI, Arial, sans-serif"
    heading_weight: int = 900
    body_weight: int = 400
    base_size: str = "0.95rem"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ThemeSpacing:
    xs: str = "4px"
    sm: str = "8px"
    md: str = "12px"
    lg: str = "18px"
    xl: str = "24px"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ThemeDefinition:
    name: str
    display_name: str
    category: str
    mode: str
    primary: str
    secondary: str
    accent: str
    success: str
    warning: str
    error: str
    background: str
    card_background: str
    surface_alt: str
    border: str
    text: str
    muted_text: str
    subtle_text: str
    typography: ThemeTypography = field(default_factory=ThemeTypography)
    spacing: ThemeSpacing = field(default_factory=ThemeSpacing)
    radius: str = "8px"
    shadow: str = "0 14px 34px rgba(15, 23, 42, 0.08)"
    icon_style: str = "rounded"
    chart_palette: list[str] = field(default_factory=list)
    description: str = ""

    @property
    def palette(self) -> list[str]:
        return self.chart_palette or [self.primary, self.secondary, self.accent, self.success, self.warning, self.error]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["palette"] = self.palette
        payload["primary_color"] = self.primary
        payload["secondary_color"] = self.secondary
        payload["accent_color"] = self.accent
        return payload
