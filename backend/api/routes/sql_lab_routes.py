from fastapi import APIRouter

from backend.api.deps import map_app_error
from backend.models.sql_lab_models import NaturalLanguageSqlRequest, SavedSqlQueryRequest, SqlQueryRequest, SqlQueryResponse
from backend.services.sql_lab_service import (
    detect_sql_errors,
    execute_sql,
    explain_sql,
    generate_sql,
    list_sql_history,
    optimize_sql,
    save_sql_query,
    sql_templates,
)

router = APIRouter(prefix="/sql-lab", tags=["SQL Lab"])


@router.get("/{dataset_id}/templates")
def templates(dataset_id: str):
    try:
        return {"templates": sql_templates(dataset_id)}
    except Exception as exc:
        raise map_app_error(exc) from exc


@router.get("/{dataset_id}/history")
def history(dataset_id: str):
    try:
        return list_sql_history(dataset_id)
    except Exception as exc:
        raise map_app_error(exc) from exc


@router.post("/{dataset_id}/query", response_model=SqlQueryResponse)
def query(dataset_id: str, payload: SqlQueryRequest):
    try:
        return execute_sql(dataset_id, payload.sql, payload.limit)
    except Exception as exc:
        raise map_app_error(exc) from exc


@router.post("/{dataset_id}/generate")
def generate(dataset_id: str, payload: NaturalLanguageSqlRequest):
    try:
        return generate_sql(dataset_id, payload.prompt)
    except Exception as exc:
        raise map_app_error(exc) from exc


@router.post("/{dataset_id}/save")
def save_query(dataset_id: str, payload: SavedSqlQueryRequest):
    try:
        return save_sql_query(dataset_id, payload.name, payload.sql)
    except Exception as exc:
        raise map_app_error(exc) from exc


@router.post("/explain")
def explain(payload: SqlQueryRequest):
    try:
        return {"explanation": explain_sql(payload.sql)}
    except Exception as exc:
        raise map_app_error(exc) from exc


@router.post("/optimize")
def optimize(payload: SqlQueryRequest):
    try:
        return optimize_sql(payload.sql)
    except Exception as exc:
        raise map_app_error(exc) from exc


@router.post("/detect-errors")
def detect_errors(payload: SqlQueryRequest):
    try:
        return detect_sql_errors(payload.sql)
    except Exception as exc:
        raise map_app_error(exc) from exc
