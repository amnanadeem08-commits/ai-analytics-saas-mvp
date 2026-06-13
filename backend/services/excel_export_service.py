from __future__ import annotations

import io
from typing import Any

import pandas as pd


def _safe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    safe: list[dict[str, Any]] = []
    for row in rows:
        safe.append(
            {
                key: str(value) if isinstance(value, (dict, list)) else value
                for key, value in row.items()
            }
        )
    return safe


def build_executive_excel(report: dict[str, Any], chart_ids: list[str] | None = None, package: str = "executive") -> bytes:
    buffer = io.BytesIO()
    selected = set(chart_ids or [])
    charts = [
        chart
        for chart in report.get("chart_specs", [])
        if not selected or chart.get("chart_id") in selected
    ]
    executive = report.get("executive_summary", {})

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame(
            [
                {
                    "dataset_id": report.get("dataset_id", ""),
                    "package": package,
                    "company": report.get("branding", {}).get("company_name", "AI Analytics"),
                    "report_title": report.get("branding", {}).get("report_title", "Executive Report"),
                    **report.get("overview", {}),
                }
            ]
        ).to_excel(writer, sheet_name="Overview", index=False)

        pd.DataFrame(_safe_rows(report.get("kpi_cards", []))).to_excel(writer, sheet_name="KPI Cards", index=False)

        pd.DataFrame(
            [
                {"section": "Insight", "text": executive.get("insight", "")},
                {"section": "Reason", "text": executive.get("reason", "")},
                {"section": "Action", "text": executive.get("action", "")},
                {"section": "Data Confidence", "text": executive.get("data_confidence", executive.get("confidence", ""))},
                {"section": "Business Confidence", "text": executive.get("business_confidence", "")},
            ]
        ).to_excel(writer, sheet_name="Executive Summary", index=False)

        pd.DataFrame([report.get("data_quality_score", {})]).to_excel(writer, sheet_name="Data Quality", index=False)
        pd.DataFrame(_safe_rows(executive.get("recommendations", []))).to_excel(writer, sheet_name="Recommendations", index=False)
        pd.DataFrame(_safe_rows(executive.get("action_plan", []))).to_excel(writer, sheet_name="Action Plan", index=False)
        pd.DataFrame(
            [
                {
                    "chart_id": chart.get("chart_id", ""),
                    "title": chart.get("title", ""),
                    "chart_type": chart.get("chart_type", ""),
                    "section": chart.get("section", ""),
                    "columns": ", ".join(chart.get("columns", [])),
                    "subtitle": chart.get("metadata", {}).get("subtitle", ""),
                }
                for chart in charts
            ]
        ).to_excel(writer, sheet_name="Charts", index=False)
        pd.DataFrame({"question": report.get("suggested_questions", [])}).to_excel(writer, sheet_name="Suggested Questions", index=False)

        for worksheet in writer.book.worksheets:
            worksheet.freeze_panes = "A2"
            for column_cells in worksheet.columns:
                max_length = max(len(str(cell.value or "")) for cell in column_cells)
                worksheet.column_dimensions[column_cells[0].column_letter].width = min(max(max_length + 2, 12), 48)

    return buffer.getvalue()
