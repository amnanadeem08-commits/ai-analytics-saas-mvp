import pandas as pd

from backend.ai.rule_based_engine import generate_rule_based_insights
from backend.processing.data_profiler import profile_dataframe
from backend.services.analyst.analyst_service import answer_analyst_question
from backend.services.dashboard_service import build_dashboard_view
from backend.services.suggested_question_service import build_suggested_questions


def test_profile_adds_quality_outliers_correlations_and_trends():
    df = pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=10, freq="ME"),
            "revenue": [10, 12, 14, 16, 18, 20, 22, 24, 26, 200],
            "profit": [5, 6, 7, 8, 9, 10, 11, 12, 13, 100],
            "region": ["North", "South"] * 5,
        }
    )

    profile = profile_dataframe(df)

    assert profile["data_quality_score"]["grade"] in {"A", "B"}
    assert profile["date_summary"]["date"]["unique_periods"] == 10
    assert profile["outlier_summary"][0]["column"] == "revenue"
    assert profile["correlation_summary"]
    assert profile["correlation_summary"][0]["caution"]
    assert profile["trend_summary"][0]["metric"] in {"revenue", "profit"}


def test_rule_based_insights_include_structured_business_metadata():
    df = pd.DataFrame({"region": ["North", "South", "South"], "sales": [100, 150, 200]})

    insights = generate_rule_based_insights(df)
    quality = next(item for item in insights if item["type"] == "data_quality_score")

    assert quality["metadata"]["what_happened"]
    assert quality["metadata"]["why_it_matters"]
    assert quality["metadata"]["evidence_from_data"]
    assert quality["metadata"]["recommended_action"]


def test_suggested_questions_are_grounded_in_profile_evidence():
    profile = {
        "outlier_summary": [{"column": "revenue"}],
        "correlation_summary": [{"column_a": "revenue", "column_b": "profit"}],
        "trend_summary": [{"metric": "revenue"}],
        "total_missing_values": 3,
    }
    questions = build_suggested_questions(
        business_metrics={"primary_metric": "revenue", "primary_segment": "region"},
        domain_intelligence={"detection": {"domain": "Sales"}},
        profile=profile,
    )

    assert any("region" in question and "revenue" in question for question in questions)
    assert any("outliers" in question for question in questions)
    assert any("revenue and profit" in question for question in questions)


def test_analyst_uses_average_for_age_segment_questions():
    df = pd.DataFrame(
        {
            "gender": ["Male", "Male", "Female", "Female"],
            "age": [50, 60, 25, 35],
        }
    )

    answer = answer_analyst_question(df, "Which gender has the highest age?")

    assert "average age" in answer["answer"].lower()
    assert answer["analyst"]["rows"][0]["label"] == "Male"
    assert answer["analyst"]["rows"][0]["aggregation"] == "average"
