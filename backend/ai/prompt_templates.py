from __future__ import annotations

from collections.abc import Iterable

HEALTH_ANALYST_PROMPT = """
You are a healthcare analytics analyst. Interpret the dataset cautiously, focus on population-level patterns, data quality, risk indicators, and evidence-backed operational recommendations. Do not provide medical diagnosis or treatment advice.
""".strip()

BUSINESS_ANALYST_PROMPT = """
You are a business analytics analyst. Interpret the dataset through revenue, customer, sales, churn, operations, and executive decision-making context. Focus on evidence, KPI meaning, risks, opportunities, and practical recommendations.
""".strip()

FINANCE_ANALYST_PROMPT = """
You are a finance analytics analyst. Interpret the dataset through market, price, volume, profitability, cost, risk, and financial performance context. Focus on evidence-backed financial signals and decision implications.
""".strip()

GENERAL_ANALYST_PROMPT = """
You are a general analytics analyst. Interpret the dataset using validated evidence, data quality context, statistically responsible summaries, and practical next-step recommendations.
""".strip()

DATASET_INSIGHT_PROMPT_TEMPLATE = """
{system_prompt}

Dataset profile:
{dataset_profile}

Question:
{question}
"""


def detect_prompt_domain(columns: Iterable[object]) -> str:
    cols = {str(column).lower().replace("_", " ") for column in columns}
    joined = " ".join(cols)

    if any(signal in joined for signal in ["heart", "bp", "blood", "glucose", "insulin", "bmi", "diagnosis", "health", "patient", "medical"]):
        return "health"
    if any(signal in joined for signal in ["revenue", "profit", "sales", "customer", "churn", "order", "product"]):
        return "business"
    if any(signal in joined for signal in ["stock", "price", "volume", "market", "cash", "margin", "invoice"]):
        return "finance"
    return "general"


def select_analyst_prompt(columns: Iterable[object]) -> str:
    domain = detect_prompt_domain(columns)
    if domain == "health":
        return HEALTH_ANALYST_PROMPT
    if domain == "business":
        return BUSINESS_ANALYST_PROMPT
    if domain == "finance":
        return FINANCE_ANALYST_PROMPT
    return GENERAL_ANALYST_PROMPT


def build_dataset_insight_prompt(dataset_profile: str, question: str, columns: Iterable[object]) -> str:
    return DATASET_INSIGHT_PROMPT_TEMPLATE.format(
        system_prompt=select_analyst_prompt(columns),
        dataset_profile=dataset_profile,
        question=question,
    )
