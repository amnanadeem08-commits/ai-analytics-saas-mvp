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


class VisualBuilderSchemaResponse(BaseModel):
    dataset_id: str
    dimensions: list[VisualField]
    measures: list[VisualField]
    dates: list[VisualField]
    filters: dict[str, Any]
    suggested_defaults: dict[str, Any]


class VisualBuilderSpec(BaseModel):
    chart_type: str = "bar"
    dimension: str | None = None
    measure: str | None = None
    aggregation: str = "sum"
    filters: dict[str, Any] = {}


class VisualBuilderRenderResponse(BaseModel):
    dataset_id: str
    chart: ChartSpec
    applied_spec: VisualBuilderSpec
    suggestions: list[dict[str, Any]]
