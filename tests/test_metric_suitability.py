import pandas as pd

from backend.services.executive_insight_service import build_executive_summary
from backend.services.kpi_service import compute_business_metrics
from backend.services.metric_suitability_service import metric_suitability


def test_age_uses_average_not_total_in_executive_narrative():
    df = pd.DataFrame(
        {
            "gender": ["Male", "Male", "Female", "Female"],
            "age": [50, 60, 25, 35],
            "customer_id": [101, 102, 103, 104],
        }
    )

    suitability = metric_suitability("age", df["age"])
    assert suitability["recommended_aggregation"] == "average"
    assert suitability["business_relevance"] == "medium"

    metrics = compute_business_metrics(df)
    assert metrics["primary_metric"] == "age"
    assert metrics["segment_leader"] == {
        "dimension": "gender",
        "metric": "age",
        "segment": "Male",
        "value": 55.0,
        "aggregation": "average",
        "business_relevance": "medium",
    }

    summary = build_executive_summary(df)
    combined_text = " ".join(
        [
            summary["insight"],
            summary["reason"],
            " ".join(summary["evidence"]),
        ]
    ).lower()
    assert "highest average age" in combined_text
    assert "total age" not in combined_text
    assert summary["business_confidence"] == "medium"
    assert summary["business_relevance"] == "medium"
