import pandas as pd

from backend.services.executive_insight_service import build_executive_summary
from backend.services.dax_service import package_dax_measure
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


def test_dax_measure_preview_uses_friendly_display_formats():
    count_preview = package_dax_measure("Record Count =\nCOUNTROWS('Dataset')", "Generic Analytics", None)["measure_preview"]
    assert count_preview["display_format"] == "Whole Number"
    assert count_preview["power_bi_format_string"] == "#,##0"
    assert count_preview["preview_value"] == "1,234"

    revenue_preview = package_dax_measure("Total revenue =\nSUM('Dataset'[revenue])", "Sales", "revenue")["measure_preview"]
    assert revenue_preview["display_format"] == "Currency"
    assert revenue_preview["power_bi_format_string"] == "$#,##0.00"

    rate_preview = package_dax_measure("Churn Rate =\nDIVIDE([Churned], [Customers])", "Customer Churn", "churn_rate")[
        "measure_preview"
    ]
    assert rate_preview["display_format"] == "Percentage"
    assert rate_preview["power_bi_format_string"] == "0.00%"

    age_preview = package_dax_measure("Average age =\nAVERAGE('Dataset'[age])", "Generic Analytics", "age")["measure_preview"]
    assert age_preview["display_format"] == "Decimal Number"
    assert age_preview["power_bi_format_string"] == "0.0"
