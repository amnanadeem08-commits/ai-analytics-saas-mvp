import pandas as pd

from backend.services.executive_insight_service import build_executive_summary
from backend.services.dax_service import package_dax_measure
from backend.services.kpi_service import compute_business_metrics, compute_kpi_cards
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



def test_kpi_cards_use_average_for_continuous_measurements_with_units():
    df = pd.DataFrame(
        {
            "age": [20, 30, 40],
            "sleep_hours": [6.5, 7.0, 8.0],
            "daily_social_media_hours": [1.0, 2.0, 3.0],
            "screen_time_before_sleep": [0.5, 1.0, 1.5],
        }
    )

    cards = compute_kpi_cards(df)
    labels = [card["label"] for card in cards]

    assert "Avg Age" in labels
    age_card = next(card for card in cards if card["label"] == "Avg Age")
    assert age_card["value"] == 30.0
    assert age_card["aggregation"] == "average"
    assert age_card["formatted_value"] == "30 years"
    assert "Total Age" not in labels

    sleep_card = next(card for card in cards if card["label"] == "Avg Sleep Hours")
    assert sleep_card["aggregation"] == "average"
    assert sleep_card["unit"] == "h"


def test_kpi_cards_keep_sum_for_money_and_unique_count_for_ids():
    df = pd.DataFrame(
        {
            "customer_id": [101, 102, 102, 103],
            "revenue": [100, 200, 50, 25],
            "category": ["A", "A", "B", "C"],
        }
    )

    cards = compute_kpi_cards(df)
    revenue = next(card for card in cards if card["label"] == "Total Revenue")
    customer_id = next(card for card in cards if card["label"] == "Unique Customer Id")

    assert revenue["value"] == 375.0
    assert revenue["aggregation"] == "sum"
    assert customer_id["value"] == 3.0
    assert customer_id["aggregation"] == "unique_count"
    assert "Total Customer Id" not in [card["label"] for card in cards]
