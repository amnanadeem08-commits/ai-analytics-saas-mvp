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


def _formula_tenure_band(df: pd.DataFrame, m: dict[str, str]) -> pd.Series:
    tenure_col = _get_column_if_present(m, ("tenure", "tenure_months", "customer_tenure"))
    if not tenure_col:
        raise ValueError("Missing tenure column for tenure band recipe.")
    tenure = _safe_numeric(df, tenure_col)
    bins = [-float("inf"), 6, 12, 24, float("inf")]
    labels = ["New", "Early", "Established", "Loyal"]
    return pd.cut(tenure, bins=bins, labels=labels, include_lowest=True).astype("string")


def _formula_revenue_band(df: pd.DataFrame, m: dict[str, str]) -> pd.Series:
    revenue_col = _get_column_if_present(m, ("monthly_charges", "monthly_revenue", "revenue", "sales"))
    if not revenue_col:
        raise ValueError("Missing revenue-like column for revenue band recipe.")
    values = _safe_numeric(df, revenue_col)
    valid = values.dropna()
    if valid.empty:
        return pd.Series(pd.NA, index=df.index, dtype="string")
    q1 = float(valid.quantile(0.33))
    q2 = float(valid.quantile(0.66))
    out = pd.Series(pd.NA, index=df.index, dtype="string")
    out.loc[values.le(q1)] = "Low"
    out.loc[values.gt(q1) & values.le(q2)] = "Medium"
    out.loc[values.gt(q2)] = "High"
    return out


def _formula_loyalty_tier(df: pd.DataFrame, m: dict[str, str]) -> pd.Series:
    tenure_col = _get_column_if_present(m, ("tenure", "tenure_months", "customer_tenure"))
    if not tenure_col:
        raise ValueError("Missing tenure column for loyalty tier recipe.")
    tenure = _safe_numeric(df, tenure_col)
    bins = [-float("inf"), 6, 12, 24, float("inf")]
    labels = ["Bronze", "Silver", "Gold", "Platinum"]
    return pd.cut(tenure, bins=bins, labels=labels, include_lowest=True).astype("string")


def _formula_high_value_customer(df: pd.DataFrame, m: dict[str, str]) -> pd.Series:
    revenue_col = _get_column_if_present(m, ("monthly_charges", "monthly_revenue", "revenue", "sales"))
    if not revenue_col:
        raise ValueError("Missing revenue-like column for high value recipe.")
    values = _safe_numeric(df, revenue_col)
    threshold = float(values.dropna().quantile(0.75)) if not values.dropna().empty else 0.0
    out = pd.Series(pd.NA, index=df.index, dtype="string")
    out.loc[values.ge(threshold)] = "Yes"
    out.loc[values.lt(threshold)] = "No"
    return out


def _formula_contract_category(df: pd.DataFrame, m: dict[str, str]) -> pd.Series:
    contract_col = _get_column_if_present(m, ("contract_type", "contract"))
    if not contract_col:
        raise ValueError("Missing contract column for contract category recipe.")
    return df[contract_col].astype("string")


def _formula_payment_risk(df: pd.DataFrame, m: dict[str, str]) -> pd.Series:
    payment_col = _get_column_if_present(m, ("payment_method", "payment", "payment_type"))
    if not payment_col:
        raise ValueError("Missing payment method column for payment risk recipe.")
    text = df[payment_col].astype("string").str.lower().fillna("")
    out = pd.Series("Medium", index=df.index, dtype="string")
    out.loc[text.str.contains("electronic|credit|debit|auto", regex=True)] = "High"
    out.loc[text.str.contains("bank transfer|bank|wire", regex=True)] = "Low"
    out.loc[text.str.contains("mailed|cash|check", regex=True)] = "Medium"
    return out


