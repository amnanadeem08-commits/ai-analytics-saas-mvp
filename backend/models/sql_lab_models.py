from typing import Any

from pydantic import BaseModel


class SqlQueryRequest(BaseModel):
    sql: str
    limit: int = 100


class NaturalLanguageSqlRequest(BaseModel):
    prompt: str


class SavedSqlQueryRequest(BaseModel):
    name: str
    sql: str


class SqlQueryResponse(BaseModel):
    sql: str
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    limited: bool
    error: str = ""


class SqlTemplateResponse(BaseModel):
    templates: list[dict[str, str]]
