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
