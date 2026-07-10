from fastapi import APIRouter

from backend.api.deps import map_app_error
from backend.models.dax_models import DaxFormula, DaxPrompt
from backend.services.dax_service import dax_library, detect_dax_errors, explain_dax, generate_dax, optimize_dax, optimize_dataset_dax

router = APIRouter(prefix="/dax", tags=["DAX Studio"])


@router.get("/{dataset_id}/library")
def library(dataset_id: str):
    try:
        return dax_library(dataset_id)
    except Exception as exc:
        raise map_app_error(exc) from exc


@router.post("/{dataset_id}/generate")
def generate(dataset_id: str, payload: DaxPrompt):
    try:
        return generate_dax(dataset_id, payload.prompt)
    except Exception as exc:
        raise map_app_error(exc) from exc


@router.post("/explain")
def explain(payload: DaxFormula):
    try:
        return {"explanation": explain_dax(payload.dax)}
    except Exception as exc:
        raise map_app_error(exc) from exc


@router.post("/optimize")
def optimize(payload: DaxFormula):
    try:
        return optimize_dax(payload.dax)
    except Exception as exc:
        raise map_app_error(exc) from exc


@router.post("/{dataset_id}/optimize")
def optimize_for_dataset(dataset_id: str, payload: DaxFormula):
    try:
        return optimize_dataset_dax(dataset_id, payload.dax)
    except Exception as exc:
        raise map_app_error(exc) from exc


@router.post("/detect-errors")
def detect_errors(payload: DaxFormula):
    try:
        return detect_dax_errors(payload.dax)
    except Exception as exc:
        raise map_app_error(exc) from exc
