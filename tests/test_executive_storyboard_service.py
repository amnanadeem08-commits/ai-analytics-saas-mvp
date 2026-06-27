import pandas as pd

from backend.services.ai_business_insight_service import build_ai_business_insights_from_data_insights
from backend.services.data_insights_service import build_data_insights
from backend.services.executive_storyboard_service import _build_recommendations


def test_executive_storyboard_recommendations_are_ranked_from_ai_cards():
    data_insights = build_data_insights(
        pd.DataFrame(
            {
                "order_date": ["2026-01-01", "2026-01-02", "2026-02-01", "2026-02-02", "2026-03-01", "2026-03-02", "2026-04-01", "2026-04-02"],
                "revenue": [100, 120, 160, 180, 210, 230, 260, 280],
                "segment": ["A", "A", "B", "B", "A", "B", "A", "B"],
            }
        )
    )
    ai_payload = build_ai_business_insights_from_data_insights(data_insights)
    recommendations = _build_recommendations(ai_payload["cards"])

    assert recommendations
    assert set(recommendations[0]) == {"title", "priority", "business_value", "difficulty", "expected_impact", "recommendation", "source_type"}
    assert recommendations[0]["priority"] in {"High", "Medium", "Low"}


def test_executive_storyboard_handles_empty_ai_cards():
    assert _build_recommendations([]) == []
