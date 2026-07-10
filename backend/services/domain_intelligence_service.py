from __future__ import annotations

from dataclasses import asdict
from typing import Any

import pandas as pd

from backend.models.domain_context_models import DomainContext
from backend.registry.domain_registry import CustomerChurnDomain, DomainRegistry, GenericBusinessDomain, HealthcareDomain, ProfileBackedDomainPlugin, SalesDomain
from backend.registry.kpi_registry import FunctionKPIProvider, KPIRegistry
from backend.registry.metric_registry import MetricDefinition, MetricRegistry
from backend.registry.visualization_registry import VisualizationPolicy, VisualizationRegistry
from backend.processing.column_detector import detect_column_types
from backend.services.domain_policy_service import build_domain_policy
from backend.services.domain_profile_service import all_domain_signals, detect_domain_profile, domain_profile
from backend.utils.response_utils import to_json_safe


DOMAIN_SIGNALS = all_domain_signals()

_DOMAIN_REGISTRY: DomainRegistry | None = None
_KPI_REGISTRY: KPIRegistry | None = None
_VISUALIZATION_REGISTRY: VisualizationRegistry | None = None
_METRIC_REGISTRY: MetricRegistry | None = None


def _column_text(df: pd.DataFrame) -> str:
    return " ".join(str(column).lower().replace("_", " ") for column in df.columns)


def _find_column(df: pd.DataFrame, hints: list[str]) -> str | None:
    for column in df.columns:
        lowered = str(column).lower().replace("_", " ")
        if any(hint in lowered for hint in hints):
            return column
    return None


def _slug(text: str) -> str:
    return str(text or "").strip().lower().replace("&", "and").replace(" ", "_").replace("-", "_")


def _domain_kpi_provider(df: pd.DataFrame, detection: dict[str, Any], _classifier: dict[str, Any], _context: dict[str, Any] | None) -> list[dict[str, Any]]:
    domain = str(detection.get("domain") or "Generic Business Dataset")
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
    kpis.extend(_domain_template_kpis(df, domain))

    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in kpis:
        key = str(item.get("label", "")).strip().lower()
        if key and key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped


def get_domain_registry() -> DomainRegistry:
    global _DOMAIN_REGISTRY
    if _DOMAIN_REGISTRY is not None:
        return _DOMAIN_REGISTRY

    registry = DomainRegistry()

    def supplier(domain_name: str) -> dict[str, Any]:
        return domain_profile(domain_name)

    registry.register(
        SalesDomain(
            name="Sales",
            aliases=("sales",),
            profile_supplier=supplier,
            kpi_provider=_domain_kpi_provider,
        )
    )
    registry.register(
        CustomerChurnDomain(
            name="Customer Churn",
            aliases=("customer churn", "churn", "telecom"),
            profile_supplier=supplier,
            kpi_provider=_domain_kpi_provider,
        )
    )
    registry.register(
        HealthcareDomain(
            name="Healthcare",
            aliases=("healthcare", "health"),
            profile_supplier=supplier,
            kpi_provider=_domain_kpi_provider,
        )
    )
    registry.register(
        GenericBusinessDomain(
            name="Generic Business Dataset",
            aliases=("generic", "generic analytics", "general"),
            profile_supplier=supplier,
            kpi_provider=_domain_kpi_provider,
        )
    )

    # Register profile-backed default plugins for all known domains not explicitly overridden.
    for domain_name in DOMAIN_SIGNALS.keys():
        if domain_name in registry.registered_domains():
            continue
        registry.register(
            ProfileBackedDomainPlugin(
                name=domain_name,
                aliases=(domain_name.lower(),),
                profile_supplier=supplier,
                kpi_provider=_domain_kpi_provider,
            )
        )

    _DOMAIN_REGISTRY = registry
    return registry