def _formula_churn_risk(df: pd.DataFrame, m: dict[str, str]) -> pd.Series:
    churn_col = _get_column_if_present(m, ("churn", "churned", "is_churn"))
    tenure_col = _get_column_if_present(m, ("tenure", "tenure_months", "customer_tenure"))
    revenue_col = _get_column_if_present(m, ("monthly_charges", "monthly_revenue", "revenue"))
    if not churn_col:
        raise ValueError("Missing churn column for churn risk recipe.")

    churn_text = df[churn_col].astype("string").str.lower().fillna("")
    out = pd.Series("Medium", index=df.index, dtype="string")
    out.loc[churn_text.str.contains("yes|true|1|churned|left", regex=True)] = "High"

    if tenure_col:
        tenure = _safe_numeric(df, tenure_col)
        out.loc[tenure.le(6) & out.ne("High")] = "High"
        out.loc[tenure.ge(24) & out.ne("High")] = "Low"

    if revenue_col:
        values = _safe_numeric(df, revenue_col)
        threshold = float(values.dropna().quantile(0.75)) if not values.dropna().empty else 0.0
        out.loc[values.ge(threshold) & out.eq("High")] = "Critical"

    return out


def _formula_customer_segment(df: pd.DataFrame, m: dict[str, str]) -> pd.Series:
    tenure_col = _get_column_if_present(m, ("tenure", "tenure_months", "customer_tenure"))
    revenue_col = _get_column_if_present(m, ("monthly_charges", "monthly_revenue", "revenue"))
    if not tenure_col or not revenue_col:
        raise ValueError("Missing tenure or revenue column for customer segment recipe.")
    tenure_band = _formula_tenure_band(df, m)
    revenue_band = _formula_revenue_band(df, m)
    return (revenue_band.fillna("Unknown") + "-" + tenure_band.fillna("Unknown")).astype("string")


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
        BusinessColumnRecipe(
            target_column="Tenure Band",
            display_name="Tenure Band",
            description="Customer tenure grouping for lifecycle analysis.",
            required_columns=("tenure",),
            optional_columns=("tenure_months", "customer_tenure"),
            formula=_formula_tenure_band,
        ),
        BusinessColumnRecipe(
            target_column="Revenue Band",
            display_name="Revenue Band",
            description="Revenue/charges stratification into low, medium, and high tiers.",
            required_columns=("monthly_charges",),
            optional_columns=("monthly_revenue", "revenue", "sales"),
            formula=_formula_revenue_band,
        ),
        BusinessColumnRecipe(
            target_column="Loyalty Tier",
            display_name="Loyalty Tier",
            description="Deterministic customer loyalty tier derived from tenure.",
            required_columns=("tenure",),
            optional_columns=("tenure_months", "customer_tenure"),
            formula=_formula_loyalty_tier,
        ),
        BusinessColumnRecipe(
            target_column="High Value Customer",
            display_name="High Value Customer",
            description="Flags customers in the top spend/revenue quartile.",
            required_columns=("monthly_charges",),
            optional_columns=("monthly_revenue", "revenue", "sales"),
            formula=_formula_high_value_customer,
        ),
        BusinessColumnRecipe(
            target_column="Contract Category",
            display_name="Contract Category",
            description="Normalized contract grouping for churn and retention analysis.",
            required_columns=("contract_type",),
            optional_columns=("contract",),
            formula=_formula_contract_category,
        ),
        BusinessColumnRecipe(
            target_column="Payment Risk",
            display_name="Payment Risk",
            description="Payment method risk categorization for churn review.",
            required_columns=("payment_method",),
            optional_columns=("payment", "payment_type"),
            formula=_formula_payment_risk,
        ),
        BusinessColumnRecipe(
            target_column="Churn Risk",
            display_name="Churn Risk",
            description="Composite churn risk indicator using churn status and account context.",
            required_columns=("churn",),
            optional_columns=("tenure", "monthly_charges", "monthly_revenue", "revenue"),
            formula=_formula_churn_risk,
        ),
        BusinessColumnRecipe(
            target_column="Customer Segment",
            display_name="Customer Segment",
            description="Segment label built from tenure and revenue bands.",
            required_columns=("tenure", "monthly_charges"),
            optional_columns=("tenure_months", "customer_tenure", "monthly_revenue", "revenue"),
            formula=_formula_customer_segment,
        ),
    ]


RECIPE_REGISTRY: list[BusinessColumnRecipe] = _build_recipe_registry()

