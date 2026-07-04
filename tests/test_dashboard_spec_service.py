import pandas as pd

from backend.services.dashboard_spec_service import build_dashboard_spec
from backend.services.kpi_service import compute_kpi_cards


def _dashboard(df: pd.DataFrame) -> dict:
    return {
        "kpi_cards": compute_kpi_cards(df),
        "chart_specs": [],
        "data_quality_score": {"score": 100, "grade": "A"},
    }


def test_dashboard_spec_uses_sales_storyboard_and_knowledge():
    df = pd.DataFrame(
        {
            "order_date": ["2026-01-01", "2026-01-02"],
            "revenue": [100, 200],
            "sales_region": ["East", "West"],
            "product": ["A", "B"],
        }
    )

    spec = build_dashboard_spec("sales", df, _dashboard(df))

    assert spec["domain"]["detected"] == "Sales"
    assert spec["domain_context"]["detected_domain"] == "Sales"
    assert "Revenue Overview" in [item["title"] for item in spec["storyboard_blueprint"]]
    assert any("revenue" in item.lower() for item in spec["domain_knowledge"])


def test_dashboard_spec_unknown_dataset_is_generic_not_healthcare():
    df = pd.DataFrame({"name": ["A", "B"], "value": [1, 2], "notes": ["x", "y"]})

    spec = build_dashboard_spec("unknown", df, _dashboard(df))

    assert spec["domain"]["detected"] == "Generic Business Dataset"
    assert spec["domain_context"]["detected_domain"] == "Generic Business Dataset"
    assert "Patient Overview" not in [item["title"] for item in spec["storyboard_blueprint"]]
    assert "Dataset Overview" in [item["title"] for item in spec["storyboard_blueprint"]]


def test_dashboard_spec_exposes_dynamic_templates_classifier_and_domain_kpis():
    df = pd.DataFrame(
        {
            "order_date": ["2026-01-01", "2026-01-02", "2026-01-03"],
            "revenue": [120, 140, 160],
            "cost": [80, 90, 110],
            "region": ["East", "West", "East"],
            "customer_id": ["C1", "C2", "C3"],
        }
    )

    spec = build_dashboard_spec("sales_phase3", df, _dashboard(df))

    assert "dataset_classifier" in spec
    assert spec["dataset_classifier"]["dataset_type"] in {"time_series", "panel_time_series", "transactional", "cross_sectional", "tabular"}

    assert "business_context_engine" in spec
    assert spec["business_context_engine"].get("purpose")
    assert "domain_context" in spec
    assert spec["domain_context"].get("business_context")

    assert "dynamic_storyboard_template" in spec
    assert spec["dynamic_storyboard_template"].get("sections")

    assert "dynamic_dashboard_template" in spec
    assert spec["dynamic_dashboard_template"].get("widgets")
    assert "language_policy" in spec
    assert spec["language_policy"].get("prompt")
    assert "rag_context" in spec

    assert "domain_specific_kpis" in spec["default_dashboard"]
    assert isinstance(spec["default_dashboard"]["domain_specific_kpis"], list)
