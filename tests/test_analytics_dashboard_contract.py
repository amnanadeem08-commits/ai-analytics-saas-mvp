from fastapi.testclient import TestClient

from backend.main import app



def test_analytics_dashboard_exposes_visualization_contract(monkeypatch):
    payload = {
        "dataset_id": "demo",
        "status": "ready",
        "overview": {"row_count": 10, "column_count": 3, "column_groups": {}, "missing_summary": {}},
        "kpi_cards": [
            {
                "kpi_id": "rows",
                "label": "Rows",
                "value": 10,
                "format": "number",
            }
        ],
        "chart_specs": [
            {
                "chart_id": "chart_demo",
                "title": "Demo Chart",
                "chart_type": "bar",
                "section": "comparisons",
                "columns": ["segment", "value"],
                "plotly": {"data": [{"type": "bar", "x": ["A", "B"], "y": [1, 2]}], "layout": {}},
                "metadata": {"subtitle": "Demo"},
            }
        ],
        "business_metrics": {"primary_metric": "value"},
        "layout": {"sections": [{"section_id": "visualizations", "title": "Visuals", "description": "", "chart_ids": ["chart_demo"], "order": 1}]},
        "column_types": {
            "numeric_columns": ["value"],
            "categorical_columns": ["segment"],
            "date_columns": [],
            "boolean_columns": [],
        },
        "top_categories": {},
        "correlations": {},
        "time_trends": {},
        "domain_intelligence": {"detection": {"domain": "Sales"}},
        "domain_context": {"detected_domain": "Sales"},
        "dashboard_spec": {
            "default_dashboard": {"charts": [{"chart_id": "chart_demo"}]},
            "visualization_rules": {"registry_policy": {"chart_types": ["bar"]}},
        },
        "export_bundle": {"exports": {"excel": True, "pptx": True, "pdf": True}},
    }

    monkeypatch.setattr("backend.api.routes.analytics_routes.get_dashboard_stats", lambda _dataset_id: payload)

    client = TestClient(app)
    response = client.get("/analytics/demo/dashboard")

    assert response.status_code == 200
    body = response.json()
    assert body["chart_specs"]
    assert body["dashboard_spec"]["default_dashboard"]["charts"]
    assert body["dashboard_spec"]["visualization_rules"]["registry_policy"]
    assert body["export_bundle"]["exports"]["excel"] is True
    assert body["domain_context"]["detected_domain"] == "Sales"
