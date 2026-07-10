import pandas as pd

from backend.registry.domain_registry import DomainRegistry, GenericBusinessDomain, ProfileBackedDomainPlugin
from backend.registry.kpi_registry import FunctionKPIProvider, KPIRegistry
from backend.registry.metric_registry import MetricDefinition, MetricRegistry
from backend.registry.visualization_registry import VisualizationPolicy, VisualizationRegistry
from backend.services.domain_intelligence_service import (
    get_domain_registry,
    get_kpi_registry,
    get_metric_registry,
    get_visualization_registry,
)
from backend.services.domain_profile_service import domain_profile


def test_domain_registry_resolves_known_aliases_and_defaults():
    registry = get_domain_registry()

    assert registry.resolve("Sales").name == "Sales"
    assert registry.resolve("churn").name == "Customer Churn"
    assert registry.resolve("healthcare").name == "Healthcare"
    assert registry.resolve("unknown-domain").name == "Generic Business Dataset"


def test_kpi_registry_provider_selection_returns_domain_provider():
    registry = get_kpi_registry()
    provider = registry.resolve("Sales")
    assert provider is not None
    assert provider.domain == "Sales"

    df = pd.DataFrame({"revenue": [100, 120], "cost": [60, 70], "region": ["E", "W"]})
    kpis = provider.build_kpis(df, detection={"domain": "Sales"}, classifier={})
    assert isinstance(kpis, list)
    assert any(item["label"] in {"Total Revenue", "Records"} for item in kpis)


def test_visualization_registry_selection_and_ranking():
    registry = get_visualization_registry()
    recommendation = registry.recommend_for_section("Sales", "trends", "Revenue")

    assert recommendation["ranked_chart_types"]
    assert recommendation["fallback_chart_types"]
    assert registry.rank_chart_suitability("Sales", recommendation["ranked_chart_types"][0], section_id="trends") >= 1


def test_plugin_registration_lifecycle_with_custom_registry():
    custom = DomainRegistry()

    plugin = GenericBusinessDomain(
        name="Generic Business Dataset",
        aliases=("generic",),
        profile_supplier=domain_profile,
        kpi_provider=lambda _df, _det, _cls, _ctx: [{"label": "Records", "value": 2, "format": "integer"}],
    )
    custom.register(plugin)

    assert "Generic Business Dataset" in custom.registered_domains()
    assert custom.resolve("generic").name == "Generic Business Dataset"


def test_metric_registry_lookup_returns_definition_metadata():
    registry = MetricRegistry()
    registry.register(
        MetricDefinition(
            name="Revenue",
            business_meaning="Top-line income",
            metric_category="financial",
            executive_importance="high",
            preferred_visualizations=["line", "bar"],
            benchmark_compatibility=True,
            aggregation_strategy="sum",
        )
    )

    found = registry.to_lookup_dict("total revenue")
    assert found["name"] == "Revenue"
    assert found["aggregation_strategy"] == "sum"
    assert found["preferred_visualizations"] == ["line", "bar"]


def test_global_metric_registry_is_available():
    global_registry = get_metric_registry()
    found = global_registry.to_lookup_dict("churn rate")
    assert found["name"] == "Churn Rate"
