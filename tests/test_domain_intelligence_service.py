import pandas as pd

from backend.models.domain_context_models import DomainContext
from backend.services.domain_intelligence_service import build_domain_context, build_domain_intelligence, detect_domain


def test_detect_domain_recognizes_health_finance_and_business_signals():
    health = detect_domain(pd.DataFrame(columns=["heart_rate", "bp", "glucose", "insulin", "bmi", "diagnosis"]))
    assert health["domain"] == "Healthcare"
    assert set(["heart", "bp", "glucose", "insulin", "bmi", "diagnosis"]).issubset(set(health["signals"]))

    finance = detect_domain(pd.DataFrame(columns=["stock", "price", "volume", "market_cap"]))
    assert finance["domain"] == "Finance"
    assert set(["stock", "price", "volume", "market"]).issubset(set(finance["signals"]))

    business = detect_domain(pd.DataFrame(columns=["revenue", "profit", "sales", "customer", "churn"]))
    assert business["domain"] in {"Sales", "Customer Churn", "Ecommerce"}


def test_detect_domain_never_defaults_unknown_to_healthcare():
    result = detect_domain(pd.DataFrame(columns=["name", "value", "notes"]))

    assert result["domain"] == "Generic Business Dataset"
    assert result["confidence"] == "low"


def test_detect_domain_supports_multiple_business_contexts():
    assert detect_domain(pd.DataFrame(columns=["employee_id", "department", "salary", "attrition"]))["domain"] == "HR"
    assert detect_domain(pd.DataFrame(columns=["ticket_id", "sla", "resolution_time", "agent_queue"]))["domain"] == "Customer Support"
    assert detect_domain(pd.DataFrame(columns=["loan_id", "balance", "credit_score", "default_status"]))["domain"] == "Banking"


def test_build_domain_intelligence_includes_phase3_components():
    df = pd.DataFrame(
        {
            "order_date": ["2026-01-01", "2026-01-02", "2026-01-03"],
            "revenue": [100.0, 140.0, 120.0],
            "cost": [70.0, 80.0, 75.0],
            "segment": ["A", "B", "A"],
            "customer_id": ["C1", "C2", "C3"],
        }
    )

    intelligence = build_domain_intelligence(df)

    assert "domain_detector" in intelligence
    assert intelligence["domain_detector"]["detected_domain"] in {"Sales", "Ecommerce", "Retail", "Generic Business Dataset"}

    assert "business_context_engine" in intelligence
    assert isinstance(intelligence["business_context_engine"].get("decision_focus", []), list)

    assert "dataset_classifier" in intelligence
    assert intelligence["dataset_classifier"]["dataset_type"] in {"time_series", "panel_time_series", "transactional", "cross_sectional", "tabular"}

    assert "dynamic_storyboard_template" in intelligence
    assert intelligence["dynamic_storyboard_template"].get("sections")

    assert "dynamic_dashboard_template" in intelligence
    assert intelligence["dynamic_dashboard_template"].get("widgets")

    assert "domain_kpis" in intelligence
    assert intelligence["domain_kpis"]


def test_build_domain_context_is_typed_and_serializes_legacy_contract():
    df = pd.DataFrame(
        {
            "order_date": ["2026-01-01", "2026-01-02"],
            "revenue": [100, 120],
            "cost": [60, 70],
            "region": ["East", "West"],
        }
    )

    context = build_domain_context(df)
    assert isinstance(context, DomainContext)
    assert context.detected_domain in {"Sales", "Ecommerce", "Retail", "Generic Business Dataset"}
    assert context.business_context
    assert context.storyboard_template
    assert context.dashboard_template
    assert isinstance(context.domain_specific_kpis, list)

    serialized = context.to_dict()
    assert "domain_context" in serialized
    assert serialized["domain_context"]["detected_domain"] == context.detected_domain
    assert serialized["domain_context"]["business_context"] == context.business_context
    assert serialized["domain_context"]["language_policy"]
