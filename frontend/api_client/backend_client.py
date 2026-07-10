from __future__ import annotations

import logging
import os
import time
from typing import Any

import requests

from frontend.api_client import endpoints


DEFAULT_API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

_log = logging.getLogger("ai_analytics.api")


class BackendClient:
    """Streamlit-friendly wrapper around the FastAPI backend.

    All public methods route through ``_request()`` which provides:
    - Automatic retry on transient connection errors (exponential back-off).
    - Per-category timeouts so uploads/exports never starve fast health checks.
    - Structured debug/warning logging via the ``ai_analytics.api`` logger.
    - A ``_friendly_error()`` helper for producing human-readable messages.
    """

    # Timeout presets: (connect_seconds, read_seconds)
    _TIMEOUT_HEALTH: tuple[float, float] = (3.0, 6.0)
    _TIMEOUT_FAST: tuple[float, float] = (5.0, 15.0)
    _TIMEOUT_MEDIUM: tuple[float, float] = (5.0, 30.0)
    _TIMEOUT_SLOW: tuple[float, float] = (10.0, 120.0)
    _TIMEOUT_UPLOAD: tuple[float, float] = (10.0, 600.0)

    def __init__(self, base_url: str = DEFAULT_API_BASE_URL):
        self.base_url = base_url.rstrip("/")

    # ── Internal helpers ────────────────────────────────────────────────

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _request(
        self,
        method: str,
        path: str,
        *,
        timeout: tuple[float, float] | float = (5.0, 30.0),
        max_retries: int = 2,
        **kwargs: Any,
    ) -> requests.Response:
        """Execute an HTTP request, retrying on transient connection errors."""
        url = self._url(path)
        last_exc: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                _log.debug(
                    "%s %s (attempt %d/%d)",
                    method.upper(), path, attempt + 1, max_retries + 1,
                )
                resp = requests.request(method, url, timeout=timeout, **kwargs)
                resp.raise_for_status()
                _log.debug("%s %s -> HTTP %d", method.upper(), path, resp.status_code)
                return resp
            except requests.exceptions.Timeout as exc:
                _log.warning("Timeout: %s %s (attempt %d)", method.upper(), path, attempt + 1)
                last_exc = exc
                break  # Timeouts are not retried — the operation is unlikely to complete faster
            except requests.exceptions.ConnectionError as exc:
                _log.warning(
                    "Connection error: %s %s (attempt %d): %s",
                    method.upper(), path, attempt + 1, exc,
                )
                last_exc = exc
                if attempt < max_retries:
                    time.sleep(0.4 * (attempt + 1))  # 0.4 s, then 0.8 s
            except requests.HTTPError as exc:
                _log.warning("HTTP error: %s %s -> %s", method.upper(), path, exc)
                raise
        assert last_exc is not None
        raise last_exc

    @staticmethod
    def _friendly_error(exc: Exception) -> str:
        """Convert a requests exception to a user-readable message (no tracebacks)."""
        if isinstance(exc, requests.exceptions.ConnectionError):
            return "Cannot connect to the backend. Verify the server is running and the URL is correct."
        if isinstance(exc, requests.exceptions.Timeout):
            return "Request timed out. The backend may be processing a large dataset — try again shortly."
        if isinstance(exc, requests.exceptions.HTTPError) and exc.response is not None:
            try:
                detail = exc.response.json().get("detail", exc.response.text)
                return f"Backend error ({exc.response.status_code}): {str(detail)[:200]}"
            except Exception:
                return f"Backend returned HTTP {exc.response.status_code}."
        return "An unexpected error occurred while communicating with the backend."

    # ── Health ───────────────────────────────────────────────────────────

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health", timeout=self._TIMEOUT_HEALTH, max_retries=1).json()

    # ── Upload ───────────────────────────────────────────────────────────

    def upload_csv(self, uploaded_file) -> dict[str, Any]:
        suffix = os.path.splitext(uploaded_file.name)[1].lower()
        content_type = (
            "text/csv"
            if suffix == ".csv"
            else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        uploaded_file.seek(0)
        files = {"file": (uploaded_file.name, uploaded_file, content_type)}
        _log.info("Uploading file: %s", uploaded_file.name)
        response = requests.post(
            self._url(endpoints.UPLOAD), files=files, timeout=self._TIMEOUT_UPLOAD
        )
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

    # ── Datasets ─────────────────────────────────────────────────────────

    def list_datasets(self) -> list[dict[str, Any]]:
        return self._request("GET", endpoints.DATASETS, timeout=self._TIMEOUT_FAST).json()

    def get_preview(self, dataset_id: str, rows: int = 10) -> dict[str, Any]:
        path = endpoints.DATASET_PREVIEW.format(dataset_id=dataset_id)
        return self._request("GET", path, params={"rows": rows}, timeout=self._TIMEOUT_MEDIUM).json()

    def get_overview(self, dataset_id: str) -> dict[str, Any]:
        path = endpoints.DATASET_OVERVIEW.format(dataset_id=dataset_id)
        return self._request("GET", path, timeout=self._TIMEOUT_MEDIUM).json()

    def clean_dataset(self, dataset_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        path = endpoints.DATASET_CLEAN.format(dataset_id=dataset_id)
        return self._request("POST", path, json=payload, timeout=self._TIMEOUT_SLOW).json()

    def download_cleaned_dataset(self, dataset_id: str, filename: str) -> bytes:
        path = endpoints.DATASET_CLEAN_DOWNLOAD.format(dataset_id=dataset_id)
        return self._request(
            "GET", path, params={"filename": filename}, timeout=self._TIMEOUT_SLOW
        ).content

    # ── Analytics ────────────────────────────────────────────────────────

    def get_summary(self, dataset_id: str) -> dict[str, Any]:
        path = endpoints.ANALYTICS_SUMMARY.format(dataset_id=dataset_id)
        return self._request("GET", path, timeout=self._TIMEOUT_MEDIUM).json()

    def get_dashboard(self, dataset_id: str) -> dict[str, Any]:
        path = endpoints.ANALYTICS_DASHBOARD.format(dataset_id=dataset_id)
        return self._request("GET", path, timeout=self._TIMEOUT_MEDIUM).json()

    def get_filtered_dashboard(self, dataset_id: str, filters: dict[str, Any]) -> dict[str, Any]:
        path = endpoints.ANALYTICS_DASHBOARD_FILTER.format(dataset_id=dataset_id)
        return self._request(
            "POST", path, json={"filters": filters}, timeout=self._TIMEOUT_MEDIUM
        ).json()

    # ── Insights / AI ────────────────────────────────────────────────────

    def get_insights(self, dataset_id: str) -> dict[str, Any]:
        path = endpoints.INSIGHTS.format(dataset_id=dataset_id)
        return self._request("GET", path, timeout=self._TIMEOUT_MEDIUM).json()

    def ask_question(self, dataset_id: str, question: str) -> dict[str, Any]:
        path = endpoints.ASK_QUESTION.format(dataset_id=dataset_id)
        return self._request(
            "POST", path, json={"question": question}, timeout=self._TIMEOUT_SLOW
        ).json()

    def get_data_insights(self, dataset_id: str) -> dict[str, Any]:
        path = endpoints.DATA_INSIGHTS.format(dataset_id=dataset_id)
        return self._request("GET", path, timeout=self._TIMEOUT_MEDIUM).json()

    def get_ai_business_insights(self, dataset_id: str) -> dict[str, Any]:
        path = endpoints.AI_BUSINESS_INSIGHTS.format(dataset_id=dataset_id)
        return self._request("GET", path, timeout=self._TIMEOUT_MEDIUM).json()

    def get_executive_storyboard(self, dataset_id: str) -> dict[str, Any]:
        path = endpoints.EXECUTIVE_STORYBOARD.format(dataset_id=dataset_id)
        return self._request("GET", path, timeout=self._TIMEOUT_MEDIUM).json()

    def get_domain_intelligence(self, dataset_id: str) -> dict[str, Any]:
        path = endpoints.DOMAIN_INTELLIGENCE.format(dataset_id=dataset_id)
        return self._request("GET", path, timeout=self._TIMEOUT_MEDIUM).json()

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
        return self._request("GET", path, params=params, timeout=self._TIMEOUT_MEDIUM).json()

    # ── Visual builder ───────────────────────────────────────────────────

    def get_visual_builder_schema(self, dataset_id: str) -> dict[str, Any]:
        path = endpoints.VISUAL_BUILDER_SCHEMA.format(dataset_id=dataset_id)
        return self._request("GET", path, timeout=self._TIMEOUT_MEDIUM).json()

    def render_visual(self, dataset_id: str, spec: dict[str, Any]) -> dict[str, Any]:
        path = endpoints.VISUAL_BUILDER_RENDER.format(dataset_id=dataset_id)
        return self._request("POST", path, json=spec, timeout=self._TIMEOUT_MEDIUM).json()

    def register_visual(self, dataset_id: str, chart: dict[str, Any]) -> dict[str, Any]:
        path = endpoints.VISUAL_BUILDER_REGISTER.format(dataset_id=dataset_id)
        return self._request("POST", path, json=chart, timeout=self._TIMEOUT_MEDIUM).json()

    # ── Reports / Export ─────────────────────────────────────────────────

    def get_report(self, dataset_id: str) -> dict[str, Any]:
        path = endpoints.REPORT.format(dataset_id=dataset_id)
        return self._request("GET", path, timeout=self._TIMEOUT_MEDIUM).json()

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
        return self._request("GET", path, params=params, timeout=self._TIMEOUT_SLOW).content

    # ── Theme / Branding ─────────────────────────────────────────────────

    def list_themes(self) -> dict[str, Any]:
        return self._request("GET", endpoints.THEMES, timeout=self._TIMEOUT_FAST).json()

    def set_active_theme(self, theme_name: str) -> dict[str, Any]:
        path = endpoints.ACTIVE_THEME.format(theme_name=theme_name)
        return self._request("POST", path, timeout=self._TIMEOUT_FAST).json()

    def get_branding(self) -> dict[str, Any]:
        return self._request("GET", endpoints.BRANDING, timeout=self._TIMEOUT_FAST).json()

    def update_branding(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("PUT", endpoints.BRANDING, json=payload, timeout=self._TIMEOUT_FAST).json()

    def upload_logo(self, uploaded_file) -> dict[str, Any]:
        files = {
            "file": (
                uploaded_file.name,
                uploaded_file.getvalue(),
                uploaded_file.type or "application/octet-stream",
            )
        }
        response = requests.post(
            self._url(endpoints.BRANDING_LOGO), files=files, timeout=self._TIMEOUT_UPLOAD
        )
        response.raise_for_status()
        return response.json()

    # ── SQL Lab ──────────────────────────────────────────────────────────

    def get_sql_templates(self, dataset_id: str) -> dict[str, Any]:
        path = endpoints.SQL_TEMPLATES.format(dataset_id=dataset_id)
        return self._request("GET", path, timeout=self._TIMEOUT_FAST).json()

    def get_sql_history(self, dataset_id: str) -> dict[str, Any]:
        path = endpoints.SQL_HISTORY.format(dataset_id=dataset_id)
        return self._request("GET", path, timeout=self._TIMEOUT_FAST).json()

    def run_sql(self, dataset_id: str, sql: str, limit: int = 100) -> dict[str, Any]:
        path = endpoints.SQL_QUERY.format(dataset_id=dataset_id)
        return self._request(
            "POST", path, json={"sql": sql, "limit": limit}, timeout=self._TIMEOUT_SLOW
        ).json()

    def generate_sql(self, dataset_id: str, prompt: str) -> dict[str, Any]:
        path = endpoints.SQL_GENERATE.format(dataset_id=dataset_id)
        return self._request(
            "POST", path, json={"prompt": prompt}, timeout=self._TIMEOUT_MEDIUM
        ).json()

    def save_sql(self, dataset_id: str, name: str, sql: str) -> dict[str, Any]:
        path = endpoints.SQL_SAVE.format(dataset_id=dataset_id)
        return self._request(
            "POST", path, json={"name": name, "sql": sql}, timeout=self._TIMEOUT_FAST
        ).json()

    def explain_sql(self, sql: str) -> dict[str, Any]:
        return self._request(
            "POST", endpoints.SQL_EXPLAIN, json={"sql": sql, "limit": 100}, timeout=self._TIMEOUT_FAST
        ).json()

    def optimize_sql(self, sql: str) -> dict[str, Any]:
        return self._request(
            "POST", endpoints.SQL_OPTIMIZE, json={"sql": sql, "limit": 100}, timeout=self._TIMEOUT_FAST
        ).json()

    def detect_sql_errors(self, sql: str) -> dict[str, Any]:
        return self._request(
            "POST", endpoints.SQL_DETECT_ERRORS, json={"sql": sql, "limit": 100},
            timeout=self._TIMEOUT_FAST,
        ).json()

    # ── DAX Studio ───────────────────────────────────────────────────────

    def get_dax_library(self, dataset_id: str) -> dict[str, Any]:
        path = endpoints.DAX_LIBRARY.format(dataset_id=dataset_id)
        return self._request("GET", path, timeout=self._TIMEOUT_FAST).json()

    def generate_dax(self, dataset_id: str, prompt: str) -> dict[str, Any]:
        path = endpoints.DAX_GENERATE.format(dataset_id=dataset_id)
        return self._request(
            "POST", path, json={"prompt": prompt}, timeout=self._TIMEOUT_MEDIUM
        ).json()

    def explain_dax(self, dax: str) -> dict[str, Any]:
        return self._request(
            "POST", endpoints.DAX_EXPLAIN, json={"dax": dax}, timeout=self._TIMEOUT_FAST
        ).json()

    def optimize_dax(self, dax: str, dataset_id: str | None = None) -> dict[str, Any]:
        path = (
            endpoints.DAX_OPTIMIZE_DATASET.format(dataset_id=dataset_id)
            if dataset_id
            else endpoints.DAX_OPTIMIZE
        )
        return self._request(
            "POST", path, json={"dax": dax}, timeout=self._TIMEOUT_FAST
        ).json()

    def detect_dax_errors(self, dax: str) -> dict[str, Any]:
        return self._request(
            "POST", endpoints.DAX_DETECT_ERRORS, json={"dax": dax}, timeout=self._TIMEOUT_FAST
        ).json()
