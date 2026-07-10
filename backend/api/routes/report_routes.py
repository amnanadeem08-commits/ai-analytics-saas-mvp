import io
import json

from fastapi import APIRouter, Query
from fastapi.responses import Response

from backend.api.deps import map_app_error
from backend.services.analytics_service import get_data_summary
from backend.services.dataset_service import load_dataset_dataframe
from backend.services.report_payload_service import (
    build_report_payload,
    filter_report_chart_specs,
    filter_report_kpi_cards,
)

router = APIRouter(prefix="/report", tags=["Reports"])


@router.get("/{dataset_id}")
def report_preview(dataset_id: str):
    try:
        report = build_report_payload(dataset_id)
        return {
            "dataset_id": report["dataset_id"],
            "branding": report["branding"],
            "theme": report["theme"],
            "overview": report["overview"],
            "kpi_cards": report["kpi_cards"],
            "executive_summary": report["executive_summary"],
            "business_story": report["business_story"],
            "domain_intelligence": report.get("domain_intelligence", {}),
            "regional_analytics": report.get("regional_analytics", {}),
            "analysis_guardrails": report.get("analysis_guardrails", {}),
            "data_quality_score": report.get("data_quality_score", {}),
            "suggested_questions": report.get("suggested_questions", []),
            "chart_specs": report["chart_specs"],
            "chart_count": report["chart_count"],
        }
    except Exception as exc:
        raise map_app_error(exc) from exc


@router.get("/{dataset_id}/export")
def export_report(
    dataset_id: str,
    format: str = "json",
    chart_ids: list[str] | None = Query(default=None),
    kpi_ids: list[str] | None = Query(default=None),
    package: str = "executive",
):
    try:
        fmt = format.lower()
        if fmt == "csv":
            df = load_dataset_dataframe(dataset_id)
            buffer = io.StringIO()
            df.to_csv(buffer, index=False)
            return Response(
                buffer.getvalue(),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={dataset_id}.csv"},
            )
        if fmt == "json":
            body = build_report_payload(dataset_id)
            filter_report_chart_specs(body, chart_ids)
            filter_report_kpi_cards(body, kpi_ids)
            body["export_package"] = package
            return Response(
                json.dumps(body, indent=2),
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename={dataset_id}_report.json"},
            )
        if fmt == "pdf":
            body = build_report_payload(dataset_id)
            filter_report_kpi_cards(body, kpi_ids)
            try:
                from backend.services.pdf_export_service import build_executive_pdf
            except ImportError as exc:
                raise ValueError("PDF export dependency is missing. Install reportlab and retry.") from exc
            return Response(
                build_executive_pdf(body, chart_ids=chart_ids, package=package),
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename={dataset_id}_executive_report.pdf"},
            )
        if fmt in {"ppt", "pptx"}:
            body = build_report_payload(dataset_id)
            filter_report_kpi_cards(body, kpi_ids)
            try:
                from backend.services.ppt_export_service import build_executive_pptx
            except ImportError as exc:
                raise ValueError("PowerPoint export dependency is missing. Install python-pptx and retry.") from exc
            return Response(
                build_executive_pptx(body, chart_ids=chart_ids, package=package),
                media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                headers={"Content-Disposition": f"attachment; filename={dataset_id}_executive_deck.pptx"},
            )
        if fmt in {"xlsx", "excel"}:
            body = build_report_payload(dataset_id)
            filter_report_kpi_cards(body, kpi_ids)
            summary = get_data_summary(dataset_id)
            raw_df = load_dataset_dataframe(dataset_id)
            try:
                from backend.services.excel_export_service import build_executive_excel
            except ImportError as exc:
                raise ValueError("Excel export dependency is missing. Install openpyxl and retry.") from exc
            return Response(
                build_executive_excel(body, raw_df=raw_df, summary=summary, chart_ids=chart_ids, package=package),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename={dataset_id}_executive_report.xlsx"},
            )
        if fmt == "png":
            body = build_report_payload(dataset_id)
            try:
                from backend.services.export_render_service import build_dashboard_snapshot
            except ImportError as exc:
                raise ValueError("PNG snapshot dependency is missing. Install Pillow and retry.") from exc
            return Response(
                build_dashboard_snapshot(body, chart_ids=chart_ids),
                media_type="image/png",
                headers={"Content-Disposition": f"attachment; filename={dataset_id}_dashboard_snapshot.png"},
            )
        raise ValueError("Unsupported export format. Use json, csv, pdf, pptx, xlsx, or png.")
    except Exception as exc:
        raise map_app_error(exc) from exc
