import re

import pandas as pd


def normalize_column_name(column: str) -> str:
    """Convert column names into stable snake_case identifiers."""
    column = str(column).strip().lower()
    column = re.sub(r"[^a-z0-9]+", "_", column)
    column = re.sub(r"_+", "_", column).strip("_")
    return column or "unnamed_column"


def make_unique_columns(columns: list[str]) -> list[str]:
    """Prevent duplicate column names after normalization."""
    seen: dict[str, int] = {}
    unique_columns: list[str] = []

    for column in columns:
        if column not in seen:
            seen[column] = 0
            unique_columns.append(column)
        else:
            seen[column] += 1
            unique_columns.append(f"{column}_{seen[column]}")

    return unique_columns


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Basic safe cleaning for MVP analytics."""
    cleaned = df.copy()

    cleaned.columns = make_unique_columns([normalize_column_name(col) for col in cleaned.columns])

    # Remove fully empty rows and columns only. Do not guess-fill user data in MVP.
    cleaned = cleaned.dropna(axis=0, how="all")
    cleaned = cleaned.dropna(axis=1, how="all")

    # Trim strings while preserving missing values.
    object_columns = cleaned.select_dtypes(include=["object"]).columns
    for column in object_columns:
        cleaned[column] = cleaned[column].map(lambda value: value.strip() if isinstance(value, str) else value)

    return cleaned
