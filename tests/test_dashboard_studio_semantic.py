import pandas as pd

from backend.processing.schema_service import build_column_schema
from backend.services.visual_builder_service import _field, build_visual_recommendations


def test_dashboard_studio_flags_id_columns_and_prioritizes_business_fields():
    df = pd.DataFrame(
        {
            "customer_id": [101, 102, 103, 104],
            "country": ["USA", "USA", "Canada", "Brazil"],
            "revenue": [1200.0, 900.0, 700.0, 1100.0],
            "churn_rate": [0.1, 0.2, 0.05, 0.15],
        }
    )
    schema = build_column_schema(df)
    fields = {_field(column, "semantic", len(df))["name"]: _field(column, "semantic", len(df)) for column in schema}

    assert fields["customer_id"]["semantic_role"] == "id_column"
    assert "may not be useful as a chart axis" in fields["customer_id"]["helper_message"]
    assert fields["country"]["semantic_role"] == "geography_column"
    assert fields["revenue"]["semantic_role"] == "revenue_currency_column"
    assert fields["churn_rate"]["semantic_role"] == "percentage_ratio_column"
    assert fields["country"]["business_priority"] > fields["customer_id"]["business_priority"]

    recommendations = build_visual_recommendations(list(fields.values()), len(df))
    titles = {item["title"] for item in recommendations}
    chart_types = {item["suggested_chart_type"] for item in recommendations}

    assert "Total Records" in titles
    assert "Total Revenue" in titles
    assert "Revenue by Country" in titles
    assert "Churn Rate by Country" in titles
    assert {"kpi", "bar", "horizontal_bar", "table"}.issubset(chart_types)
    assert all(item["business_meaning"] for item in recommendations)
    assert all(item["spec"] for item in recommendations)
