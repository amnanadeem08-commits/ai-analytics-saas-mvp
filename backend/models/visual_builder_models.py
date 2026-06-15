from typing import Any

from pydantic import BaseModel

from backend.models.analytics_models import ChartSpec


class VisualField(BaseModel):
    name: str
    role: str
    dtype: str
    semantic_type: str
    unique_count: int
    sample_values: list[Any]
    semantic_role: str = "dimension_column"
    business_priority: int = 50
    helper_message: str = ""


class VisualBuilderSchemaResponse(BaseModel):
    dataset_id: str
    dimensions: list[VisualField]
    measures: list[VisualField]
    dates: list[VisualField]
    semantic_layer: list[VisualField]
    recommended_visuals: list[dict[str, Any]] = []
    slicer_recommendations: list[dict[str, Any]] = []
    filters: dict[str, Any]
    suggested_defaults: dict[str, Any]


class VisualBuilderSpec(BaseModel):
    chart_type: str = "bar"
    dimension: str | None = None
    measure: str | None = None
    aggregation: str = "sum"
    sort: str = "descending"
    legend: str | None = None
    tooltip: str | None = None
    number_format: str = "Auto"
    title: str | None = None
    data_labels: bool = True
    filters: dict[str, Any] = {}


class VisualBuilderRenderResponse(BaseModel):
    dataset_id: str
    chart: ChartSpec
    applied_spec: VisualBuilderSpec
    suggestions: list[dict[str, Any]]
    semantic_warnings: list[str] = []
