import streamlit as st


def _format_pct(value: float | int | None) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):.1f}%"


def render_summary_metrics(summary: dict) -> None:
    from frontend.design_system.cards import metric_cards
    from frontend.design_system.layout import section_header

    missing = int(summary.get("total_missing_values", 0) or 0)
    duplicates = int(summary.get("duplicate_rows", 0) or 0)
    total_cells = max(int(summary.get("row_count", 0) or 0) * int(summary.get("column_count", 0) or 0), 1)
    completeness = round((1 - missing / total_cells) * 100, 2)
    quality_label = "Ready" if missing == 0 and duplicates == 0 else "Review"

    section_header("Dataset summary", "Rows, completeness, and readiness at a glance")
    metric_cards(
        [
            ("Rows", f"{summary.get('row_count', 0):,}", "Total records available for analysis."),
            ("Columns", f"{summary.get('column_count', 0):,}", "Total fields available for metrics, segments, and charts."),
            ("Completeness", _format_pct(completeness), "Percent of cells with usable values."),
            ("Missing", f"{missing:,}", "Blank or null values that may affect statistical reliability."),
            ("Quality", quality_label, "Overall readiness based on missing values and duplicate rows."),
        ]
    )