def get_kpi_registry() -> KPIRegistry:
    global _KPI_REGISTRY
    if _KPI_REGISTRY is not None:
        return _KPI_REGISTRY
    registry = KPIRegistry()
    for domain_name in list(DOMAIN_SIGNALS.keys()) + ["Generic Business Dataset"]:
        registry.register(
            FunctionKPIProvider(
                domain=domain_name,
                aliases=(domain_name.lower(),),
                handler=_domain_kpi_provider,
            )
        )
    _KPI_REGISTRY = registry
    return registry


def get_visualization_registry() -> VisualizationRegistry:
    global _VISUALIZATION_REGISTRY
    if _VISUALIZATION_REGISTRY is not None:
        return _VISUALIZATION_REGISTRY
    registry = VisualizationRegistry()
    for domain_name in list(DOMAIN_SIGNALS.keys()) + ["Generic Business Dataset"]:
        profile = domain_profile(domain_name)
        registry.register(
            VisualizationPolicy(
                domain=domain_name,
                preferred_charts=["line", "bar", "table"],
                fallback_charts=["bar", "line", "table"],
                section_chart_hints={
                    "trends": ["line", "area", "table"],
                    "risks": ["bar", "table"],
                    "opportunities": ["bar", "line", "table"],
                    "kpi_overview": ["table", "bar"],
                },
            ),
            aliases=(domain_name.lower(),),
        )
        del profile
    _VISUALIZATION_REGISTRY = registry
    return registry


def get_metric_registry() -> MetricRegistry:
    global _METRIC_REGISTRY
    if _METRIC_REGISTRY is not None:
        return _METRIC_REGISTRY
    registry = MetricRegistry()
    registry.register(
        MetricDefinition(
            name="Revenue",
            business_meaning="Top-line income generated by commercial activity.",
            metric_category="financial",
            executive_importance="high",
            preferred_visualizations=["line", "bar", "waterfall"],
            benchmark_compatibility=True,
            aggregation_strategy="sum",
        )
    )
    registry.register(
        MetricDefinition(
            name="Churn Rate",
            business_meaning="Share of customers who discontinue service in the period.",
            metric_category="retention",
            executive_importance="high",
            preferred_visualizations=["line", "bar", "table"],
            benchmark_compatibility=True,
            aggregation_strategy="rate",
        )
    )
    registry.register(
        MetricDefinition(
            name="Data Quality Score",
            business_meaning="Readiness of data for reliable analysis and decision-making.",
            metric_category="governance",
            executive_importance="high",
            preferred_visualizations=["gauge", "table", "bar"],
            benchmark_compatibility=False,
            aggregation_strategy="score",
        )
    )
    _METRIC_REGISTRY = registry
    return registry


def _first_numeric_metric(df: pd.DataFrame, hints: list[str] | None = None) -> str | None:
    numeric_columns = detect_column_types(df).get("numeric_columns", [])
    if not numeric_columns:
        return None
    if hints:
        for hint in hints:
            for column in numeric_columns:
                lowered = column.lower().replace("_", " ")
                if hint in lowered:
                    return column
    return numeric_columns[0]


def _average_numeric(df: pd.DataFrame, column: str) -> float:
    series = pd.to_numeric(df[column], errors="coerce").dropna()
    if series.empty:
        return 0.0
    return round(float(series.mean()), 2)


def _sum_numeric(df: pd.DataFrame, column: str) -> float:
    series = pd.to_numeric(df[column], errors="coerce").dropna()
    if series.empty:
        return 0.0
    return round(float(series.sum()), 2)


def detect_domain(df: pd.DataFrame, metadata: dict[str, Any] | None = None, title: str | None = None) -> dict[str, Any]:
    return detect_domain_profile(df, metadata=metadata, title=title)


def _purpose(domain: str) -> str:
    return domain_profile(domain)["purpose"]


def _context(domain: str) -> str:
    return domain_profile(domain)["context"]


def _common_metrics(domain: str) -> list[str]:
    return domain_profile(domain)["metrics"]


