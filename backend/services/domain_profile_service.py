from __future__ import annotations

from typing import Any

import pandas as pd


DOMAIN_PROFILES: dict[str, dict[str, Any]] = {
    "Sales": {
        "signals": ["sales", "revenue", "order", "product", "region", "amount", "quota", "pipeline"],
        "value_signals": ["won", "lost", "closed", "prospect"],
        "purpose": "Analyze revenue, sales distribution, products, regions, and growth drivers.",
        "context": "Commercial performance management and revenue decision support.",
        "metrics": ["Revenue", "Sales Growth", "Average Order Value", "Product Ranking", "Regional Performance"],
        "root_causes": ["regional mix", "product mix", "seasonality", "pricing", "sales channel"],
        "storyboard_sections": ["Revenue Overview", "Sales Trends", "Product Performance", "Regional Performance", "Profitability", "Forecast", "Recommendations"],
        "dashboard_widgets": ["Revenue Trend", "Profit Trend", "Product Ranking", "Region Performance", "KPI Cards"],
        "knowledge": ["Use additive revenue/profit measures for totals.", "Compare performance by product, region, channel, and time.", "Treat averages as supporting diagnostics, not revenue totals."],
    },
    "Customer Churn": {
        "signals": ["churn", "cancel", "retention", "tenure", "contract", "subscription", "left", "renewal"],
        "value_signals": ["churned", "cancelled", "canceled", "retained", "month-to-month"],
        "purpose": "Understand retention, churn risk, and drivers of customer loss.",
        "context": "Retention, customer lifetime value, and revenue-at-risk decisions.",
        "metrics": ["Churn Rate", "Retention Rate", "Tenure", "Revenue at Risk", "High Risk Segment"],
        "root_causes": ["contract type", "tenure", "price sensitivity", "service issues", "usage decline"],
        "storyboard_sections": ["Executive Summary", "Customer Profile", "Churn Drivers", "High Risk Customers", "Revenue Impact", "Retention Recommendations"],
        "dashboard_widgets": ["Churn Rate", "Contract Type", "Customer Lifetime", "Tenure Distribution", "Revenue at Risk"],
        "knowledge": ["Churn datasets should prioritize retention and revenue-at-risk language.", "Segment churn by tenure, contract, plan, and service usage.", "Do not describe churn datasets with healthcare terminology."],
    },
    "Telecom": {
        "signals": ["call", "usage", "plan", "data", "minutes", "roaming", "contract", "churn", "subscriber"],
        "value_signals": ["prepaid", "postpaid", "roaming", "unlimited"],
        "purpose": "Analyze subscriber usage, plans, service performance, and churn.",
        "context": "Telecom subscriber retention and service performance management.",
        "metrics": ["Usage", "Plan Mix", "Churn Rate", "Subscriber Count", "Service Revenue"],
        "root_causes": ["plan type", "usage decline", "network experience", "contract status"],
        "storyboard_sections": ["Subscriber Overview", "Usage Patterns", "Plan Performance", "Churn Risk", "Service Revenue", "Recommendations"],
        "dashboard_widgets": ["Subscriber KPIs", "Usage Trend", "Plan Mix", "Churn Rate", "Revenue at Risk"],
        "knowledge": ["Telecom analytics should focus on subscribers, usage, plans, churn, and revenue risk."],
    },
    "Finance": {
        "signals": ["profit", "loss", "expense", "cost", "margin", "budget", "cash", "invoice", "stock", "price", "volume", "market", "transaction"],
        "value_signals": ["debit", "credit", "asset", "liability"],
        "purpose": "Monitor financial performance, costs, margin, cash, and risk.",
        "context": "Financial control, board reporting, and variance review.",
        "metrics": ["Profit", "Cost", "Margin", "Variance", "Cash Flow"],
        "root_causes": ["cost mix", "margin pressure", "budget variance", "market movement"],
        "storyboard_sections": ["Financial Overview", "Revenue and Cost", "Margin Analysis", "Variance", "Risk Controls", "Recommendations"],
        "dashboard_widgets": ["Profit Trend", "Cost Breakdown", "Margin KPI", "Variance Table", "Risk Indicators"],
        "knowledge": ["Finance datasets should use financial control language and avoid clinical terms."],
    },
    "Retail": {
        "signals": ["store", "sku", "product", "cart", "checkout", "basket", "retail", "inventory", "price", "promotion"],
        "value_signals": ["online", "store", "pickup", "return"],
        "purpose": "Analyze store, product, basket, channel, inventory, and promotion performance.",
        "context": "Retail trading performance and merchandising decisions.",
        "metrics": ["Sales", "Basket Size", "Product Rank", "Inventory", "Returns"],
        "root_causes": ["product mix", "channel mix", "promotion", "stock availability"],
        "storyboard_sections": ["Retail Overview", "Product Performance", "Store or Channel Performance", "Basket Behavior", "Inventory", "Recommendations"],
        "dashboard_widgets": ["Sales KPIs", "Product Ranking", "Channel Mix", "Inventory", "Returns"],
        "knowledge": ["Retail datasets should prioritize product, store, channel, basket, and inventory language."],
    },
    "Ecommerce": {
        "signals": ["ecommerce", "cart", "checkout", "sku", "product", "order", "customer", "revenue", "session", "conversion"],
        "value_signals": ["abandoned", "checkout", "online", "conversion"],
        "purpose": "Analyze online orders, conversion, customers, basket behavior, and revenue.",
        "context": "Digital commerce performance and funnel optimization.",
        "metrics": ["Conversion Rate", "Revenue", "Average Order Value", "Cart Abandonment", "Product Performance"],
        "root_causes": ["channel quality", "checkout friction", "product mix", "traffic source"],
        "storyboard_sections": ["Ecommerce Overview", "Funnel Performance", "Product Performance", "Customer Behavior", "Revenue Impact", "Recommendations"],
        "dashboard_widgets": ["Conversion KPIs", "Revenue Trend", "Product Ranking", "Cart Abandonment", "Channel Performance"],
        "knowledge": ["Ecommerce datasets should focus on funnel, conversion, basket, product, and digital revenue."],
    },
    "Marketing": {
        "signals": ["campaign", "lead", "click", "impression", "conversion", "channel", "cpc", "ctr", "roas", "creative"],
        "value_signals": ["email", "social", "paid", "organic", "campaign"],
        "purpose": "Evaluate campaign performance, channel efficiency, and conversion behavior.",
        "context": "Marketing effectiveness and funnel decision support.",
        "metrics": ["Conversion Rate", "Cost per Lead", "Campaign ROI", "CTR", "Channel Mix"],
        "root_causes": ["channel quality", "targeting", "creative fit", "funnel leakage"],
        "storyboard_sections": ["Marketing Overview", "Campaign Performance", "Channel Efficiency", "Lead Quality", "Conversion", "Recommendations"],
        "dashboard_widgets": ["Campaign KPIs", "Channel Performance", "Conversion Funnel", "Cost Metrics", "Lead Quality"],
        "knowledge": ["Marketing datasets should use campaign, lead, channel, cost, and conversion language."],
    },
    "HR": {
        "signals": ["employee", "salary", "department", "attrition", "hire", "performance", "attendance", "turnover", "role"],
        "value_signals": ["terminated", "active", "resigned", "hired"],
        "purpose": "Understand workforce performance, attrition, hiring, compensation, and departments.",
        "context": "People analytics and workforce planning.",
        "metrics": ["Headcount", "Attrition", "Hiring", "Compensation", "Performance"],
        "root_causes": ["department", "role", "manager", "tenure", "compensation"],
        "storyboard_sections": ["Workforce Summary", "Attrition", "Hiring", "Department Analysis", "Employee Performance", "Recommendations"],
        "dashboard_widgets": ["Headcount", "Attrition Rate", "Hiring Trend", "Department Mix", "Performance"],
        "knowledge": ["HR datasets should use workforce, employee, attrition, hiring, and department language."],
    },
    "Manufacturing": {
        "signals": ["production", "machine", "defect", "quality", "downtime", "yield", "plant", "line", "throughput", "scrap"],
        "value_signals": ["defect", "downtime", "pass", "fail"],
        "purpose": "Monitor production, quality, throughput, downtime, and yield.",
        "context": "Manufacturing operations and quality performance.",
        "metrics": ["Throughput", "Yield", "Defect Rate", "Downtime", "Scrap"],
        "root_causes": ["machine", "line", "shift", "material", "quality process"],
        "storyboard_sections": ["Manufacturing Overview", "Throughput", "Quality", "Downtime", "Yield", "Recommendations"],
        "dashboard_widgets": ["Throughput KPIs", "Defect Trend", "Downtime", "Yield", "Plant Performance"],
        "knowledge": ["Manufacturing datasets should focus on production, quality, throughput, downtime, and yield."],
    },
    "Healthcare": {
        "signals": ["depression", "anxiety", "stress", "health", "patient", "diagnosis", "heart", "bp", "blood", "glucose", "insulin", "bmi", "medical", "admission", "treatment", "hospital"],
        "value_signals": ["diagnosed", "normal", "abnormal", "admitted", "discharged"],
        "purpose": "Assess population health indicators, risk groups, admissions, outcomes, and clinical score patterns.",
        "context": "Population health and evidence-based clinical operations monitoring.",
        "metrics": ["Patient Count", "Disease Frequency", "Admissions", "Risk Groups", "Outcomes"],
        "root_causes": ["age group", "population segment", "score severity", "access factors"],
        "storyboard_sections": ["Patient Overview", "Disease Distribution", "Admissions", "Outcomes", "Clinical Recommendations"],
        "dashboard_widgets": ["Disease Frequency", "Patient Demographics", "Admissions", "Treatment Outcomes", "Risk Indicators"],
        "knowledge": ["Healthcare language is only used for detected healthcare datasets.", "Avoid diagnosis or treatment advice; present population-level evidence and operational recommendations."],
    },
    "Banking": {
        "signals": ["account", "loan", "deposit", "branch", "credit", "debit", "balance", "default", "mortgage", "interest"],
        "value_signals": ["approved", "default", "delinquent", "active"],
        "purpose": "Analyze accounts, balances, credit risk, loans, branches, and customer activity.",
        "context": "Banking performance, risk, and customer portfolio management.",
        "metrics": ["Balance", "Loan Volume", "Default Rate", "Deposits", "Branch Performance"],
        "root_causes": ["credit segment", "branch", "loan type", "delinquency"],
        "storyboard_sections": ["Banking Overview", "Portfolio Performance", "Credit Risk", "Branch Analysis", "Customer Activity", "Recommendations"],
        "dashboard_widgets": ["Balance KPIs", "Loan Trend", "Default Risk", "Branch Performance", "Portfolio Mix"],
        "knowledge": ["Banking datasets should use portfolio, loan, account, balance, branch, and credit-risk language."],
    },
    "Education": {
        "signals": ["student", "grade", "course", "attendance", "score", "school", "enrollment", "teacher", "class"],
        "value_signals": ["passed", "failed", "enrolled", "graduated"],
        "purpose": "Analyze student outcomes, scores, attendance, enrollment, courses, and institutions.",
        "context": "Education performance and student outcome review.",
        "metrics": ["Enrollment", "Attendance", "Scores", "Pass Rate", "Course Performance"],
        "root_causes": ["course", "attendance", "grade level", "school", "student segment"],
        "storyboard_sections": ["Education Overview", "Enrollment", "Attendance", "Student Outcomes", "Course Performance", "Recommendations"],
        "dashboard_widgets": ["Enrollment KPIs", "Attendance", "Score Distribution", "Course Performance", "Pass Rate"],
        "knowledge": ["Education datasets should use student, course, enrollment, attendance, and outcome language."],
    },
    "Inventory": {
        "signals": ["inventory", "stock", "warehouse", "shipment", "supplier", "sku", "reorder", "backorder", "quantity"],
        "value_signals": ["in stock", "out of stock", "backorder"],
        "purpose": "Monitor stock, inventory movement, suppliers, warehouses, and reorder risk.",
        "context": "Inventory control and supply performance.",
        "metrics": ["Stock Level", "Reorder Risk", "Backorders", "Supplier Performance", "Warehouse Mix"],
        "root_causes": ["supplier", "warehouse", "demand", "lead time", "stockout"],
        "storyboard_sections": ["Inventory Overview", "Stock Levels", "Supplier Performance", "Reorder Risk", "Warehouse Analysis", "Recommendations"],
        "dashboard_widgets": ["Inventory KPIs", "Stock Trend", "Warehouse Mix", "Backorders", "Supplier Performance"],
        "knowledge": ["Inventory datasets should focus on stock, warehouse, supplier, reorder, and backorder language."],
    },
    "CRM": {
        "signals": ["lead", "opportunity", "account", "contact", "pipeline", "stage", "deal", "crm", "owner"],
        "value_signals": ["qualified", "proposal", "closed won", "closed lost"],
        "purpose": "Analyze accounts, contacts, pipeline, opportunities, and sales stages.",
        "context": "CRM pipeline and account management.",
        "metrics": ["Pipeline", "Deal Count", "Win Rate", "Stage Conversion", "Account Activity"],
        "root_causes": ["stage", "owner", "account", "deal size", "lead source"],
        "storyboard_sections": ["CRM Overview", "Pipeline", "Opportunity Stages", "Account Performance", "Win/Loss", "Recommendations"],
        "dashboard_widgets": ["Pipeline KPIs", "Stage Funnel", "Win Rate", "Owner Performance", "Account Activity"],
        "knowledge": ["CRM datasets should use account, contact, opportunity, pipeline, and stage language."],
    },
    "Customer Support": {
        "signals": ["ticket", "case", "support", "sla", "resolution", "agent", "queue", "priority", "csat"],
        "value_signals": ["open", "closed", "resolved", "escalated"],
        "purpose": "Analyze support tickets, SLA, resolution, queue, priority, agents, and customer satisfaction.",
        "context": "Customer support operations and service quality.",
        "metrics": ["Ticket Volume", "SLA Compliance", "Resolution Time", "Escalations", "CSAT"],
        "root_causes": ["queue", "priority", "agent", "issue type", "resolution time"],
        "storyboard_sections": ["Support Overview", "Ticket Volume", "SLA Performance", "Resolution", "Escalations", "Recommendations"],
        "dashboard_widgets": ["Ticket KPIs", "SLA", "Resolution Trend", "Queue Mix", "CSAT"],
        "knowledge": ["Customer support datasets should use tickets, cases, SLA, resolution, queues, and CSAT language."],
    },
    "Generic Business Dataset": {
        "signals": [],
        "value_signals": [],
        "purpose": "Analyze dataset structure, KPIs, segments, trends, risks, and decision opportunities.",
        "context": "General business analytics and evidence-based decision support.",
        "metrics": ["Primary Metric", "Top Segment", "Trend", "Data Quality"],
        "root_causes": ["segment concentration", "data quality", "trend movement", "metric variance"],
        "storyboard_sections": ["Dataset Overview", "KPI Summary", "Segment Analysis", "Trends", "Risks", "Recommendations"],
        "dashboard_widgets": ["KPI Cards", "Data Quality", "Recommended Charts", "Slicers", "Insights"],
        "knowledge": ["Use neutral business analytics language when domain confidence is low.", "Never default unknown datasets to healthcare."],
    },
}

