from __future__ import annotations

from typing import Any

import pandas as pd

from backend.processing.column_detector import detect_column_types
from backend.utils.response_utils import to_json_safe


DOMAIN_SIGNALS = {
    "Customer Churn": ["churn", "cancel", "retention", "tenure", "contract", "subscription"],
    "Sales": ["sales", "revenue", "order", "customer", "product", "region", "amount"],
    "Marketing": ["campaign", "lead", "click", "impression", "conversion", "channel", "cpc", "ctr"],
    "Finance": ["profit", "loss", "expense", "cost", "margin", "budget", "cash", "invoice"],
    "Healthcare": ["depression", "anxiety", "stress", "health", "patient", "score", "diagnosis", "risk"],
    "HR": ["employee", "salary", "department", "attrition", "hire", "performance", "attendance"],
    "Operations": ["inventory", "shipment", "delivery", "delay", "warehouse", "ticket", "sla"],
    "Telecom": ["call", "usage", "plan", "data", "minutes", "roaming", "contract", "churn"],
    "E-commerce": ["cart", "checkout", "sku", "product", "order", "customer", "revenue"],
    "Education": ["student", "grade", "course", "attendance", "score", "school", "enrollment"],
}


def _column_text(df: pd.DataFrame) -> str:
    return " ".join(str(column).lower().replace("_", " ") for column in df.columns)


def _find_column(df: pd.DataFrame, hints: list[str]) -> str | None:
    for column in df.columns:
        lowered = str(column).lower().replace("_", " ")
        if any(hint in lowered for hint in hints):
            return column
    return None


def detect_domain(df: pd.DataFrame) -> dict[str, Any]:
    text = _column_text(df)
    scores = {
        domain: sum(1 for signal in signals if signal in text)
        for domain, signals in DOMAIN_SIGNALS.items()
    }
    domain, score = max(scores.items(), key=lambda item: item[1])
    if score == 0:
        domain = "Generic Analytics"
    confidence = "high" if score >= 4 else "medium" if score >= 2 else "low"
    return {
        "domain": domain,
        "confidence": confidence,
        "score": score,
        "signals": [signal for signal in DOMAIN_SIGNALS.get(domain, []) if signal in text],
        "dataset_purpose": _purpose(domain),
        "business_context": _context(domain),
        "common_metrics": _common_metrics(domain),
        "likely_root_causes": _likely_causes(domain),
    }


def _purpose(domain: str) -> str:
    return {
        "Customer Churn": "Understand customer retention, churn risk, and drivers of customer loss.",
        "Sales": "Analyze revenue, sales distribution, segments, products, and growth drivers.",
        "Marketing": "Evaluate campaign performance, channel efficiency, and conversion behavior.",
        "Finance": "Monitor financial performance, costs, profit, margin, and risk.",
        "Healthcare": "Assess population health indicators, risk groups, and clinical score patterns.",
        "HR": "Understand workforce performance, attrition, compensation, and department patterns.",
        "Operations": "Monitor operational throughput, delays, inventory, quality, and service performance.",
        "Telecom": "Analyze subscriber usage, churn, plans, and service performance.",
        "E-commerce": "Analyze orders, product performance, customers, basket behavior, and revenue.",
        "Education": "Analyze student outcomes, scores, attendance, and enrollment trends.",
    }.get(domain, "Analyze dataset structure, KPIs, segments, trends, and decision opportunities.")


def _context(domain: str) -> str:
    return {
        "Customer Churn": "Retention and customer lifetime value decisions.",
        "Healthcare": "Population risk and evidence-based health indicator monitoring.",
        "Sales": "Executive revenue and commercial performance management.",
        "Finance": "Board-level financial control and performance review.",
    }.get(domain, "Business performance management and analytical decision support.")


def _common_metrics(domain: str) -> list[str]:
    return {
        "Customer Churn": ["Churn Rate", "Retention Rate", "High Risk Segments", "Churn Drivers"],
        "Healthcare": ["Depression Rate", "Anxiety Rate", "Stress Rate", "High Risk Groups"],
        "Sales": ["Revenue", "Average Order Value", "Top Region", "Growth Rate"],
        "Marketing": ["Conversion Rate", "Cost per Lead", "Campaign ROI", "Channel Mix"],
        "Finance": ["Profit", "Cost", "Margin", "Variance"],
    }.get(domain, ["Primary Metric", "Top Segment", "Trend", "Data Quality"])


