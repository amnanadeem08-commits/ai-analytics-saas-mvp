from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

import pandas as pd
import streamlit as st

SUPPORTED_DOMAINS = ("Sales", "Customer Churn", "Telecom", "Finance", "Retail", "Ecommerce", "Marketing", "HR", "Manufacturing", "Healthcare", "Banking", "Education", "Inventory", "CRM", "Customer Support", "Generic Business Dataset")

DOMAIN_SIGNALS: dict[str, tuple[str, ...]] = {
    "Sales": ("sales", "revenue", "order", "product", "region", "amount", "quota", "pipeline"),
    "Customer Churn": ("churn", "cancel", "retention", "tenure", "contract", "subscription", "left", "renewal"),
    "Telecom": ("call", "usage", "plan", "data", "minutes", "roaming", "contract", "subscriber"),
    "Finance": ("stock", "price", "volume", "market", "cash", "invoice", "expense", "budget", "asset", "liability", "portfolio", "return", "cost", "margin", "transaction"),
    "Retail": ("retail", "store", "sku", "product", "cart", "checkout", "inventory", "category", "brand", "discount", "units", "basket"),
    "Ecommerce": ("ecommerce", "cart", "checkout", "sku", "product", "order", "customer", "session", "conversion"),
    "Marketing": ("campaign", "lead", "click", "impression", "conversion", "channel", "cpc", "ctr", "roas", "creative"),
    "HR": ("employee", "salary", "department", "attrition", "hire", "tenure", "performance", "attendance", "role", "manager", "headcount"),
    "Manufacturing": ("manufacturing", "factory", "plant", "machine", "defect", "downtime", "production", "yield", "quality", "workorder", "batch", "supplier"),
    "Healthcare": ("patient", "health", "diagnosis", "clinical", "medical", "heart", "bp", "blood", "glucose", "insulin", "bmi", "treatment", "hospital", "admission"),
    "Banking": ("account", "loan", "deposit", "branch", "credit", "debit", "balance", "default", "mortgage", "interest"),
    "Education": ("student", "grade", "course", "attendance", "score", "school", "enrollment", "teacher", "class", "semester", "gpa"),
    "Inventory": ("inventory", "stock", "warehouse", "shipment", "supplier", "sku", "reorder", "backorder", "quantity"),
    "CRM": ("lead", "opportunity", "account", "contact", "pipeline", "stage", "deal", "crm", "owner"),
    "Customer Support": ("ticket", "case", "support", "sla", "resolution", "agent", "queue", "priority", "csat"),
}

DOMAIN_VALUE_SIGNALS: dict[str, tuple[str, ...]] = {
    "Sales": ("won", "lost", "closed"),
    "Customer Churn": ("churned", "retained", "cancelled", "canceled"),
    "Healthcare": ("positive", "negative", "diagnosed", "patient", "normal", "abnormal"),
    "Finance": ("buy", "sell", "market", "equity", "bond", "invoice"),
    "HR": ("terminated", "active", "manager", "employee", "full time", "part time"),
    "Education": ("pass", "fail", "enrolled", "student", "freshman", "senior"),
    "Retail": ("cart", "checkout", "store", "online", "returned", "discount"),
    "Manufacturing": ("defective", "passed", "failed", "machine", "supplier", "batch"),
    "Customer Support": ("open", "closed", "resolved", "escalated"),
}

TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9]+")


def _tokens(value: Any) -> list[str]:
    text = str(value or "").replace("_", " ").replace("-", " ").lower()
    return TOKEN_RE.findall(text)


def _flatten_metadata(metadata: Mapping[str, Any] | None) -> list[str]:
    if not metadata:
        return []
    values: list[str] = []

    def visit(item: Any) -> None:
        if isinstance(item, Mapping):
            for key, value in item.items():
                values.append(str(key))
                visit(value)
        elif isinstance(item, list | tuple | set):
            for value in item:
                visit(value)
        elif item is not None:
            values.append(str(item))

    visit(metadata)
    return values


def _sample_value_tokens(df: pd.DataFrame | None, limit_columns: int = 12, limit_values: int = 20) -> list[str]:
    if df is None or df.empty:
        return []
    values: list[str] = []
    for column in df.columns[:limit_columns]:
        series = df[column].dropna().astype(str).head(limit_values)
        values.extend(series.tolist())
    return values


def _score_domain(evidence_tokens: list[str]) -> tuple[str, float, list[str]]:
    if not evidence_tokens:
        return "Generic Business Dataset", 0.0, []

    token_text = " ".join(evidence_tokens)
    scores: dict[str, int] = {}
    matched: dict[str, list[str]] = {}
    for domain, signals in DOMAIN_SIGNALS.items():
        hits = [signal for signal in signals if signal in token_text]
        value_hits = [signal for signal in DOMAIN_VALUE_SIGNALS.get(domain, ()) if signal in token_text]
        scores[domain] = len(hits) * 3 + len(value_hits)
        matched[domain] = sorted(set(hits + value_hits))

    best_domain, best_score = max(scores.items(), key=lambda item: item[1])
    if best_score <= 0:
        return "Generic Business Dataset", 0.0, []

    total_possible = max(len(DOMAIN_SIGNALS[best_domain]) * 3, 1)
    confidence = min(0.98, max(0.35, best_score / total_possible))
    return best_domain, round(confidence, 2), matched[best_domain]


def detect_dataset_domain(
    columns: Iterable[Any] | None = None,
    df: pd.DataFrame | None = None,
    metadata: Mapping[str, Any] | None = None,
    title: str | None = None,
) -> dict[str, Any]:
    column_values = list(columns) if columns is not None else (df.columns.tolist() if df is not None else [])
    evidence_text = []
    evidence_text.extend(column_values)
    evidence_text.extend(_flatten_metadata(metadata))
    evidence_text.extend(_sample_value_tokens(df))
    if title:
        evidence_text.append(title)

    evidence_tokens: list[str] = []
    for value in evidence_text:
        evidence_tokens.extend(_tokens(value))

    domain, confidence_score, signals = _score_domain(evidence_tokens)
    return {
        "domain": domain if domain in SUPPORTED_DOMAINS else "Generic Business Dataset",
        "confidence_score": confidence_score,
        "confidence": "high" if confidence_score >= 0.7 else "medium" if confidence_score >= 0.45 else "low",
        "signals": signals,
        "supported_domains": list(SUPPORTED_DOMAINS),
    }


def update_session_detected_domain(
    dataset_id: str | None,
    df: pd.DataFrame | None = None,
    metadata: Mapping[str, Any] | None = None,
    title: str | None = None,
) -> dict[str, Any]:
    detection = detect_dataset_domain(df=df, metadata=metadata, title=title)
    if dataset_id:
        st.session_state.setdefault("detected_domains", {})[dataset_id] = detection
    st.session_state["active_detected_domain"] = detection
    st.session_state["detected_domain"] = detection["domain"]
    return detection