def _likely_causes(domain: str) -> list[str]:
    return domain_profile(domain)["root_causes"]


def classify_dataset(df: pd.DataFrame) -> dict[str, Any]:
    detected = detect_column_types(df)
    numeric_columns = detected.get("numeric_columns", [])
    categorical_columns = detected.get("categorical_columns", [])
    date_columns = detected.get("date_columns", [])
    row_count = int(len(df))
    column_count = int(len(df.columns))
    id_like_columns = [
        col for col in df.columns
        if str(col).lower() == "id" or str(col).lower().endswith("_id") or str(col).lower().endswith("id")
    ]

    if date_columns and id_like_columns:
        dataset_type = "panel_time_series"
    elif date_columns:
        dataset_type = "time_series"
    elif id_like_columns and numeric_columns:
        dataset_type = "transactional"
    elif categorical_columns and numeric_columns:
        dataset_type = "cross_sectional"
    else:
        dataset_type = "tabular"

    primary_metric = _first_numeric_metric(df, hints=["revenue", "sales", "profit", "amount", "cost", "score", "rate"]) or ""
    primary_time_dimension = date_columns[0] if date_columns else ""
    key_dimension = (id_like_columns[0] if id_like_columns else (categorical_columns[0] if categorical_columns else ""))
    completeness = 0.0
    if row_count > 0 and column_count > 0:
        completeness = round((1.0 - (float(df.isna().sum().sum()) / float(max(df.size, 1)))) * 100.0, 2)

    return {
        "dataset_type": dataset_type,
        "row_count": row_count,
        "column_count": column_count,
        "numeric_count": len(numeric_columns),
        "categorical_count": len(categorical_columns),
        "date_count": len(date_columns),
        "id_like_columns": [str(col) for col in id_like_columns],
        "primary_metric": primary_metric,
        "primary_time_dimension": primary_time_dimension,
        "key_dimension": key_dimension,
        "completeness_score": completeness,
    }


def build_business_context_engine(df: pd.DataFrame, detection: dict[str, Any], classifier: dict[str, Any]) -> dict[str, Any]:
    domain = detection.get("domain", "Generic Business Dataset")
    profile = domain_profile(domain)
    metric = classifier.get("primary_metric") or _first_numeric_metric(df)
    key_dimension = classifier.get("key_dimension") or _find_column(df, ["segment", "region", "category", "department", "channel"])

    decision_focus = [
        f"Track {_common_metrics(domain)[0] if _common_metrics(domain) else 'primary KPI'} with domain-specific evidence.",
        f"Investigate {_likely_causes(domain)[0] if _likely_causes(domain) else 'main drivers'} before committing actions.",
        "Prioritize actions that can be measured in the next review cycle.",
    ]

    risk_focus = [
        f"Monitor {_likely_causes(domain)[0] if _likely_causes(domain) else 'variance drivers'} for early warning signals.",
        "Validate data quality before making high-impact decisions.",
    ]

    return {
        "domain": domain,
        "purpose": profile.get("purpose"),
        "business_context": profile.get("context"),
        "common_metrics": profile.get("metrics", []),
        "likely_root_causes": profile.get("root_causes", []),
        "primary_metric": metric,
        "key_dimension": key_dimension,
        "decision_focus": decision_focus,
        "risk_focus": risk_focus,
    }


def build_dynamic_storyboard_template(detection: dict[str, Any], classifier: dict[str, Any]) -> dict[str, Any]:
    domain = detection.get("domain", "Generic Business Dataset")
    profile = domain_profile(domain)
    sections = [
        {
            "section_id": _slug(title),
            "title": title,
            "order": index + 1,
            "intent": "time_analysis" if "trend" in title.lower() else "domain_analysis",
        }
        for index, title in enumerate(profile.get("storyboard_sections", []))
    ]

    dataset_type = classifier.get("dataset_type", "tabular")
    if dataset_type in {"time_series", "panel_time_series"} and not any("trend" in section["title"].lower() for section in sections):
        sections.insert(
            min(2, len(sections)),
            {
                "section_id": "time_trends",
                "title": "Time Trends",
                "order": 3,
                "intent": "time_analysis",
            },
        )
    for index, section in enumerate(sections):
        section["order"] = index + 1

    return {
        "template_id": f"storyboard_{_slug(domain)}_{dataset_type}",
        "domain": domain,
        "dataset_type": dataset_type,
        "sections": sections,
    }


