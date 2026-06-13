from fastapi import APIRouter

from backend.api.deps import map_app_error
from backend.services.dataset_service import load_dataset_dataframe
from backend.services.domain_intelligence_service import build_domain_intelligence
from backend.services.geospatial_service import generate_geo_chart_specs, regional_analytics
from backend.core.theme_manager import theme_manager

router = APIRouter(prefix="/intelligence", tags=["Intelligence"])


@router.get("/{dataset_id}/domain")
def domain_intelligence(dataset_id: str):
    try:
        return build_domain_intelligence(load_dataset_dataframe(dataset_id))
    except Exception as exc:
        raise map_app_error(exc) from exc


@router.get("/{dataset_id}/regional")
def regional_intelligence(dataset_id: str):
    try:
        df = load_dataset_dataframe(dataset_id)
        theme = theme_manager.get_theme()
        regional = regional_analytics(df)
        return {**regional, "map_charts": generate_geo_chart_specs(df, theme.name)}
    except Exception as exc:
        raise map_app_error(exc) from exc
