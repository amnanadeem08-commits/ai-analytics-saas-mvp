from __future__ import annotations

import os
from typing import Any

import requests

from frontend.api_client import endpoints


DEFAULT_API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


class BackendClient:
    """Small Streamlit-friendly wrapper around the FastAPI backend."""

    def __init__(self, base_url: str = DEFAULT_API_BASE_URL):
        self.base_url = base_url.rstrip("/")

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def health(self) -> dict[str, Any]:
        response = requests.get(self._url("/health"), timeout=10)
        response.raise_for_status()
        return response.json()

    def upload_csv(self, uploaded_file) -> dict[str, Any]:
        suffix = os.path.splitext(uploaded_file.name)[1].lower()
        content_type = (
            "text/csv"
            if suffix == ".csv"
            else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        uploaded_file.seek(0)
        files = {"file": (uploaded_file.name, uploaded_file, content_type)}
        response = requests.post(self._url(endpoints.UPLOAD), files=files, timeout=(10, 600))
        if not response.ok:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            raise requests.HTTPError(
                f"Backend rejected the upload ({response.status_code}): {detail}",
                response=response,
            )
        return response.json()

    def list_datasets(self) -> list[dict[str, Any]]:
        response = requests.get(self._url(endpoints.DATASETS), timeout=20)
        response.raise_for_status()
        return response.json()

    def get_preview(self, dataset_id: str, rows: int = 10) -> dict[str, Any]:
        path = endpoints.DATASET_PREVIEW.format(dataset_id=dataset_id)
        response = requests.get(self._url(path), params={"rows": rows}, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_overview(self, dataset_id: str) -> dict[str, Any]:
        path = endpoints.DATASET_OVERVIEW.format(dataset_id=dataset_id)
        response = requests.get(self._url(path), timeout=30)
        response.raise_for_status()
        return response.json()

    def get_summary(self, dataset_id: str) -> dict[str, Any]:
        path = endpoints.ANALYTICS_SUMMARY.format(dataset_id=dataset_id)
        response = requests.get(self._url(path), timeout=30)
        response.raise_for_status()
        return response.json()

    def get_dashboard(self, dataset_id: str) -> dict[str, Any]:
        path = endpoints.ANALYTICS_DASHBOARD.format(dataset_id=dataset_id)
        response = requests.get(self._url(path), timeout=30)
        response.raise_for_status()
        return response.json()

    def get_filtered_dashboard(self, dataset_id: str, filters: dict[str, Any]) -> dict[str, Any]:
        path = endpoints.ANALYTICS_DASHBOARD_FILTER.format(dataset_id=dataset_id)
        response = requests.post(self._url(path), json={"filters": filters}, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_insights(self, dataset_id: str) -> dict[str, Any]:
        path = endpoints.INSIGHTS.format(dataset_id=dataset_id)
        response = requests.get(self._url(path), timeout=30)
        response.raise_for_status()
        return response.json()

    def ask_question(self, dataset_id: str, question: str) -> dict[str, Any]:
        path = endpoints.ASK_QUESTION.format(dataset_id=dataset_id)
        response = requests.post(self._url(path), json={"question": question}, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_visual_builder_schema(self, dataset_id: str) -> dict[str, Any]:
        path = endpoints.VISUAL_BUILDER_SCHEMA.format(dataset_id=dataset_id)
        response = requests.get(self._url(path), timeout=30)
        response.raise_for_status()
        return response.json()

    def render_visual(self, dataset_id: str, spec: dict[str, Any]) -> dict[str, Any]:
        path = endpoints.VISUAL_BUILDER_RENDER.format(dataset_id=dataset_id)
        response = requests.post(self._url(path), json=spec, timeout=30)
        response.raise_for_status()
        return response.json()

    def register_visual(self, dataset_id: str, chart: dict[str, Any]) -> dict[str, Any]:
        path = endpoints.VISUAL_BUILDER_REGISTER.format(dataset_id=dataset_id)
        response = requests.post(self._url(path), json=chart, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_report(self, dataset_id: str) -> dict[str, Any]:
        path = endpoints.REPORT.format(dataset_id=dataset_id)
        response = requests.get(self._url(path), timeout=30)
        response.raise_for_status()
        return response.json()

    def export_report(
        self,
        dataset_id: str,
        report_format: str,
        chart_ids: list[str] | None = None,
        kpi_ids: list[str] | None = None,
        package: str = "executive",
    ) -> bytes:
        path = endpoints.REPORT_EXPORT.format(dataset_id=dataset_id)
        params: list[tuple[str, str]] = [("format", report_format), ("package", package)]
        for chart_id in chart_ids or []:
            params.append(("chart_ids", chart_id))
        for kpi_id in kpi_ids or []:
            params.append(("kpi_ids", kpi_id))
        response = requests.get(self._url(path), params=params, timeout=60)
        response.raise_for_status()
        return response.content

    def clean_dataset(self, dataset_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        path = endpoints.DATASET_CLEAN.format(dataset_id=dataset_id)
        response = requests.post(self._url(path), json=payload, timeout=120)
        response.raise_for_status()
        return response.json()

    def download_cleaned_dataset(self, dataset_id: str, filename: str) -> bytes:
        path = endpoints.DATASET_CLEAN_DOWNLOAD.format(dataset_id=dataset_id)
        response = requests.get(self._url(path), params={"filename": filename}, timeout=120)
        response.raise_for_status()
        return response.content

    def list_themes(self) -> dict[str, Any]:
        response = requests.get(self._url(endpoints.THEMES), timeout=20)
        response.raise_for_status()
        return response.json()

    def set_active_theme(self, theme_name: str) -> dict[str, Any]:
        path = endpoints.ACTIVE_THEME.format(theme_name=theme_name)
        response = requests.post(self._url(path), timeout=20)
        response.raise_for_status()
        return response.json()

    def get_branding(self) -> dict[str, Any]:
        response = requests.get(self._url(endpoints.BRANDING), timeout=20)
        response.raise_for_status()
        return response.json()

    def update_branding(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = requests.put(self._url(endpoints.BRANDING), json=payload, timeout=20)
        response.raise_for_status()
        return response.json()

    def upload_logo(self, uploaded_file) -> dict[str, Any]:
        files = {
            "file": (
                uploaded_file.name,
                uploaded_file.getvalue(),
                uploaded_file.type or "application/octet-stream",
            )
        }
        response = requests.post(self._url(endpoints.BRANDING_LOGO), files=files, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_sql_templates(self, dataset_id: str) -> dict[str, Any]:
        path = endpoints.SQL_TEMPLATES.format(dataset_id=dataset_id)
        response = requests.get(self._url(path), timeout=20)
        response.raise_for_status()
        return response.json()

    def get_sql_history(self, dataset_id: str) -> dict[str, Any]:
        path = endpoints.SQL_HISTORY.format(dataset_id=dataset_id)
        response = requests.get(self._url(path), timeout=20)
        response.raise_for_status()
        return response.json()

    def run_sql(self, dataset_id: str, sql: str, limit: int = 100) -> dict[str, Any]:
        path = endpoints.SQL_QUERY.format(dataset_id=dataset_id)
        response = requests.post(self._url(path), json={"sql": sql, "limit": limit}, timeout=60)
        response.raise_for_status()
        return response.json()

    def generate_sql(self, dataset_id: str, prompt: str) -> dict[str, Any]:
        path = endpoints.SQL_GENERATE.format(dataset_id=dataset_id)
        response = requests.post(self._url(path), json={"prompt": prompt}, timeout=30)
        response.raise_for_status()
        return response.json()

    def save_sql(self, dataset_id: str, name: str, sql: str) -> dict[str, Any]:
        path = endpoints.SQL_SAVE.format(dataset_id=dataset_id)
        response = requests.post(self._url(path), json={"name": name, "sql": sql}, timeout=20)
        response.raise_for_status()
        return response.json()

    def explain_sql(self, sql: str) -> dict[str, Any]:
        response = requests.post(self._url(endpoints.SQL_EXPLAIN), json={"sql": sql, "limit": 100}, timeout=20)
        response.raise_for_status()
        return response.json()

    def optimize_sql(self, sql: str) -> dict[str, Any]:
        response = requests.post(self._url(endpoints.SQL_OPTIMIZE), json={"sql": sql, "limit": 100}, timeout=20)
        response.raise_for_status()
        return response.json()

    def detect_sql_errors(self, sql: str) -> dict[str, Any]:
        response = requests.post(self._url(endpoints.SQL_DETECT_ERRORS), json={"sql": sql, "limit": 100}, timeout=20)
        response.raise_for_status()
        return response.json()

    def get_domain_intelligence(self, dataset_id: str) -> dict[str, Any]:
        path = endpoints.DOMAIN_INTELLIGENCE.format(dataset_id=dataset_id)
        response = requests.get(self._url(path), timeout=30)
        response.raise_for_status()
        return response.json()

    def get_regional_intelligence(
        self,
        dataset_id: str,
        metric: str | None = None,
        aggregation: str | None = None,
    ) -> dict[str, Any]:
        path = endpoints.REGIONAL_INTELLIGENCE.format(dataset_id=dataset_id)
        params: dict[str, str] = {}
        if metric:
            params["metric"] = metric
        if aggregation:
            params["aggregation"] = aggregation
        response = requests.get(self._url(path), params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_dax_library(self, dataset_id: str) -> dict[str, Any]:
        path = endpoints.DAX_LIBRARY.format(dataset_id=dataset_id)
        response = requests.get(self._url(path), timeout=20)
        response.raise_for_status()
        return response.json()

    def generate_dax(self, dataset_id: str, prompt: str) -> dict[str, Any]:
        path = endpoints.DAX_GENERATE.format(dataset_id=dataset_id)
        response = requests.post(self._url(path), json={"prompt": prompt}, timeout=30)
        response.raise_for_status()
        return response.json()

    def explain_dax(self, dax: str) -> dict[str, Any]:
        response = requests.post(self._url(endpoints.DAX_EXPLAIN), json={"dax": dax}, timeout=20)
        response.raise_for_status()
        return response.json()

    def optimize_dax(self, dax: str, dataset_id: str | None = None) -> dict[str, Any]:
        path = endpoints.DAX_OPTIMIZE_DATASET.format(dataset_id=dataset_id) if dataset_id else endpoints.DAX_OPTIMIZE
        response = requests.post(self._url(path), json={"dax": dax}, timeout=20)
        response.raise_for_status()
        return response.json()

    def detect_dax_errors(self, dax: str) -> dict[str, Any]:
        response = requests.post(self._url(endpoints.DAX_DETECT_ERRORS), json={"dax": dax}, timeout=20)
        response.raise_for_status()
        return response.json()