def build_dynamic_dashboard_template(detection: dict[str, Any], classifier: dict[str, Any]) -> dict[str, Any]:
    domain = detection.get("domain", "Generic Business Dataset")
    profile = domain_profile(domain)
    widgets = []
    for index, widget in enumerate(profile.get("dashboard_widgets", []), start=1):
        widget_kind = "trend" if "trend" in widget.lower() else "kpi" if "kpi" in widget.lower() else "chart"
        widgets.append(
            {
                "widget_id": f"widget_{index}_{_slug(widget)}",
                "title": widget,
                "kind": widget_kind,
                "order": index,
            }
        )

    dataset_type = classifier.get("dataset_type", "tabular")
    if dataset_type in {"time_series", "panel_time_series"} and not any("trend" in str(item.get("title", "")).lower() for item in widgets):
        widgets.append(
            {
                "widget_id": "widget_time_trend",
                "title": "Time Trend",
                "kind": "trend",
                "order": len(widgets) + 1,
            }
        )

    return {
        "template_id": f"dashboard_{_slug(domain)}_{dataset_type}",
        "domain": domain,
        "dataset_type": dataset_type,
        "widgets": widgets,
        "layout": "grid_2x2" if len(widgets) <= 4 else "grid_3x2",
    }


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


def _domain_template_kpis(df: pd.DataFrame, domain: str) -> list[dict[str, Any]]:
    kpis: list[dict[str, Any]] = []
    lower_domain = str(domain or "").lower()
    revenue_col = _find_column(df, ["revenue", "sales", "amount", "income"])
    cost_col = _find_column(df, ["cost", "expense", "spend"])
    margin_col = _find_column(df, ["margin", "profit"])
    count_label = "Records" if lower_domain in {"generic business dataset", "sales", "finance", "retail", "ecommerce"} else "Entities"

    kpis.append({"label": count_label, "value": int(len(df)), "format": "integer", "evidence": {"source": "row_count"}})

    if revenue_col:
        kpis.append({
            "label": "Total Revenue",
            "value": _sum_numeric(df, revenue_col),
            "format": "number",
            "evidence": {"column": revenue_col},
        })
    if cost_col:
        kpis.append({
            "label": "Total Cost",
            "value": _sum_numeric(df, cost_col),
            "format": "number",
            "evidence": {"column": cost_col},
        })
    if margin_col:
        kpis.append({
            "label": "Average Margin",
            "value": _average_numeric(df, margin_col),
            "format": "number",
            "evidence": {"column": margin_col},
        })

    if domain == "Marketing":
        conv_col = _find_column(df, ["conversion", "converted", "won"])
        if conv_col:
            _, rate = _binary_rate(df, conv_col, ["yes", "true", "1", "converted", "won"])
            kpis.append({"label": "Conversion Rate", "value": rate, "format": "percent", "evidence": {"column": conv_col}})

    if domain == "HR":
        attrition_col = _find_column(df, ["attrition", "terminated", "resigned", "left"])
        if attrition_col:
            _, rate = _binary_rate(df, attrition_col, ["yes", "true", "1", "terminated", "resigned", "left"])
            kpis.append({"label": "Attrition Rate", "value": rate, "format": "percent", "evidence": {"column": attrition_col}})

    if domain == "Manufacturing":
        defect_col = _find_column(df, ["defect", "failed", "scrap"])
        if defect_col:
            _, rate = _binary_rate(df, defect_col, ["yes", "true", "1", "defect", "failed", "scrap"])
            kpis.append({"label": "Defect Rate", "value": rate, "format": "percent", "evidence": {"column": defect_col}})

    if domain == "Customer Support":
        sla_col = _find_column(df, ["sla", "resolved", "resolution"])
        if sla_col:
            _, rate = _binary_rate(df, sla_col, ["yes", "true", "1", "resolved", "closed", "met"])
            kpis.append({"label": "Resolution/SLA Rate", "value": rate, "format": "percent", "evidence": {"column": sla_col}})

    if domain == "Banking":
        default_col = _find_column(df, ["default", "delinquent"])
        if default_col:
            _, rate = _binary_rate(df, default_col, ["yes", "true", "1", "default", "delinquent"])
            kpis.append({"label": "Default Rate", "value": rate, "format": "percent", "evidence": {"column": default_col}})

    if domain == "Education":
        pass_col = _find_column(df, ["pass", "result", "grade_status"])
        if pass_col:
            _, rate = _binary_rate(df, pass_col, ["yes", "true", "1", "pass", "passed"])
            kpis.append({"label": "Pass Rate", "value": rate, "format": "percent", "evidence": {"column": pass_col}})

    if domain == "Inventory":
        stockout_col = _find_column(df, ["out_of_stock", "stockout", "backorder"])
        if stockout_col:
            _, rate = _binary_rate(df, stockout_col, ["yes", "true", "1", "stockout", "backorder"])
            kpis.append({"label": "Stockout/Backorder Rate", "value": rate, "format": "percent", "evidence": {"column": stockout_col}})

    if domain == "CRM":
        win_col = _find_column(df, ["won", "stage", "deal_status"])
        if win_col:
            _, rate = _binary_rate(df, win_col, ["yes", "true", "1", "won", "closed won"])
            kpis.append({"label": "Win Rate", "value": rate, "format": "percent", "evidence": {"column": win_col}})

    return kpis


