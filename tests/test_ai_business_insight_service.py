import pandas as pd

from backend.services.ai_business_insight_service import build_ai_business_insights_from_data_insights
from backend.services.data_insights_service import build_data_insights


def _card(payload, card_type):
    return next(card for card in payload["cards"] if card["type"] == card_type)


def test_ai_business_insights_empty_dataset_returns_insufficient_cards():
    payload = build_ai_business_insights_from_data_insights(build_data_insights(pd.DataFrame()))

    assert len(payload["cards"]) == 5
    assert all(card["evidence_status"] == "insufficient" for card in payload["cards"])


def test_ai_business_insights_small_dataset_avoids_forecast_guessing():
    data_insights = build_data_insights(pd.DataFrame({"revenue": [10, 20], "segment": ["A", "B"]}))
    payload = build_ai_business_insights_from_data_insights(data_insights)

    assert len(payload["cards"]) == 5
    assert _card(payload, "Forecast")["evidence_status"] == "insufficient"


def test_ai_business_insights_missing_columns_state_insufficient_trend():
    data_insights = build_data_insights(pd.DataFrame({"category": ["A", "B", "C", "D"], "label": ["x", "y", "z", "w"]}))
    payload = build_ai_business_insights_from_data_insights(data_insights)

    assert _card(payload, "Trend")["evidence_status"] == "insufficient"
    assert _card(payload, "Forecast")["evidence_status"] == "insufficient"


def test_ai_business_insights_existing_dataset_uses_validated_evidence():
    data_insights = build_data_insights(
        pd.DataFrame(
            {
                "order_date": ["2026-01-01", "2026-01-02", "2026-02-01", "2026-02-02", "2026-03-01", "2026-03-02", "2026-04-01", "2026-04-02"],
                "revenue": [100, 120, 160, 180, 210, 230, 260, 280],
                "segment": ["A", "A", "B", "B", "A", "B", "A", "B"],
            }
        )
    )
    payload = build_ai_business_insights_from_data_insights(data_insights)

    assert len(payload["cards"]) == 5
    assert _card(payload, "Opportunity")["evidence_status"] == "validated"
    assert _card(payload, "Trend")["evidence_status"] == "validated"
    assert "projected" not in _card(payload, "Forecast")["supporting_evidence"].lower()


def test_ai_business_insights_routes_supported_domains_to_prompts():
    data_insights = build_data_insights(pd.DataFrame({"metric": [1, 2, 3, 4], "segment": ["A", "B", "A", "B"]}))

    expected_prompts = {
        "Sales": "SALES_ANALYST_PROMPT",
        "Customer Churn": "CUSTOMER_CHURN_ANALYST_PROMPT",
        "Telecom": "TELECOM_ANALYST_PROMPT",
        "Finance": "FINANCE_ANALYST_PROMPT",
        "Retail": "RETAIL_ANALYST_PROMPT",
        "Ecommerce": "ECOMMERCE_ANALYST_PROMPT",
        "Marketing": "MARKETING_ANALYST_PROMPT",
        "HR": "HR_ANALYST_PROMPT",
        "Manufacturing": "MANUFACTURING_ANALYST_PROMPT",
        "Healthcare": "HEALTHCARE_ANALYST_PROMPT",
        "Banking": "BANKING_ANALYST_PROMPT",
        "Education": "EDUCATION_ANALYST_PROMPT",
        "Inventory": "INVENTORY_ANALYST_PROMPT",
        "CRM": "CRM_ANALYST_PROMPT",
        "Customer Support": "CUSTOMER_SUPPORT_ANALYST_PROMPT",
        "Generic Business Dataset": "GENERAL_ANALYST_PROMPT",
    }

    for domain, prompt in expected_prompts.items():
        payload = build_ai_business_insights_from_data_insights(
            data_insights,
            {"domain": domain, "confidence_score": 0.88},
        )

        assert payload["domain_router"]["domain"] == domain
        assert payload["domain_router"]["prompt"] == prompt
        assert payload["domain_router"]["confidence_score"] == 0.88
        assert all(card["domain"] == domain for card in payload["cards"])
        assert all(card["prompt"] == prompt for card in payload["cards"])


def test_healthcare_domain_router_avoids_business_language_in_card_values():
    data_insights = build_data_insights(
        pd.DataFrame(
            {
                "patient_id": [1, 2, 3, 4, 5, 6, 7, 8],
                "glucose": [90, 110, 140, 160, 95, 125, 150, 170],
                "bmi": [21, 24, 31, 34, 23, 29, 33, 36],
                "diagnosis": ["low", "low", "high", "high", "low", "medium", "high", "high"],
            }
        )
    )

    payload = build_ai_business_insights_from_data_insights(
        data_insights,
        {"domain": "Healthcare", "confidence_score": 0.91},
    )
    text_fields = (
        "title",
        "business_meaning",
        "supporting_evidence",
        "expected_business_impact",
        "executive_recommendation",
    )
    combined_text = " ".join(str(card.get(field, "")) for card in payload["cards"] for field in text_fields).lower()

    assert payload["domain_router"]["domain"] == "Healthcare"
    assert payload["domain_router"]["prompt"] == "HEALTHCARE_ANALYST_PROMPT"
    assert "business" not in combined_text
    assert "kpi" not in combined_text
    assert "revenue" not in combined_text
    assert "customer" not in combined_text


def test_ai_business_insight_engine_generates_complete_domain_sections():
    data_insights = build_data_insights(
        pd.DataFrame(
            {
                "order_date": ["2026-01-01", "2026-01-02", "2026-02-01", "2026-02-02", "2026-03-01", "2026-03-02", "2026-04-01", "2026-04-02"],
                "revenue": [100, 120, 160, 180, 210, 230, 260, 280],
                "segment": ["A", "A", "B", "B", "A", "B", "A", "B"],
            }
        )
    )

    payload = build_ai_business_insights_from_data_insights(data_insights, {"domain": "Finance", "confidence": "high"})

    assert payload["executive_summary"]["headline"] == "Finance Executive Summary"
    assert "financial" in payload["executive_summary"]["summary"].lower()
    assert payload["key_findings"]
    assert payload["kpis"]
    assert payload["risks"]
    assert payload["opportunities"]
    assert payload["recommendations"]
    assert payload["cards"]


def test_healthcare_language_applies_to_upgraded_insight_sections():
    data_insights = build_data_insights(
        pd.DataFrame(
            {
                "patient_id": [1, 2, 3, 4, 5, 6, 7, 8],
                "glucose": [90, 110, 140, 160, 95, 125, 150, 170],
                "bmi": [21, 24, 31, 34, 23, 29, 33, 36],
                "diagnosis": ["low", "low", "high", "high", "low", "medium", "high", "high"],
            }
        )
    )

    payload = build_ai_business_insights_from_data_insights(data_insights, {"domain": "Healthcare", "confidence": "high"})
    sections = [
        payload["executive_summary"],
        payload["key_findings"],
        payload["kpis"],
        payload["risks"],
        payload["opportunities"],
        payload["recommendations"],
    ]
    combined_text = str(sections).lower()

    assert "population health" in payload["executive_summary"]["summary"].lower()
    assert "business" not in combined_text
    assert "kpi" not in combined_text
    assert "revenue" not in combined_text
    assert "customer" not in combined_text
