from __future__ import annotations

import json
from dataclasses import dataclass

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.ai_business_insight_service import build_ai_business_insights_from_data_insights
from backend.services.dashboard_spec_service import build_dashboard_spec
from backend.services.data_insights_service import build_data_insights
from backend.services.domain_intelligence_service import build_domain_intelligence, detect_domain
from backend.services.kpi_service import compute_kpi_cards


HEALTHCARE_TERMS = ("patient", "diagnosis", "disease", "admission", "clinical", "treatment")
CHURN_TERMS = ("churn rate", "retention rate", "churn drivers", "high risk customers")


@dataclass(frozen=True)
class DomainRouteCase:
    case_id: str
    dataset_id: str
    expected_domain: str
    expected_titles: tuple[str, ...]
    forbidden_titles: tuple[str, ...]
    expected_domain_kpi_labels: tuple[str, ...]
    expected_context_terms: tuple[str, ...]
    forbid_healthcare_terms: bool = True
    forbid_churn_terms: bool = True


def _sales_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "order_date": ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"],
            "revenue": [120.0, 140.0, 100.0, 160.0],
            "cost": [80.0, 90.0, 70.0, 95.0],
            "region": ["East", "West", "East", "South"],
            "product": ["A", "B", "A", "C"],
        }
    )


def _churn_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "customer_id": ["C1", "C2", "C3", "C4", "C5", "C6"],
            "churn": ["Yes", "No", "Yes", "No", "Yes", "No"],
            "tenure": [2, 20, 4, 36, 3, 24],
            "contract_type": ["Month-to-month", "One year", "Month-to-month", "Two year", "Month-to-month", "One year"],
            "monthly_charges": [90, 70, 95, 60, 88, 72],
            "segment": ["A", "B", "A", "B", "A", "B"],
        }
    )


def _healthcare_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "patient_id": ["P1", "P2", "P3", "P4", "P5", "P6"],
            "diagnosis": ["A", "B", "A", "C", "B", "A"],
            "admission_status": ["Admitted", "Discharged", "Admitted", "Discharged", "Admitted", "Discharged"],
            "depression": ["Yes", "No", "Yes", "No", "Yes", "No"],
            "anxiety": ["No", "Yes", "No", "Yes", "No", "Yes"],
            "bmi": [29.5, 24.1, 31.2, 23.8, 30.4, 22.9],
        }
    )


def _generic_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "name": ["A", "B", "C", "D"],
            "value": [1, 2, 3, 4],
            "notes": ["x", "y", "z", "w"],
        }
    )


CASES: tuple[tuple[DomainRouteCase, pd.DataFrame], ...] = (
    (
        DomainRouteCase(
            case_id="sales",
            dataset_id="sales_case",
            expected_domain="Sales",
            expected_titles=("Revenue Overview", "Sales Trends", "Product Performance", "Regional Performance", "Recommendations"),
            forbidden_titles=("Patient Overview", "Disease Distribution", "Admissions", "Customer Profile", "Churn Drivers"),
            expected_domain_kpi_labels=("Total Revenue", "Total Cost"),
            expected_context_terms=("sales context", "commercial performance"),
            forbid_healthcare_terms=True,
            forbid_churn_terms=True,
        ),
        _sales_df(),
    ),
    (
        DomainRouteCase(
            case_id="customer_churn",
            dataset_id="churn_case",
            expected_domain="Customer Churn",
            expected_titles=("Executive Summary", "Customer Profile", "Churn Drivers", "High Risk Customers", "Retention Recommendations"),
            forbidden_titles=("Patient Overview", "Disease Distribution", "Admissions"),
            expected_domain_kpi_labels=("Churn Rate", "Retention Rate"),
            expected_context_terms=("customer churn context", "retention"),
            forbid_healthcare_terms=True,
            forbid_churn_terms=False,
        ),
        _churn_df(),
    ),
    (
        DomainRouteCase(
            case_id="healthcare",
            dataset_id="healthcare_case",
            expected_domain="Healthcare",
            expected_titles=("Patient Overview", "Disease Distribution", "Admissions", "Outcomes", "Clinical Recommendations"),
            forbidden_titles=("Customer Profile", "Churn Drivers", "High Risk Customers"),
            expected_domain_kpi_labels=("Depression Rate", "Anxiety Rate"),
            expected_context_terms=("healthcare context", "population health", "clinical operations"),
            forbid_healthcare_terms=False,
            forbid_churn_terms=True,
        ),
        _healthcare_df(),
    ),
    (
        DomainRouteCase(
            case_id="generic",
            dataset_id="generic_case",
            expected_domain="Generic Business Dataset",
            expected_titles=("Dataset Overview", "KPI Summary", "Segment Analysis", "Trends", "Recommendations"),
            forbidden_titles=("Patient Overview", "Disease Distribution", "Admissions", "Customer Profile", "Churn Drivers"),
            expected_domain_kpi_labels=("Records",),
            expected_context_terms=("generic business dataset context", "general business analytics"),
            forbid_healthcare_terms=True,
            forbid_churn_terms=True,
        ),
        _generic_df(),
    ),
)


def _response_text(payload: dict) -> str:
    return json.dumps(payload).lower()