def _visualization_rules(domain: str, classifier: dict[str, Any]) -> dict[str, Any]:
    profile = domain_profile(domain)
    visualization_registry = get_visualization_registry()
    return {
        "preferred_widgets": profile.get("dashboard_widgets", []),
        "preferred_storyboard_sections": profile.get("storyboard_sections", []),
        "dataset_type": classifier.get("dataset_type", "tabular"),
        "layout_hint": "time_series_first" if classifier.get("dataset_type") in {"time_series", "panel_time_series"} else "balanced",
        "registry_policy": asdict(visualization_registry.resolve(domain)),
    }


def _executive_summary_style(domain: str) -> dict[str, Any]:
    return {
        "tone": "clinical" if domain == "Healthcare" else "executive_business",
        "focus": "risk_and_outcomes" if domain == "Healthcare" else "value_and_risk",
        "format": "what_why_action",
    }


def _recommended_questions(domain: str, classifier: dict[str, Any], profile: dict[str, Any]) -> list[str]:
    metric = classifier.get("primary_metric") or "primary metric"
    key_dimension = classifier.get("key_dimension") or "top segment"
    questions = [
        f"Which {key_dimension} is driving the strongest movement in {metric}?",
        f"What is the highest-priority risk driver for {domain.lower()} performance?",
        "Which action should leadership prioritize in the next review cycle?",
    ]
    if domain in {"Customer Churn", "Telecom"}:
        questions.append("Which segment has the highest churn risk and why?")
    if domain == "Healthcare":
        questions.append("Which population segment shows the highest risk indicators?")
    if profile.get("metrics"):
        questions.append(f"How should we track {profile['metrics'][0]} week over week?")
    return list(dict.fromkeys(questions))[:8]


