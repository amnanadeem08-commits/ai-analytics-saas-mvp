from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable

import pandas as pd


@dataclass(frozen=True)
class BusinessColumnRecipe:
    # Public identifiers
    target_column: str
    display_name: str
    description: str

    # Dependency specification (case-insensitive matching against df.columns)
    required_columns: tuple[str, ...] = ()
    optional_columns: tuple[str, ...] = ()

    # Deterministic behavior only (given a df, formula returns a Series of same length)
    # The formula receives df and a dict mapping "normalized" recipe column keys to actual df columns.
    formula: Callable[[pd.DataFrame, dict[str, str]], pd.Series] | None = None


def _normalize_col(col: str) -> str:
    return str(col).strip().lower()


def _available_column_map(df: pd.DataFrame) -> dict[str, str]:
    # Map normalized name -> actual name (if duplicates exist, keep the first)
    mapping: dict[str, str] = {}
    for c in df.columns:
        key = _normalize_col(c)
        if key not in mapping:
            mapping[key] = c
    return mapping


def _has_any_column(df: pd.DataFrame, candidates: Iterable[str]) -> bool:
    mapping = _available_column_map(df)
    return any(_normalize_col(c) in mapping for c in candidates)


def _get_column_if_present(mapping: dict[str, str], candidates: Iterable[str]) -> str | None:
    for c in candidates:
        key = _normalize_col(c)
        if key in mapping:
            return mapping[key]
    return None


def _bins_for_age_group(age_series: pd.Series) -> pd.Series:
    # Deterministic age bins for numeric ages.
    # Labels are stable and do not require external knowledge.
    bins = [-float("inf"), 17, 24, 34, 44, 54, float("inf")]
    labels = ["<18", "18-24", "25-34", "35-44", "45-54", "55+"]
    return pd.cut(age_series, bins=bins, labels=labels, include_lowest=True).astype("string")