def _likely_causes(domain: str) -> list[str]:
    return {
        "Customer Churn": ["Contract type", "tenure", "price sensitivity", "service issues", "usage decline"],
        "Healthcare": ["Age group", "population segment", "stress indicators", "score severity", "access factors"],
        "Sales": ["regional mix", "product mix", "seasonality", "customer segment", "pricing"],
        "Marketing": ["channel quality", "campaign targeting", "creative fit", "funnel leakage"],
    }.get(domain, ["segment concentration", "data quality", "trend movement", "metric variance"])


def _binary_rate(df: pd.DataFrame, column: str, positive_terms: list[str]) -> tuple[int, float]:
    series = df[column].dropna()
    if series.empty:
        return 0, 0.0
    if pd.api.types.is_numeric_dtype(series):
        positives = int((pd.to_numeric(series, errors="coerce").fillna(0) > 0).sum())
    else:
        positives = int(series.astype(str).str.lower().isin(positive_terms).sum())
    return positives, round(positives / len(series) * 100, 2)


def _segment_rate(df: pd.DataFrame, indicator: str, segment: str, terms: list[str]) -> dict[str, Any] | None:
    if indicator not in df.columns or segment not in df.columns:
        return None
    rows = []
    for label, group in df.groupby(segment, dropna=False):
        positives, rate = _binary_rate(group, indicator, terms)
        rows.append({"segment": str(label), "records": int(len(group)), "positive_count": positives, "rate": rate})
    return max(rows, key=lambda row: row["rate"]) if rows else None


def churn_analytics(df: pd.DataFrame) -> dict[str, Any]:
    churn_col = _find_column(df, ["churn", "cancel", "left"])
    segment_col = _find_column(df, ["segment", "region", "contract", "plan", "customer type"])
    if not churn_col:
        return {"available": False, "reason": "No churn indicator column was detected."}
    churn_count, churn_rate = _binary_rate(df, churn_col, ["yes", "true", "1", "churned", "left", "cancelled", "canceled"])
    high_risk = _segment_rate(df, churn_col, segment_col, ["yes", "true", "1", "churned", "left", "cancelled", "canceled"]) if segment_col else None
    retention_rate = round(100 - churn_rate, 2)
    drivers = []
    numeric_columns = detect_column_types(df)["numeric_columns"]
    churn_numeric = df[churn_col].astype(str).str.lower().isin(["yes", "true", "1", "churned", "left", "cancelled", "canceled"]).astype(int)
    for column in numeric_columns[:8]:
        corr = pd.to_numeric(df[column], errors="coerce").corr(churn_numeric)
        if pd.notna(corr):
            drivers.append({"driver": column, "correlation": to_json_safe(round(float(corr), 4))})
    drivers = sorted(drivers, key=lambda row: abs(row["correlation"]), reverse=True)[:5]
    return {
        "available": True,
        "churn_column": churn_col,
        "churn_rate": churn_rate,
        "retention_rate": retention_rate,
        "churned_records": churn_count,
        "high_risk_segment": high_risk,
        "churn_drivers": drivers,
        "what_happened": f"Churn rate is {churn_rate}% and retention rate is {retention_rate}%.",
        "why_it_happened": (
            f"{high_risk['segment']} is the highest-risk segment at {high_risk['rate']}% churn."
            if high_risk else "No segment column was detected to isolate churn concentration."
        ),
        "what_to_do": "Prioritize retention actions for high-risk segments and investigate the strongest correlated churn drivers.",
        "expected_impact": "Reducing churn in the highest-risk segment can improve retention and protect recurring revenue.",
    }