DOMAIN_RECIPE_PRIORITIES: dict[str, tuple[str, ...]] = {
    "sales": ("Revenue", "Profit", "Margin %"),
    "customer churn": (
        "Churn Risk",
        "Customer Segment",
        "Revenue Band",
        "Tenure Band",
        "Loyalty Tier",
        "High Value Customer",
        "Contract Category",
        "Payment Risk",
        "Age Group",
    ),
    "telecom": (
        "Churn Risk",
        "Customer Segment",
        "Revenue Band",
        "Tenure Band",
        "Loyalty Tier",
        "High Value Customer",
        "Contract Category",
        "Payment Risk",
    ),
    "healthcare": ("Age Group", "Risk Category", "Requirements"),
    "finance": ("Profit", "Margin %", "Revenue", "Risk Category"),
    "retail": ("Revenue", "Profit", "Margin %"),
    "ecommerce": ("Revenue", "Profit", "Margin %"),
    "generic business dataset": (),
    "generic analytics": (),
}


def _domain_name(domain_context: dict[str, Any] | str | None) -> str:
    if isinstance(domain_context, str):
        return domain_context.strip().lower()
    if isinstance(domain_context, dict):
        for key in ("detected_domain", "domain"):
            value = domain_context.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip().lower()
        detection = domain_context.get("detection")
        if isinstance(detection, dict):
            value = detection.get("domain")
            if isinstance(value, str) and value.strip():
                return value.strip().lower()
        nested = domain_context.get("domain_context")
        if isinstance(nested, dict):
            value = nested.get("detected_domain")
            if isinstance(value, str) and value.strip():
                return value.strip().lower()
    return "generic business dataset"


def _priority_for_recipe(target: str, domain_name: str) -> int:
    preferred = DOMAIN_RECIPE_PRIORITIES.get(domain_name, ())
    if not preferred:
        return 99
    try:
        return preferred.index(target)
    except ValueError:
        return 99


def _domain_hint_text(target: str, domain_name: str) -> str:
    if domain_name in {"generic business dataset", "generic analytics"}:
        return ""
    prioritized = _priority_for_recipe(target, domain_name) < 99
    if prioritized:
        return f" Prioritized for {domain_name.title()} context."
    return f" Available for {domain_name.title()} context when source columns are present."


def detect_available_recipes(df: pd.DataFrame, domain_context: dict[str, Any] | str | None = None) -> list[dict[str, Any]]:
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

    domain_name = _domain_name(domain_context)
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
                "description": recipe.description + _domain_hint_text(recipe.target_column, domain_name),
                "depends_on_columns": depends_on + _resolve_any_columns(recipe.optional_columns),
                "domain_context": domain_name,
                "domain_priority": _priority_for_recipe(recipe.target_column, domain_name),
                "recipe": recipe,
            }
        )

    suggestions.sort(key=lambda item: (int(item.get("domain_priority", 99)), item.get("target_column", "")))
    return suggestions


def generate_domain_business_questions(domain_context: dict[str, Any] | str | None = None) -> list[str]:
    domain_name = _domain_name(domain_context)
    churn_questions = [
        "Which customers have high churn risk with high revenue impact?",
        "How does churn risk vary by contract category and payment risk?",
        "Which tenure bands need immediate retention campaigns?",
        "What share of high-value customers are at medium/high churn risk?",
        "Which customer segments should be prioritized for loyalty incentives?",
    ]
    sales_questions = [
        "Which regions drive the largest revenue and margin contribution?",
        "Where is margin erosion concentrated by product or segment?",
        "Which segments should receive immediate upsell focus?",
    ]
    healthcare_questions = [
        "Which cohorts show elevated clinical risk indicators?",
        "How do risk categories shift across age and diagnosis groups?",
        "Which population segment should be prioritized for intervention?",
    ]
    generic_questions = [
        "Which segments are driving the largest performance changes?",
        "What is the highest-priority risk in the current dataset?",
        "Which action would create the most immediate business value?",
    ]

    if domain_name in {"customer churn", "telecom"}:
        return churn_questions
    if domain_name == "sales":
        return sales_questions
    if domain_name == "healthcare":
        return healthcare_questions
    return generic_questions


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