def _safe_numeric(df: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_numeric(df[col], errors="coerce")


def _formula_revenue(df: pd.DataFrame, m: dict[str, str]) -> pd.Series:
    # Revenue: deterministic only if (sales and quantity) or (revenue exists already -> no suggestion).
    # We only run this formula when required columns exist in detection.
    sales_col = _get_column_if_present(m, ("sales", "revenue_sales"))
    qty_col = _get_column_if_present(m, ("quantity", "qty", "units"))
    if not sales_col or not qty_col:
        raise ValueError("Missing required sales/quantity inputs for revenue recipe.")
    return _safe_numeric(df, sales_col) * _safe_numeric(df, qty_col)


def _formula_profit(df: pd.DataFrame, m: dict[str, str]) -> pd.Series:
    revenue_col = _get_column_if_present(m, ("revenue", "sales", "revenue_sales"))
    # For profit we require either explicit profit-like, or cost-like to compute.
    # We'll compute as revenue - cost/expenses if cost-like exists.
    cost_col = _get_column_if_present(m, ("cost", "expense", "expenses", "operating_cost", "cogs"))
    if not revenue_col or not cost_col:
        raise ValueError("Missing required inputs for profit recipe.")
    return _safe_numeric(df, revenue_col) - _safe_numeric(df, cost_col)


def _formula_margin_pct(df: pd.DataFrame, m: dict[str, str]) -> pd.Series:
    # Margin %: profit / revenue * 100. Deterministic with explicit required columns.
    revenue_col = _get_column_if_present(m, ("revenue", "sales", "revenue_sales"))
    profit_col = _get_column_if_present(m, ("profit",))
    if not revenue_col or not profit_col:
        raise ValueError("Missing required inputs for margin recipe.")
    revenue = _safe_numeric(df, revenue_col)
    profit = _safe_numeric(df, profit_col)

    out = pd.Series([pd.NA] * len(df), index=df.index, dtype="Float64")
    mask = revenue.notna() & (revenue != 0)
    out.loc[mask] = (profit.loc[mask] / revenue.loc[mask]) * 100
    return out


def _formula_age_group(df: pd.DataFrame, m: dict[str, str]) -> pd.Series:
    age_col = _get_column_if_present(m, ("age", "years_old"))
    if not age_col:
        raise ValueError("Missing age column for age group recipe.")
    age = _safe_numeric(df, age_col)
    return _bins_for_age_group(age)


def _formula_risk_category(df: pd.DataFrame, m: dict[str, str]) -> pd.Series:
    risk_col = _get_column_if_present(m, ("risk", "risk_score", "risk score"))
    if not risk_col:
        raise ValueError("Missing risk score column for risk category recipe.")
    score = _safe_numeric(df, risk_col)
    # Deterministic ranges:
    # <0.33 = Low, 0.33-0.66 = Medium, >0.66 = High when score in [0,1]
    # If score looks like 0-100, normalize heuristically by dividing by 100.
    # IMPORTANT: this is still deterministic given the provided column values.
    # We do NOT infer missing columns; only transform existing values.
    norm = score.copy()
    # If max score looks like 100-ish, normalize.
    try:
        max_val = float(score.max(skipna=True))
    except Exception:
        max_val = 0.0
    if max_val > 1.5:
        norm = norm / 100.0

    out = pd.Series(pd.NA, index=df.index, dtype="string")
    out.loc[norm.lt(0.33)] = "Low"
    out.loc[norm.ge(0.33) & norm.le(0.66)] = "Medium"
    out.loc[norm.gt(0.66)] = "High"
    return out


def _formula_requirements(df: pd.DataFrame, m: dict[str, str]) -> pd.Series:
    # Requirements: deterministic only if there's an explicit requirements-like column.
    req_col = _get_column_if_present(m, ("requirements", "required", "requested_features", "requirements_list"))
    if not req_col:
        raise ValueError("Missing requirements column for requirements recipe.")
    return df[req_col].astype("string")


def _build_recipe_registry() -> list[BusinessColumnRecipe]:
    # Target columns must not exist to be suggested.
    # Required columns specify the existence checks for those inputs.
    # Note: formulas are deterministic and depend ONLY on detected source columns.
    return [
        BusinessColumnRecipe(
            target_column="Revenue",
            display_name="Revenue",
            description="Calculated revenue (Sales * Quantity) when both inputs exist.",
            required_columns=("sales", "quantity"),
            formula=_formula_revenue,
        ),
        BusinessColumnRecipe(
            target_column="Profit",
            display_name="Profit",
            description="Calculated profit (Revenue - Cost/Expenses) when both inputs exist.",
            required_columns=("revenue", "cost"),
            optional_columns=("sales", "expenses"),  # alternative names handled by formula lookup
            formula=_formula_profit,
        ),
        BusinessColumnRecipe(
            target_column="Margin %",
            display_name="Margin %",
            description="Profit margin percentage (Profit / Revenue * 100) when both inputs exist.",
            required_columns=("profit", "revenue"),
            formula=_formula_margin_pct,
        ),
        BusinessColumnRecipe(
            target_column="Age Group",
            display_name="Age Group",
            description="Age bucket label derived from the Age column.",
            required_columns=("age",),
            formula=_formula_age_group,
        ),
        BusinessColumnRecipe(
            target_column="Risk Category",
            display_name="Risk Category",
            description="Deterministic Low/Medium/High label derived from risk score.",
            required_columns=("risk_score",),
            optional_columns=("risk", "risk score"),
            formula=_formula_risk_category,
        ),
        BusinessColumnRecipe(
            target_column="Requirements",
            display_name="Requirements",
            description="Normalized Requirements text from the first requirements-like column.",
            required_columns=("requirements",),
            optional_columns=("requested_features", "requirements_list"),
            formula=_formula_requirements,
        ),
    ]


RECIPE_REGISTRY: list[BusinessColumnRecipe] = _build_recipe_registry()


def detect_available_recipes(df: pd.DataFrame) -> list[dict[str, Any]]:
    """
    Returns suggestion objects without mutating df.
    Each suggestion includes:
      - recipe
      - depends_on_columns: the actual df column names used for each required/optional key
      - target_column
    """
    mapping = _available_column_map(df)
    # Existing-target protection must be exact (case-sensitive) to avoid treating
    # source columns like `revenue` / `profit` as calculated targets `Revenue` / `Profit`.
    existing_targets = set(df.columns)

    suggestions: list[dict[str, Any]] = []

    def _resolve_any_columns(candidates: tuple[str, ...]) -> list[str]:
        resolved: list[str] = []
        for c in candidates:
            key = _normalize_col(c)
            if key in mapping:
                resolved.append(mapping[key])
        return resolved

    for recipe in RECIPE_REGISTRY:
        if recipe.target_column in existing_targets:
            continue

        # Dependency validation:
        # - required_columns must all exist (case-insensitive)
        # - optional_columns may exist, but are not required for suggestion
        required_present_actual: dict[str, str] = {}
        ok = True
        for req in recipe.required_columns:
            req_norm = _normalize_col(req)
            if req_norm not in mapping:
                ok = False
                break
            required_present_actual[req_norm] = mapping[req_norm]
        if not ok:
            continue

        depends_on = [required_present_actual[_normalize_col(req)] for req in recipe.required_columns if _normalize_col(req) in required_present_actual]

        # Note: we do NOT require optional columns; they are handled inside formulas
        # using whichever alternate names are actually present.
        suggestions.append(
            {
                "target_column": recipe.target_column,
                "display_name": recipe.display_name,
                "description": recipe.description,
                "depends_on_columns": depends_on + _resolve_any_columns(recipe.optional_columns),
                "recipe": recipe,
            }
        )

    return suggestions


def generate_preview_rows(df: pd.DataFrame, recipe: BusinessColumnRecipe, preview_rows: int = 10) -> list[dict[str, Any]]:
    mapping = _available_column_map(df)
    if not recipe.formula:
        raise ValueError("Recipe has no formula.")

    series = recipe.formula(df, mapping)
    # Only preview values (no mutation)
    out_df = pd.DataFrame({recipe.target_column: series})
    # head values; keep it deterministic and simple
    head = out_df.head(preview_rows)
    return [{recipe.target_column: val} for val in head[recipe.target_column].tolist()]


def create_business_columns(df: pd.DataFrame, selected_recipes: list[BusinessColumnRecipe]) -> pd.DataFrame:
    """
    Returns a new df copy with selected calculated columns added.
    Never overwrites existing target columns.
    """
    # Exact (case-sensitive) protection; do not normalize because recipe targets are canonical.
    existing_targets = set(df.columns)
    out = df.copy()

    mapping = _available_column_map(out)
    for recipe in selected_recipes:
        if recipe.target_column in existing_targets:
            continue
        if not recipe.formula:
            continue
        out[recipe.target_column] = recipe.formula(out, mapping)

    return out


def recipe_by_target(target_column: str) -> BusinessColumnRecipe | None:
    target_norm = _normalize_col(target_column)
    for r in RECIPE_REGISTRY:
        if _normalize_col(r.target_column) == target_norm:
            return r
    return None
