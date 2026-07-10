from fastapi import APIRouter

from backend.api.deps import map_app_error
from backend.models.analytics_models import ChartSpec
from backend.services.chart_catalog_service import register_custom_chart_spec
from backend.models.visual_builder_models import (
    VisualBuilderRenderResponse,
    VisualBuilderSchemaResponse,
    VisualBuilderSpec,
)
from backend.services.visual_builder_service import (
    discover_visual_builder_schema,
    render_visual_builder_chart,
)

router = APIRouter(prefix="/visual-builder", tags=["Visual Builder"])


@router.get("/{dataset_id}/schema", response_model=VisualBuilderSchemaResponse)
def visual_builder_schema(dataset_id: str):
    try:
        return discover_visual_builder_schema(dataset_id)
    except Exception as exc:
        raise map_app_error(exc) from exc


@router.post("/{dataset_id}/render", response_model=VisualBuilderRenderResponse)
def visual_builder_render(dataset_id: str, spec: VisualBuilderSpec):
    try:
        return render_visual_builder_chart(dataset_id, spec.model_dump())
    except Exception as exc:
        raise map_app_error(exc) from exc


@router.post("/{dataset_id}/register")
def visual_builder_register(dataset_id: str, chart: ChartSpec):
    try:
        return register_custom_chart_spec(dataset_id, chart.model_dump())
    except Exception as exc:
        raise map_app_error(exc) from exc