DOMAIN_ALIASES = {
    "Operations": "Inventory",
    "E-commerce": "Ecommerce",
    "Generic Analytics": "Generic Business Dataset",
    "General": "Generic Business Dataset",
    "Business": "Generic Business Dataset",
}


def canonical_domain(domain: str | None) -> str:
    if not domain:
        return "Generic Business Dataset"
    value = str(domain).strip()
    return DOMAIN_ALIASES.get(value, value if value in DOMAIN_PROFILES else "Generic Business Dataset")


def domain_profile(domain: str | None) -> dict[str, Any]:
    canonical = canonical_domain(domain)
    profile = DOMAIN_PROFILES[canonical]
    return {"domain": canonical, **profile}


def all_domain_signals() -> dict[str, list[str]]:
    return {domain: list(profile.get("signals", [])) for domain, profile in DOMAIN_PROFILES.items() if domain != "Generic Business Dataset"}


def score_domain(df: pd.DataFrame, domain: str, profile: dict[str, Any], metadata: dict[str, Any] | None = None, title: str | None = None) -> dict[str, Any]:
    text_parts = [str(title or "")]
    text_parts.extend(str(column).lower().replace("_", " ") for column in df.columns)
    if metadata:
        text_parts.extend(str(value).lower() for value in metadata.values())
    column_text = " ".join(text_parts)
    column_signals = [signal for signal in profile.get("signals", []) if signal in column_text]

    value_hits: list[str] = []
    for column in df.columns[:25]:
        series = df[column].dropna()
        if series.empty or pd.api.types.is_numeric_dtype(series):
            continue
        sample = " ".join(series.astype(str).str.lower().head(50).tolist())
        value_hits.extend(signal for signal in profile.get("value_signals", []) if signal in sample)

    score = len(set(column_signals)) + min(len(set(value_hits)), 3)
    return {"domain": domain, "score": score, "signals": sorted(set(column_signals + value_hits))}


