from __future__ import annotations

"""Sprint 8.9 — design system token smoke tests (no Streamlit runtime required)."""

from frontend.design_system.charts import chart_palette
from frontend.design_system.colors import CHART_PALETTE, COLORS, STATUS_COLORS
from frontend.design_system.spacing import RADIUS, SPACING
from frontend.design_system.tokens import css_root_vars, token_reference
from frontend.design_system.typography import TYPOGRAPHY


def test_primary_color_is_brand_navy() -> None:
    assert COLORS.primary == "#174A7C"
    assert COLORS.danger.startswith("#")


def test_chart_palette_accessible_length() -> None:
    assert len(CHART_PALETTE) >= 5
    assert chart_palette(3) == list(CHART_PALETTE[:3])
    assert len(chart_palette(12)) == 12


def test_status_colors_cover_job_states() -> None:
    for key in ("running", "completed", "failed", "queued"):
        assert key in STATUS_COLORS


def test_spacing_and_typography_tokens() -> None:
    assert SPACING.md == "1rem"
    assert RADIUS.pill == "999px"
    assert "Segoe UI" in TYPOGRAPHY.font_sans
    assert TYPOGRAPHY.metric.weight == 800


def test_css_root_vars_and_token_reference() -> None:
    css = css_root_vars()
    assert "--ds-primary" in css
    assert "--ds-space-md" in css
    ref = token_reference()
    assert "colors" in ref and "typography" in ref
    assert ref["colors"]["primary"] == COLORS.primary
