import io
import json

from fastapi import APIRouter, Query
from fastapi.responses import Response

from backend.api.deps import map_app_error
from backend.services.dataset_service import load_dataset_dataframe
from backend.services.export_render_service import build_dashboard_snapshot
from backend.services.pdf_export_service import build_executive_pdf
from backend.services.ppt_export_service import build_executive_pptx
from backend.services.report_payload_service import build_report_payload

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
            if chart_ids:
                selected = set(chart_ids)
                body["chart_specs"] = [chart for chart in body.get("chart_specs", []) if chart.get("chart_id") in selected]
                body["chart_count"] = len(body["chart_specs"])
            body["export_package"] = package
            return Response(
                json.dumps(body, indent=2),
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename={dataset_id}_report.json"},
            )
        if fmt == "pdf":
            body = build_report_payload(dataset_id)
            return Response(
                build_executive_pdf(body, chart_ids=chart_ids, package=package),
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename={dataset_id}_executive_report.pdf"},
            )
        if fmt in {"ppt", "pptx"}:
            body = build_report_payload(dataset_id)
            return Response(
                build_executive_pptx(body, chart_ids=chart_ids, package=package),
                media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                headers={"Content-Disposition": f"attachment; filename={dataset_id}_executive_deck.pptx"},
            )
        if fmt == "png":
            body = build_report_payload(dataset_id)
            return Response(
                build_dashboard_snapshot(body, chart_ids=chart_ids),
                media_type="image/png",
                headers={"Content-Disposition": f"attachment; filename={dataset_id}_dashboard_snapshot.png"},
            )
        raise ValueError("Unsupported export format. Use json, csv, pdf, pptx, or png.")
    except Exception as exc:
        raise map_app_error(exc) from exc
