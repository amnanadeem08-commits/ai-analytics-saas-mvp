"""Intelligence API routes.

Response models are intentionally omitted on these endpoints:
- Payloads are domain-dependent and change with detection templates and KPI packs.
- Contract tests assert legacy keys (e.g. executive-storyboard section shape,
  domain route phase-3 fields like domain_detector and dynamic_storyboard_template).
- Even loose response_model schemas risk stripping undeclared keys during
  response validation or failing when optional domain branches omit fields.
"""

from fastapi import APIRouter, Query

from backend.api.deps import map_app_error
from backend.services.ai_business_insight_service import build_ai_business_insights
from backend.services.data_insights_service import build_data_insights
from backend.services.dataset_service import load_dataset_dataframe
from backend.services.domain_intelligence_service import build_domain_context
from backend.services.executive_storyboard_service import build_executive_storyboard
from backend.services.geospatial_service import generate_geo_chart_specs, regional_analytics
from backend.core.theme_manager import theme_manager

router = APIRouter(prefix="/intelligence", tags=["Intelligence"])


@router.get("/{dataset_id}/data-insights")
def data_insights(dataset_id: str):
    try:
        return build_data_insights(load_dataset_dataframe(dataset_id))
    except Exception as exc:
        raise map_app_error(exc) from exc


@router.get("/{dataset_id}/ai-business-insights")
def ai_business_insights(dataset_id: str):
    try:
        return build_ai_business_insights(dataset_id)
    except Exception as exc:
        raise map_app_error(exc) from exc


@router.get("/{dataset_id}/executive-storyboard")
def executive_storyboard(dataset_id: str):
    try:
        return build_executive_storyboard(dataset_id)
    except Exception as exc:
        raise map_app_error(exc) from exc


@router.get("/{dataset_id}/domain")
def domain_intelligence(dataset_id: str):
    try:
        return build_domain_context(load_dataset_dataframe(dataset_id)).to_dict()
    except Exception as exc:
        raise map_app_error(exc) from exc


@router.get("/{dataset_id}/regional")
def regional_intelligence(
    dataset_id: str,
    metric: str | None = Query(default=None),
    aggregation: str | None = Query(default=None),
):
    try:
        df = load_dataset_dataframe(dataset_id)
        theme = theme_manager.get_theme()
        regional = regional_analytics(df, metric=metric, aggregation=aggregation)
        return {
            **regional,
            "map_charts": generate_geo_chart_specs(
                df,
                theme.name,
                metric=regional.get("metric"),
                aggregation=regional.get("aggregation"),
            ),
        }
    except Exception as exc:
        raise map_app_error(exc) from exc
