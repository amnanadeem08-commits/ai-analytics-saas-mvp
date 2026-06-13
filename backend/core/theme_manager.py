from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from backend.core.config import settings


@dataclass(frozen=True)
class AnalyticsTheme:
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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ThemeManager:
    """Central registry for dashboard and chart styling."""

    def __init__(self) -> None:
        self._themes: dict[str, AnalyticsTheme] = {}
        self._active_theme = "power_bi_professional"
        self._register_defaults()
        self._load_state()

    def register(self, theme: AnalyticsTheme) -> None:
        self._themes[theme.name] = theme

    def list_themes(self) -> list[dict[str, Any]]:
        return [theme.to_dict() for theme in self._themes.values()]

    def get_theme(self, name: str | None = None) -> AnalyticsTheme:
        key = name or self._active_theme
        if key not in self._themes:
            key = self._active_theme
        return self._themes[key]

    def set_active(self, name: str) -> AnalyticsTheme:
        if name not in self._themes:
            raise ValueError(f"Unknown theme: {name}")
        self._active_theme = name
        self._save_state()
        return self._themes[name]

    def active_name(self) -> str:
        return self._active_theme

    def plotly_layout(self, title: str, x_title: str = "", y_title: str = "", theme_name: str | None = None) -> dict[str, Any]:
        theme = self.get_theme(theme_name)
        layout: dict[str, Any] = {
            "title": {"text": title, "font": {"color": theme.text, "size": 18}},
            "paper_bgcolor": theme.surface,
            "plot_bgcolor": theme.surface,
            "font": {"color": theme.text, "family": "Inter, Segoe UI, Arial"},
            "colorway": theme.palette,
            "margin": {"l": 52, "r": 28, "t": 64, "b": 52},
            "legend": {
                "orientation": "h",
                "yanchor": "bottom",
                "y": 1.02,
                "xanchor": "right",
                "x": 1,
                "font": {"color": theme.muted_text},
            },
            "hovermode": "closest",
        }
        axis_style = {
            "gridcolor": theme.grid,
            "linecolor": theme.border,
            "zerolinecolor": theme.grid,
            "tickfont": {"color": theme.muted_text},
            "title": {"font": {"color": theme.muted_text}},
        }
        if x_title:
            layout["xaxis"] = {**axis_style, "title": {"text": x_title, "font": {"color": theme.muted_text}}}
        if y_title:
            layout["yaxis"] = {**axis_style, "title": {"text": y_title, "font": {"color": theme.muted_text}}}
        return layout

    def _load_state(self) -> None:
        try:
            payload = json.loads(settings.THEME_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            payload = {}
        active_theme = payload.get("active_theme")
        if active_theme in self._themes:
            self._active_theme = active_theme

    def _save_state(self) -> None:
        settings.THEME_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        settings.THEME_STATE_FILE.write_text(
            json.dumps({"active_theme": self._active_theme}, indent=2),
            encoding="utf-8",
        )

    def _register_defaults(self) -> None:
        self.register(
            AnalyticsTheme(
                name="power_bi_professional",
                display_name="Power BI Professional",
                mode="light",
                background="#F5F7FA",
                surface="#FFFFFF",
                surface_alt="#EEF2F7",
                text="#1B1F23",
                muted_text="#5F6B7A",
                grid="#E6EAF0",
                border="#D9E0EA",
                primary="#0078D4",
                secondary="#004E8C",
                accent="#F2C811",
                success="#107C10",
                warning="#F7630C",
                danger="#C50F1F",
                neutral="#6B7280",
                palette=["#0078D4", "#004E8C", "#00B7C3", "#107C10", "#F2C811", "#F7630C", "#C50F1F", "#8764B8"],
            )
        )
        self.register(
            AnalyticsTheme(
                name="tableau_inspired",
                display_name="Tableau Inspired",
                mode="light",
                background="#F7F8FA",
                surface="#FFFFFF",
                surface_alt="#F1F5F9",
                text="#263238",
                muted_text="#607D8B",
                grid="#E6EBEF",
                border="#DCE3EA",
                primary="#4E79A7",
                secondary="#59A14F",
                accent="#F28E2B",
                success="#59A14F",
                warning="#EDC948",
                danger="#E15759",
                neutral="#8D99A6",
                palette=["#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F", "#EDC948", "#B07AA1", "#FF9DA7"],
            )
        )
        self.register(
            AnalyticsTheme(
                name="executive_dark",
                display_name="Executive Dark",
                mode="dark",
                background="#0B1220",
                surface="#111827",
                surface_alt="#1F2937",
                text="#F8FAFC",
                muted_text="#CBD5E1",
                grid="#263244",
                border="#334155",
                primary="#38BDF8",
                secondary="#818CF8",
                accent="#F59E0B",
                success="#34D399",
                warning="#FBBF24",
                danger="#FB7185",
                neutral="#94A3B8",
                palette=["#38BDF8", "#818CF8", "#34D399", "#FBBF24", "#FB7185", "#A78BFA", "#22D3EE", "#F472B6"],
            )
        )
        self.register(
            AnalyticsTheme(
                name="startup_modern",
                display_name="Startup Modern",
                mode="light",
                background="#F8FAFF",
                surface="#FFFFFF",
                surface_alt="#EEF2FF",
                text="#172033",
                muted_text="#667085",
                grid="#E5E7EB",
                border="#D9E1F2",
                primary="#2563EB",
                secondary="#7C3AED",
                accent="#F97316",
                success="#10B981",
                warning="#F59E0B",
                danger="#EF4444",
                neutral="#64748B",
                palette=["#2563EB", "#7C3AED", "#06B6D4", "#10B981", "#F97316", "#F43F5E", "#84CC16", "#A855F7"],
            )
        )
        self.register(
            AnalyticsTheme(
                name="financial_intelligence",
                display_name="Financial Intelligence",
                mode="dark",
                background="#07130D",
                surface="#0F1F17",
                surface_alt="#173526",
                text="#ECFDF5",
                muted_text="#A7F3D0",
                grid="#214734",
                border="#2F5D46",
                primary="#22C55E",
                secondary="#16A34A",
                accent="#38BDF8",
                success="#22C55E",
                warning="#FACC15",
                danger="#EF4444",
                neutral="#86A894",
                palette=["#22C55E", "#16A34A", "#84CC16", "#38BDF8", "#FACC15", "#EF4444", "#14B8A6", "#A3E635"],
            )
        )
        self.register(
            AnalyticsTheme(
                name="minimal_clean",
                display_name="Minimal Clean",
                mode="light",
                background="#FAFAFA",
                surface="#FFFFFF",
                surface_alt="#F4F4F5",
                text="#18181B",
                muted_text="#71717A",
                grid="#E4E4E7",
                border="#D4D4D8",
                primary="#27272A",
                secondary="#52525B",
                accent="#0EA5E9",
                success="#16A34A",
                warning="#CA8A04",
                danger="#DC2626",
                neutral="#A1A1AA",
                palette=["#27272A", "#52525B", "#71717A", "#0EA5E9", "#16A34A", "#CA8A04", "#DC2626", "#A1A1AA"],
            )
        )
        self.register(
            AnalyticsTheme(
                name="boardroom_light",
                display_name="Boardroom Light",
                mode="light",
                background="#F6F7F9",
                surface="#FFFFFF",
                surface_alt="#EEF0F3",
                text="#111827",
                muted_text="#4B5563",
                grid="#E5E7EB",
                border="#D1D5DB",
                primary="#1D4ED8",
                secondary="#374151",
                accent="#B45309",
                success="#047857",
                warning="#D97706",
                danger="#B91C1C",
                neutral="#6B7280",
                palette=["#1D4ED8", "#374151", "#B45309", "#047857", "#7C3AED", "#B91C1C", "#0F766E", "#6B7280"],
            )
        )
        self.register(
            AnalyticsTheme(
                name="boardroom_dark",
                display_name="Boardroom Dark",
                mode="dark",
                background="#05070B",
                surface="#10131A",
                surface_alt="#1B2130",
                text="#F9FAFB",
                muted_text="#CBD5E1",
                grid="#2A3345",
                border="#374151",
                primary="#60A5FA",
                secondary="#A78BFA",
                accent="#FBBF24",
                success="#34D399",
                warning="#F59E0B",
                danger="#F87171",
                neutral="#94A3B8",
                palette=["#60A5FA", "#A78BFA", "#34D399", "#FBBF24", "#F87171", "#22D3EE", "#C084FC", "#94A3B8"],
            )
        )
        self.register(
            AnalyticsTheme(
                name="consulting_report",
                display_name="Consulting Report",
                mode="light",
                background="#FFFFFF",
                surface="#FFFFFF",
                surface_alt="#F3F4F6",
                text="#0F172A",
                muted_text="#475569",
                grid="#E2E8F0",
                border="#CBD5E1",
                primary="#0F172A",
                secondary="#2563EB",
                accent="#0EA5E9",
                success="#15803D",
                warning="#CA8A04",
                danger="#DC2626",
                neutral="#64748B",
                palette=["#0F172A", "#2563EB", "#0EA5E9", "#15803D", "#CA8A04", "#DC2626", "#7C3AED", "#64748B"],
            )
        )
        self.register(
            AnalyticsTheme(
                name="investor_deck",
                display_name="Startup Investor Deck",
                mode="dark",
                background="#080B16",
                surface="#111827",
                surface_alt="#1E293B",
                text="#F8FAFC",
                muted_text="#CBD5E1",
                grid="#334155",
                border="#475569",
                primary="#2DD4BF",
                secondary="#818CF8",
                accent="#FB7185",
                success="#22C55E",
                warning="#FACC15",
                danger="#F43F5E",
                neutral="#94A3B8",
                palette=["#2DD4BF", "#818CF8", "#FB7185", "#FACC15", "#22C55E", "#38BDF8", "#C084FC", "#94A3B8"],
            )
        )
        self.register(
            AnalyticsTheme(
                name="healthcare_executive",
                display_name="Healthcare Executive",
                mode="light",
                background="#F7FBFC",
                surface="#FFFFFF",
                surface_alt="#EAF7F8",
                text="#12323A",
                muted_text="#55717A",
                grid="#D9EEF0",
                border="#BBDDE2",
                primary="#0E7490",
                secondary="#0F766E",
                accent="#7C3AED",
                success="#059669",
                warning="#D97706",
                danger="#BE123C",
                neutral="#64748B",
                palette=["#0E7490", "#0F766E", "#7C3AED", "#059669", "#D97706", "#BE123C", "#2563EB", "#64748B"],
            )
        )
        self.register(
            AnalyticsTheme(
                name="sales_performance",
                display_name="Sales Performance",
                mode="light",
                background="#F8FAFC",
                surface="#FFFFFF",
                surface_alt="#EFF6FF",
                text="#172033",
                muted_text="#596579",
                grid="#DBEAFE",
                border="#BFDBFE",
                primary="#2563EB",
                secondary="#0891B2",
                accent="#F97316",
                success="#16A34A",
                warning="#F59E0B",
                danger="#DC2626",
                neutral="#64748B",
                palette=["#2563EB", "#0891B2", "#16A34A", "#F97316", "#F59E0B", "#DC2626", "#7C3AED", "#64748B"],
            )
        )


theme_manager = ThemeManager()
