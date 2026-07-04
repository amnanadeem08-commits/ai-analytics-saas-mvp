from typing import Any
from pydantic import BaseModel


class ColumnTypes(BaseModel):
    numeric_columns: list[str]
    categorical_columns: list[str]
    date_columns: list[str]
    boolean_columns: list[str]


class DataSummaryResponse(BaseModel):
    dataset_id: str
    row_count: int
    column_count: int
    duplicate_rows: int
    total_missing_values: int
    missing_values_by_column: dict[str, int]
    dtypes: dict[str, str]
    column_types: ColumnTypes
    numeric_summary: dict[str, dict[str, Any]]
    categorical_summary: dict[str, list[dict[str, Any]]]


class KpiCard(BaseModel):
    kpi_id: str
    label: str
    value: Any
    format: str = "number"
    category: str = "summary"
    description: str = ""
    current_value: Any = None
    previous_value: Any = None
    delta_percentage: Any = None
    trend: str = "neutral"
    trend_arrow: str = "->"
    status: str = "neutral"
    status_color: str = ""
    business_context: str = ""
    sparkline: list[Any] = []
    reason: str = ""
    recommended_action: str = ""
    expected_impact: str = ""
    evidence: dict[str, Any] = {}
    icon: str = ""
    risk_indicator: str = "normal"
    confidence_score: float = 0.75


class DashboardSection(BaseModel):
    section_id: str
    title: str
    description: str = ""
    card_ids: list[str] = []
    chart_keys: list[str] = []
    chart_ids: list[str] = []
    order: int = 0


class DashboardLayout(BaseModel):
    sections: list[DashboardSection]


class ChartSpec(BaseModel):
    chart_id: str
    title: str
    chart_type: str
    section: str
    columns: list[str]
    plotly: dict[str, Any]
    metadata: dict[str, Any] = {}


class DashboardResponse(BaseModel):
    dataset_id: str
    status: str
    theme: dict[str, Any] = {}
    branding: dict[str, Any] = {}
    filters: dict[str, Any] = {}
    filtered: bool = False
    original_row_count: int | None = None
    filtered_row_count: int | None = None
    overview: dict[str, Any]
    kpi_cards: list[KpiCard]
    chart_specs: list[ChartSpec]
    business_metrics: dict[str, Any]
    domain_intelligence: dict[str, Any] = {}
    domain_context: dict[str, Any] = {}
    regional_analytics: dict[str, Any] = {}
    analysis_guardrails: dict[str, Any] = {}
    data_quality_score: dict[str, Any] = {}
    suggested_questions: list[str] = []
    dashboard_spec: dict[str, Any] = {}
    export_bundle: dict[str, Any] = {}
    layout: DashboardLayout
    column_types: ColumnTypes
    top_categories: dict[str, list[dict[str, Any]]]
    correlations: dict[str, dict[str, Any]]
    time_trends: dict[str, list[dict[str, Any]]]


class DashboardFilterRequest(BaseModel):
    filters: dict[str, Any] = {}