def detect_domain_profile(df: pd.DataFrame, metadata: dict[str, Any] | None = None, title: str | None = None) -> dict[str, Any]:
    scores = [score_domain(df, domain, profile, metadata, title) for domain, profile in DOMAIN_PROFILES.items() if domain != "Generic Business Dataset"]
    winner = max(scores, key=lambda item: item["score"], default={"domain": "Generic Business Dataset", "score": 0, "signals": []})
    if winner["score"] < 2:
        winner = {"domain": "Generic Business Dataset", "score": winner.get("score", 0), "signals": winner.get("signals", [])}
    confidence = "high" if winner["score"] >= 5 else "medium" if winner["score"] >= 3 else "low"
    profile = domain_profile(winner["domain"])
    return {
        "domain": profile["domain"],
        "confidence": confidence,
        "confidence_score": 0.9 if confidence == "high" else 0.65 if confidence == "medium" else 0.35,
        "score": int(winner["score"]),
        "signals": winner.get("signals", []),
        "dataset_purpose": profile["purpose"],
        "business_context": profile["context"],
        "common_metrics": profile["metrics"],
        "likely_root_causes": profile["root_causes"],
        "storyboard_sections": profile["storyboard_sections"],
        "dashboard_widgets": profile["dashboard_widgets"],
        "knowledge": profile["knowledge"],
    }
