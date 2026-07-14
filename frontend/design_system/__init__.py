from __future__ import annotations

"""Khaldun AI DataBot design system (Sprint 8.9).

Frontend-only. Import from `frontend.design_system` or submodules.
"""

from frontend.design_system.alerts import (
    alert,
    notify_error,
    notify_info,
    notify_success,
    notify_warning,
    render_badge,
    status_chip,
    tag,
)
from frontend.design_system.buttons import (
    danger_button,
    ds_button,
    primary_button,
    secondary_button,
    success_button,
)
from frontend.design_system.cards import kpi_card, metric_cards, rich_kpi_grid, section_card
from frontend.design_system.charts import apply_chart_layout, chart_palette, ensure_session_palette, render_chart
from frontend.design_system.colors import CHART_PALETTE, COLORS, STATUS_COLORS
from frontend.design_system.forms import progress_indicator, search_box, tooltip_caption
from frontend.design_system.layout import display_title, page_header, section_header, spacer
from frontend.design_system.modals import confirm_dialog, details_modal
from frontend.design_system.navigation import accordion, tabs, workflow_stepper
from frontend.design_system.spacing import RADIUS, SPACING
from frontend.design_system.tables import data_table
from frontend.design_system.theme import apply_design_system, inject_design_system_css
from frontend.design_system.tokens import css_root_vars, token_reference
from frontend.design_system.typography import TYPOGRAPHY

__all__ = [
    "COLORS",
    "CHART_PALETTE",
    "STATUS_COLORS",
    "SPACING",
    "RADIUS",
    "TYPOGRAPHY",
    "apply_design_system",
    "inject_design_system_css",
    "css_root_vars",
    "token_reference",
    "primary_button",
    "secondary_button",
    "danger_button",
    "success_button",
    "ds_button",
    "section_card",
    "kpi_card",
    "metric_cards",
    "rich_kpi_grid",
    "alert",
    "notify_success",
    "notify_error",
    "notify_warning",
    "notify_info",
    "render_badge",
    "status_chip",
    "tag",
    "search_box",
    "progress_indicator",
    "tooltip_caption",
    "data_table",
    "apply_chart_layout",
    "chart_palette",
    "ensure_session_palette",
    "render_chart",
    "confirm_dialog",
    "details_modal",
    "page_header",
    "display_title",
    "section_header",
    "spacer",
    "tabs",
    "accordion",
    "workflow_stepper",
]
