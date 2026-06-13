from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from backend.core.config import settings
from backend.processing.column_detector import detect_column_types
from backend.services.dataset_service import load_dataset_dataframe
from backend.utils.response_utils import to_json_safe


TABLE_NAME = "dataset"
BLOCKED_SQL = re.compile(r"\b(insert|update|delete|drop|alter|create|replace|truncate|attach|detach|pragma)\b", re.I)


def _read_store() -> list[dict[str, Any]]:
    if not settings.SQL_QUERIES_FILE.exists():
        return []
    try:
        return json.loads(settings.SQL_QUERIES_FILE.read_text(encoding="utf-8") or "[]")
    except json.JSONDecodeError:
        return []


def _write_store(rows: list[dict[str, Any]]) -> None:
    settings.SQL_QUERIES_FILE.parent.mkdir(parents=True, exist_ok=True)
    settings.SQL_QUERIES_FILE.write_text(json.dumps(rows[-100:], indent=2), encoding="utf-8")


def _validate_sql(sql: str) -> str:
    cleaned = sql.strip().rstrip(";")
    if not cleaned:
        raise ValueError("SQL query is empty.")
    if not re.match(r"^(select|with)\b", cleaned, flags=re.I):
        raise ValueError("Only SELECT or WITH queries are allowed.")
    if BLOCKED_SQL.search(cleaned):
        raise ValueError("Only read-only analytical SQL is allowed.")
    return cleaned


def _connection(df: pd.DataFrame) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    df.to_sql(TABLE_NAME, conn, index=False, if_exists="replace")
    return conn


def execute_sql(dataset_id: str, sql: str, limit: int = 100) -> dict[str, Any]:
    cleaned = _validate_sql(sql)
    limit = max(1, min(int(limit or 100), 1000))
    df = load_dataset_dataframe(dataset_id)
    limited_sql = f"SELECT * FROM ({cleaned}) LIMIT {limit}"
    with _connection(df) as conn:
        try:
            result = pd.read_sql_query(limited_sql, conn)
        except Exception as exc:
            raise ValueError(f"SQL error: {exc}") from exc

    rows = [{key: to_json_safe(value) for key, value in row.items()} for row in result.to_dict(orient="records")]
    history = _read_store()
    history.append(
        {
            "type": "history",
            "dataset_id": dataset_id,
            "sql": cleaned,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "row_count": len(rows),
        }
    )
    _write_store(history)
    return {
        "sql": cleaned,
        "columns": list(result.columns),
        "rows": rows,
        "row_count": len(rows),
        "limited": len(rows) >= limit,
        "error": "",
    }


def sql_templates(dataset_id: str) -> list[dict[str, str]]:
    df = load_dataset_dataframe(dataset_id)
    column_types = detect_column_types(df)
    numeric = column_types["numeric_columns"]
    categorical = column_types["categorical_columns"]
    templates = [{"name": "Preview rows", "sql": f"SELECT * FROM {TABLE_NAME} LIMIT 20"}]
    if numeric:
        templates.append({"name": f"Total {numeric[0]}", "sql": f'SELECT SUM("{numeric[0]}") AS total_{numeric[0]} FROM {TABLE_NAME}'})
    if numeric and categorical:
        templates.append(
            {
                "name": f"Top {categorical[0]} by {numeric[0]}",
                "sql": (
                    f'SELECT "{categorical[0]}", SUM("{numeric[0]}") AS total '
                    f"FROM {TABLE_NAME} GROUP BY \"{categorical[0]}\" ORDER BY total DESC LIMIT 10"
                ),
            }
        )
    return templates


def _quote_identifier(column: str) -> str:
    return f'"{column.replace(chr(34), chr(34) + chr(34))}"'


def _quote_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _numeric_filter(prompt: str, column: str) -> str | None:
    readable = column.lower().replace("_", " ")
    pattern = rf"(?:{re.escape(readable)}\s*)?(>=|<=|>|<|=)?\s*(\d+(?:\.\d+)?)"
    if readable not in prompt.lower() and column.lower() not in {"age"}:
        return None
    match = re.search(pattern, prompt.lower())
    if not match:
        return None
    operator = match.group(1)
    value = match.group(2)
    if operator:
        return f"{_quote_identifier(column)} {operator} {value}"
    if any(term in prompt.lower() for term in [f"{readable} above", f"{readable} over", f"{readable} greater", f"{readable} 60+", "above", "over", "older"]):
        return f"{_quote_identifier(column)} >= {value}"
    return f"{_quote_identifier(column)} = {value}"


