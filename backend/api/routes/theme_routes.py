from fastapi import APIRouter

from backend.api.deps import map_app_error
from backend.core.theme_manager import theme_manager
from backend.models.theme_models import ThemeListResponse, ThemeResponse

router = APIRouter(prefix="/themes", tags=["Themes"])


@router.get("", response_model=ThemeListResponse)
def list_themes():
    return {
        "active_theme": theme_manager.active_name(),
        "themes": theme_manager.list_themes(),
    }


@router.get("/active", response_model=ThemeResponse)
def active_theme():
    return theme_manager.get_theme().to_dict()


@router.post("/active/{theme_name}", response_model=ThemeResponse)
def set_active_theme(theme_name: str):
    try:
        return theme_manager.set_active(theme_name).to_dict()
    except Exception as exc:
        raise map_app_error(exc) from exc
