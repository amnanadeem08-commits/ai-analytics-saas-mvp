from fastapi import APIRouter

from backend.api.deps import map_app_error
from backend.core.theme_manager import theme_manager

router = APIRouter(prefix="/themes", tags=["Themes"])


@router.get("")
def list_themes():
    return {
        "active_theme": theme_manager.active_name(),
        "themes": theme_manager.list_themes(),
    }


@router.get("/active")
def active_theme():
    return theme_manager.get_theme().to_dict()


@router.post("/active/{theme_name}")
def set_active_theme(theme_name: str):
    try:
        return theme_manager.set_active(theme_name).to_dict()
    except Exception as exc:
        raise map_app_error(exc) from exc