def _categorical_filters(df: pd.DataFrame, prompt: str, categorical_columns: list[str]) -> list[str]:
    filters = []
    lowered = prompt.lower()
    used_columns: set[str] = set()
    for column in categorical_columns:
        values = df[column].dropna().astype(str).drop_duplicates().head(500).tolist()
        for value in values:
            value_text = value.lower()
            if len(value_text) < 2:
                continue
            if re.search(rf"\b{re.escape(value_text)}\b", lowered) and column not in used_columns:
                filters.append(f"LOWER(CAST({_quote_identifier(column)} AS TEXT)) = {_quote_literal(value_text)}")
                used_columns.add(column)
                break
    return filters


def _filter_conditions(df: pd.DataFrame, prompt: str, numeric_columns: list[str], categorical_columns: list[str]) -> list[str]:
    conditions = []
    for column in numeric_columns:
        condition = _numeric_filter(prompt, column)
        if condition:
            conditions.append(condition)
    conditions.extend(_categorical_filters(df, prompt, categorical_columns))
    return conditions


def generate_sql(dataset_id: str, prompt: str) -> dict[str, Any]:
    df = load_dataset_dataframe(dataset_id)
    column_types = detect_column_types(df)
    numeric = column_types["numeric_columns"]
    categorical = column_types["categorical_columns"]
    q = prompt.lower()
    metric = next((column for column in numeric if column.lower().replace("_", " ") in q), numeric[0] if numeric else None)
    dimension = next((column for column in categorical if column.lower().replace("_", " ") in q), categorical[0] if categorical else None)
    limit_match = re.search(r"top\s+(\d+)", q)
    limit = int(limit_match.group(1)) if limit_match else 10
    filters = _filter_conditions(df, prompt, numeric, categorical)
    where_clause = f" WHERE {' AND '.join(filters)}" if filters else ""

    if ("top" in q or "highest" in q or "best" in q) and metric and dimension:
        sql = (
            f'SELECT "{dimension}", SUM("{metric}") AS total_{metric} '
            f"FROM {TABLE_NAME}{where_clause} GROUP BY \"{dimension}\" ORDER BY total_{metric} DESC LIMIT {limit}"
        )
    elif ("average" in q or "mean" in q) and metric:
        sql = f'SELECT AVG("{metric}") AS average_{metric} FROM {TABLE_NAME}{where_clause}'
    elif ("total" in q or "sum" in q) and metric:
        sql = f'SELECT SUM("{metric}") AS total_{metric} FROM {TABLE_NAME}{where_clause}'
    elif filters:
        sql = f"SELECT * FROM {TABLE_NAME}{where_clause} LIMIT {limit}"
    else:
        sql = f"SELECT * FROM {TABLE_NAME} LIMIT {limit}"

    return {
        "prompt": prompt,
        "sql": sql,
        "explanation": explain_sql(sql),
        "confidence": "high" if filters else "medium" if metric or dimension else "low",
        "detected_filters": filters,
    }


def explain_sql(sql: str) -> str:
    cleaned = sql.strip()
    explanation = ["This read-only query analyzes the uploaded dataset table."]
    if re.search(r"\bgroup\s+by\b", cleaned, re.I):
        explanation.append("It groups records by one or more dimensions.")
    if re.search(r"\border\s+by\b", cleaned, re.I):
        explanation.append("It sorts the result to highlight ranked performance.")
    if re.search(r"\blimit\b", cleaned, re.I):
        explanation.append("It limits returned rows for preview performance.")
    if any(fn in cleaned.lower() for fn in ["sum(", "avg(", "count(", "min(", "max("]):
        explanation.append("It uses aggregate calculations to produce business metrics.")
    return " ".join(explanation)


def optimize_sql(sql: str) -> dict[str, str]:
    cleaned = _validate_sql(sql)
    suggestions = []
    optimized = cleaned
    if "limit" not in cleaned.lower():
        optimized = f"{cleaned} LIMIT 100"
        suggestions.append("Added LIMIT 100 to keep workbench previews responsive.")
    if "select *" in cleaned.lower():
        suggestions.append("For production reports, select only the columns needed by the visual or analysis.")
    return {"sql": optimized, "suggestions": " ".join(suggestions) or "Query is already suitable for preview use."}


def detect_sql_errors(sql: str) -> dict[str, Any]:
    try:
        _validate_sql(sql)
    except ValueError as exc:
        return {"valid": False, "error": str(exc)}
    return {"valid": True, "error": ""}


def list_sql_history(dataset_id: str) -> dict[str, Any]:
    rows = [row for row in _read_store() if row.get("dataset_id") == dataset_id]
    return {
        "history": [row for row in rows if row.get("type") == "history"][-25:],
        "saved_queries": [row for row in rows if row.get("type") == "saved"],
    }


def save_sql_query(dataset_id: str, name: str, sql: str) -> dict[str, Any]:
    cleaned = _validate_sql(sql)
    rows = _read_store()
    record = {
        "type": "saved",
        "dataset_id": dataset_id,
        "name": name,
        "sql": cleaned,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    rows.append(record)
    _write_store(rows)
    return record