def healthcare_analytics(df: pd.DataFrame) -> dict[str, Any]:
    indicators = {
        "depression": _find_column(df, ["depression", "depressed"]),
        "anxiety": _find_column(df, ["anxiety", "anxious"]),
        "stress": _find_column(df, ["stress"]),
    }
    segment_col = _find_column(df, ["age", "gender", "region", "group", "segment"])
    rates = {}
    for name, column in indicators.items():
        if column:
            count, rate = _binary_rate(df, column, ["yes", "true", "1", "high", "severe", "moderate"])
            rates[f"{name}_rate"] = {"column": column, "positive_count": count, "rate": rate}
    if not rates:
        return {"available": False, "reason": "No depression, anxiety, stress, or health-risk indicator was detected."}
    high_risk_groups = []
    for name, column in indicators.items():
        if column and segment_col:
            group = _segment_rate(df, column, segment_col, ["yes", "true", "1", "high", "severe", "moderate"])
            if group:
                high_risk_groups.append({"indicator": name, "dimension": segment_col, **group})
    return {
        "available": True,
        "rates": rates,
        "high_risk_groups": high_risk_groups,
        "what_happened": "; ".join(f"{name.replace('_', ' ').title()} is {data['rate']}%" for name, data in rates.items()),
        "why_it_happened": (
            f"Highest observed risk group: {high_risk_groups[0]['segment']} for {high_risk_groups[0]['indicator']}."
            if high_risk_groups else "No demographic or regional segment column was detected to isolate risk groups."
        ),
        "what_to_do": "Focus outreach and further assessment on the highest-risk population segments identified by the data.",
        "expected_impact": "Targeted intervention can improve resource allocation and reduce unmanaged population risk.",
    }


def smart_domain_kpis(df: pd.DataFrame) -> list[dict[str, Any]]:
    domain = detect_domain(df)["domain"]
    kpis: list[dict[str, Any]] = []
    if domain in {"Customer Churn", "Telecom"}:
        churn = churn_analytics(df)
        if churn.get("available"):
            kpis.extend(
                [
                    {"label": "Churn Rate", "value": churn["churn_rate"], "format": "percent", "evidence": churn},
                    {"label": "Retention Rate", "value": churn["retention_rate"], "format": "percent", "evidence": churn},
                ]
            )
    if domain == "Healthcare":
        healthcare = healthcare_analytics(df)
        if healthcare.get("available"):
            for name, data in healthcare["rates"].items():
                kpis.append({"label": name.replace("_", " ").title(), "value": data["rate"], "format": "percent", "evidence": data})
    return kpis


def build_domain_intelligence(df: pd.DataFrame) -> dict[str, Any]:
    detection = detect_domain(df)
    domain = detection["domain"]
    domain_mode: dict[str, Any] = {}
    if domain in {"Customer Churn", "Telecom"}:
        domain_mode = {"mode": "churn", **churn_analytics(df)}
    elif domain == "Healthcare":
        domain_mode = {"mode": "healthcare", **healthcare_analytics(df)}
    return {
        "detection": detection,
        "domain_kpis": smart_domain_kpis(df),
        "domain_mode": domain_mode,
        "root_causes": build_root_causes(df),
    }


def build_root_causes(df: pd.DataFrame) -> list[dict[str, Any]]:
    column_types = detect_column_types(df)
    numeric = column_types["numeric_columns"]
    categorical = column_types["categorical_columns"]
    causes = []
    for metric in numeric[:3]:
        metric_series = pd.to_numeric(df[metric], errors="coerce")
        drivers = []
        for segment in categorical[:4]:
            grouped = df.assign(_metric=metric_series).groupby(segment, dropna=False)["_metric"].mean().dropna()
            if len(grouped) > 1:
                spread = float(grouped.max() - grouped.min())
                drivers.append(
                    {
                        "driver": segment,
                        "statistical_indicator": "mean spread",
                        "value": to_json_safe(round(spread, 4)),
                        "top_segment": str(grouped.idxmax()),
                        "bottom_segment": str(grouped.idxmin()),
                    }
                )
        if drivers:
            drivers = sorted(drivers, key=lambda row: abs(row["value"] or 0), reverse=True)
            causes.append(
                {
                    "metric": metric,
                    "potential_drivers": drivers[:3],
                    "supporting_evidence": f"{drivers[0]['driver']} shows the largest average spread for {metric}.",
                    "recommended_action": f"Investigate {drivers[0]['top_segment']} versus {drivers[0]['bottom_segment']} to identify operational drivers of {metric}.",
                }
            )
    return causes