def _build_dashboard_from_df(dataset_id: str, df: pd.DataFrame) -> dict:
    detection = detect_domain(df)
    data_insights = build_data_insights(df)
    ai_business = build_ai_business_insights_from_data_insights(data_insights, detection)
    dashboard = {
        "kpi_cards": compute_kpi_cards(df),
        "chart_specs": [],
        "domain_intelligence": build_domain_intelligence(df),
        "data_quality_score": data_insights.get("dataset_health", {}),
    }
    dashboard["dashboard_spec"] = build_dashboard_spec(
        dataset_id,
        df,
        dashboard,
        data_insights=data_insights,
        ai_business=ai_business,
    )
    return dashboard


def _patch_intelligence_dependencies(monkeypatch: pytest.MonkeyPatch, df: pd.DataFrame) -> None:
    monkeypatch.setattr("backend.api.routes.intelligence_routes.load_dataset_dataframe", lambda _dataset_id: df)
    monkeypatch.setattr("backend.services.executive_storyboard_service.load_dataset_dataframe", lambda _dataset_id: df)
    monkeypatch.setattr(
        "backend.services.executive_storyboard_service.build_dashboard_view",
        lambda dataset_id: _build_dashboard_from_df(dataset_id, df),
    )
    monkeypatch.setattr(
        "backend.services.executive_storyboard_service.build_ai_business_insights",
        lambda _dataset_id: build_ai_business_insights_from_data_insights(build_data_insights(df), detect_domain(df)),
    )


def _assert_legacy_contract(payload: dict) -> None:
    assert set(payload.keys()) == {"dataset_id", "status", "sections", "source_payloads"}
    assert isinstance(payload["sections"], list)
    assert payload["sections"]
    for section in payload["sections"]:
        assert {"section_id", "title", "order"}.issubset(set(section.keys()))


def _section(payload: dict, section_id: str) -> dict:
    return next(item for item in payload.get("sections", []) if item.get("section_id") == section_id)


def _assert_domain_kpis(storyboard_payload: dict, expected_labels: tuple[str, ...]) -> None:
    kpi_section = _section(storyboard_payload, "kpi_overview")
    kpis = kpi_section.get("kpis") or []
    injected = [item for item in kpis if str(item.get("kpi_id", "")).startswith("story_domain_")]
    assert injected
    labels = {str(item.get("label", "")) for item in injected}
    for label in expected_labels:
        assert label in labels
    for item in injected:
        assert item.get("business_context") == "Domain-specific KPI injected by domain intelligence."


@pytest.mark.parametrize(
    ("case", "df"),
    CASES,
    ids=[case.case_id for case, _ in CASES],
)
def test_executive_storyboard_route_is_domain_aware(monkeypatch: pytest.MonkeyPatch, case: DomainRouteCase, df: pd.DataFrame):
    _patch_intelligence_dependencies(monkeypatch, df)
    client = TestClient(app)

    domain_response = client.get(f"/intelligence/{case.dataset_id}/domain")
    storyboard_response = client.get(f"/intelligence/{case.dataset_id}/executive-storyboard")

    assert domain_response.status_code == 200
    assert storyboard_response.status_code == 200

    domain_payload = domain_response.json()
    storyboard_payload = storyboard_response.json()

    # 1) Correct domain detection.
    assert domain_payload.get("detection", {}).get("domain") == case.expected_domain

    # 6) Backward compatibility of route contract.
    _assert_legacy_contract(storyboard_payload)

    # 2) Dynamic storyboard generation by detected domain.
    titles = [str(item.get("title", "")) for item in storyboard_payload.get("sections", [])]
    assert tuple(titles) == case.expected_titles
    for forbidden in case.forbidden_titles:
        assert forbidden not in titles

    # 3) Domain KPI injection from domain-specific layer.
    _assert_domain_kpis(storyboard_payload, case.expected_domain_kpi_labels)

    # 4) Executive summary references domain business context.
    summary_section = _section(storyboard_payload, "executive_summary")
    summary_text = str((summary_section.get("content") or {}).get("executive_summary", "")).lower()
    assert any(token in summary_text for token in case.expected_context_terms)

    # 5) Regression protection for cross-domain terminology leakage.
    payload_text = _response_text(storyboard_payload)
    if case.forbid_healthcare_terms:
        for term in HEALTHCARE_TERMS:
            assert term not in payload_text
    if case.forbid_churn_terms:
        for term in CHURN_TERMS:
            assert term not in payload_text


def test_domain_intelligence_route_returns_phase3_contract(monkeypatch: pytest.MonkeyPatch):
    df = _sales_df()
    monkeypatch.setattr("backend.api.routes.intelligence_routes.load_dataset_dataframe", lambda _dataset_id: df)

    client = TestClient(app)
    response = client.get("/intelligence/demo/domain")

    assert response.status_code == 200
    payload = response.json()

    assert "detection" in payload
    assert "domain_detector" in payload
    assert "business_context_engine" in payload
    assert "dataset_classifier" in payload
    assert "dynamic_storyboard_template" in payload
    assert "dynamic_dashboard_template" in payload
    assert "domain_kpis" in payload
    assert "root_causes" in payload
    assert "domain_context" in payload
    assert payload["domain_context"].get("detected_domain") == payload["detection"]["domain"]
    assert payload["domain_context"].get("language_policy")