def smart_domain_kpis(df: pd.DataFrame) -> list[dict[str, Any]]:
    detection = detect_domain(df)
    classifier = classify_dataset(df)
    provider = get_kpi_registry().resolve(detection.get("domain"))
    if not provider:
        return []
    return provider.build_kpis(df, detection=detection, classifier=classifier, context=None)


def build_domain_context(df: pd.DataFrame) -> DomainContext:
    detection = detect_domain(df)
    domain = detection["domain"]
    profile = domain_profile(domain)
    classifier = classify_dataset(df)
    domain_registry = get_domain_registry()
    plugin = domain_registry.resolve(domain)
    business_context = plugin.build_context(detection=detection, classifier=classifier, profile=profile)
    storyboard_template = plugin.get_storyboard(classifier=classifier, profile=profile)
    dashboard_template = plugin.get_dashboard(classifier=classifier, profile=profile)
    policy = build_domain_policy(domain)
    visualization_registry = get_visualization_registry()
    metric_registry = get_metric_registry()

    domain_mode: dict[str, Any] = {}
    if domain in {"Customer Churn", "Telecom"}:
        domain_mode = {"mode": "churn", **churn_analytics(df)}
    elif domain == "Healthcare":
        domain_mode = {"mode": "healthcare", **healthcare_analytics(df)}

    domain_kpis = plugin.get_kpis(df, detection=detection, classifier=classifier)
    metric_details = metric_registry.to_lookup_dict(classifier.get("primary_metric"))

    context = DomainContext(
        detected_domain=domain,
        confidence=str(detection.get("confidence") or "low"),
        confidence_score=float(detection.get("confidence_score") or 0.0),
        business_context=str(business_context.get("business_context") or profile.get("context") or "General business analytics"),
        industry=str(business_context.get("industry") or domain),
        domain_specific_kpis=domain_kpis,
        storyboard_template=storyboard_template,
        dashboard_template=dashboard_template,
        visualization_rules={
            **_visualization_rules(domain, classifier),
            "section_recommendations": {
                section.get("section_id"): visualization_registry.recommend_for_section(domain, section.get("section_id", ""))
                for section in storyboard_template.get("sections", [])
            },
            "metric_details": metric_details,
        },
        language_policy=plugin.get_language_policy() or policy,
        executive_summary_style=_executive_summary_style(domain),
        recommended_questions=plugin.get_suggested_questions(classifier=classifier, profile=profile),
        rag_context={
            "enabled": False,
            "notes": "Reserved for future RAG integration.",
            "domain_knowledge": profile.get("knowledge", []),
            "knowledge_pack_id": getattr(plugin, "knowledge_pack_id", None),
            "benchmark_provider": getattr(plugin, "benchmark_provider", None),
            "glossary_provider": getattr(plugin, "glossary_provider", None),
            "executive_guidance_provider": getattr(plugin, "executive_guidance_provider", None),
        },
        detection_signals=list(detection.get("signals", [])),
        dataset_classifier=classifier,
        business_context_engine={
            **build_business_context_engine(df, detection, classifier),
            **business_context,
        },
        root_causes=build_root_causes(df),
        domain_mode=domain_mode,
        knowledge_pack_id=getattr(plugin, "knowledge_pack_id", None),
        benchmark_provider=getattr(plugin, "benchmark_provider", None),
        glossary_provider=getattr(plugin, "glossary_provider", None),
        executive_guidance_provider=getattr(plugin, "executive_guidance_provider", None),
    )
    return context


def ensure_domain_context(value: DomainContext | dict[str, Any] | None, df: pd.DataFrame | None = None) -> DomainContext:
    if isinstance(value, DomainContext):
        return value
    if isinstance(value, dict) and value:
        return DomainContext.from_dict(value)
    if df is None:
        return DomainContext.from_dict({})
    return build_domain_context(df)


def build_domain_intelligence(df: pd.DataFrame) -> dict[str, Any]:
    context = build_domain_context(df)
    return to_json_safe(context.to_dict())


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
