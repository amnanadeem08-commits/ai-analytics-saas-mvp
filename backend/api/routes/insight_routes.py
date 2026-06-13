from fastapi import APIRouter

from backend.api.deps import map_app_error
from backend.models.insight_models import InsightResponse, QuestionRequest, QuestionResponse
from backend.services.insight_service import ask_question, get_decision_framework, get_insights

router = APIRouter(prefix="/insights", tags=["Insights"])


@router.get("/{dataset_id}", response_model=InsightResponse)
def dataset_insights(dataset_id: str):
    try:
        return get_insights(dataset_id)
    except Exception as exc:
        raise map_app_error(exc) from exc


@router.get("/{dataset_id}/decision-framework")
def dataset_decision_framework(dataset_id: str):
    try:
        return get_decision_framework(dataset_id)
    except Exception as exc:
        raise map_app_error(exc) from exc


@router.post("/{dataset_id}/ask", response_model=QuestionResponse)
def ask_dataset_question(dataset_id: str, payload: QuestionRequest):
    try:
        return ask_question(dataset_id, payload.question)
    except Exception as exc:
        raise map_app_error(exc) from exc
