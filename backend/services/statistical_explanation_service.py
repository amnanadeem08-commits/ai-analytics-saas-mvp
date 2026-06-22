from __future__ import annotations

from typing import Iterable

import pandas as pd


def _distribution_note(series: pd.Series) -> str:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if len(clean) < 8:
        return ""
    skew = float(clean.skew())
    if skew > 1:
        return " Distribution is right-skewed, so the median may be more representative than the mean."
    if skew < -1:
        return " Distribution is left-skewed, so the median may be more representative than the mean."
    return ""


def build_kpi_explanation(
    *,
    label: str,
    formula: str,
    sample_size: int,
    uses_sample: bool = False,
    is_rate: bool = False,
    series: pd.Series | None = None,
) -> str:
    scope = "sample" if uses_sample else "full dataset"
    explanation = f"{label} measures {formula}. This value is computed on the {scope} (n={sample_size})."
    if is_rate and sample_size < 30:
        explanation += " The sample size is small, so this percentage has higher uncertainty."
    if series is not None:
        explanation += _distribution_note(series)
    return explanation


def build_chart_explanation(
    *,
    chart_type: str,
    columns: Iterable[str],
    sample_size: int,
    formula: str,
) -> str:
    cols = ", ".join(columns)
    base = (
        f"This {chart_type.replace('_', ' ')} chart uses {cols} and summarizes {formula} "
        f"with n={sample_size} records."
    )
    if chart_type in {"scatter", "heatmap"}:
        return base + " The relationship shown is associative and should not be interpreted as causal."
    return base
