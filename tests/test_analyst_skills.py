from __future__ import annotations

from backend.models.analyst_skill_models import (
    ANALYST_SKILL_FUTURE_EXTENSION_KEYS,
    AnalystSkill,
    SkillAvailability,
    SkillCategory,
)
from backend.services.analyst_skill_service import (
    build_skill_registry,
    discover_skills,
    find_skill,
    list_skills,
    register_skill,
    skills_by_category,
    skills_by_object,
    validate_skills,
)

EXPECTED_SKILL_IDS = {
    "insight_viewer",
    "validation_viewer",
    "decision_viewer",
    "root_cause_viewer",
    "executive_reasoning_viewer",
    "storyboard_viewer",
    "bundle_viewer",
    "registry_viewer",
    "sql_lab",
    "dax_lab",
    "report_builder",
    "dashboard_viewer",
    "dataset_explorer",
    "metadata_explorer",
}


def test_skill_registration_and_builtins():
    registry = build_skill_registry()
    ids = {skill.skill_id for skill in registry.skills}
    assert EXPECTED_SKILL_IDS.issubset(ids)
    assert len(registry.skills) == 14
    assert validate_skills(registry)["valid"] is True

    custom = AnalystSkill(
        skill_id="custom_skill",
        skill_name="Custom Skill",
        category=SkillCategory.developer,
        description="Test skill",
        required_inputs=["x"],
        produced_outputs=["y"],
        supported_modes=["technical"],
        required_objects=["metadata"],
        dependencies=["dataset_explorer"],
        permissions=["metadata.read"],
        availability=SkillAvailability.experimental,
        metadata={"note": "catalog-only"},
    )
    updated = register_skill(registry, custom)
    assert registry.skills == build_skill_registry().skills or len(registry.skills) == 14
    assert find_skill(updated, "custom_skill") is not None
    assert find_skill(updated, "custom_skill").metadata["note"] == "catalog-only"


def test_discovery():
    registry = build_skill_registry()
    discovered = discover_skills(registry)
    assert len(discovered) == 14
    card = next(item for item in discovered if item["skill_id"] == "decision_viewer")
    assert card["required_inputs"]
    assert card["produced_outputs"]
    assert "insight_viewer" in card["dependencies"]
    assert "decision" in card["required_objects"]

    bi_only = discover_skills(registry, category=SkillCategory.business_intelligence)
    assert bi_only
    assert all(item["category"] == SkillCategory.business_intelligence.value for item in bi_only)

    decision_skills = discover_skills(registry, object_type="decision")
    assert any(item["skill_id"] == "decision_viewer" for item in decision_skills)

    exec_mode = discover_skills(registry, mode="executive")
    assert all("executive" in [m.lower() for m in item["supported_modes"]] for item in exec_mode)


def test_category_grouping():
    registry = build_skill_registry()
    analytics = skills_by_category(registry, SkillCategory.analytics)
    assert {s.skill_id for s in analytics} >= {
        "insight_viewer",
        "validation_viewer",
        "root_cause_viewer",
    }
    reporting = skills_by_category(registry, "Reporting")
    assert any(s.skill_id == "report_builder" for s in reporting)
    assert skills_by_category(registry, SkillCategory.administration) == []


def test_dependency_and_object_lookup():
    registry = build_skill_registry()
    bundle = find_skill(registry, "bundle_viewer")
    assert bundle is not None
    assert "storyboard_viewer" in bundle.dependencies
    assert "insight_viewer" in bundle.dependencies

    insight_skills = skills_by_object(registry, "insight")
    assert any(s.skill_id == "insight_viewer" for s in insight_skills)

    dataset_skills = skills_by_object(registry, "dataset")
    assert {s.skill_id for s in dataset_skills} >= {
        "sql_lab",
        "dax_lab",
        "dataset_explorer",
        "dashboard_viewer",
        "report_builder",
    }


def test_availability():
    registry = build_skill_registry()
    available = list_skills(registry, availability=SkillAvailability.available)
    assert len(available) == 14

    experimental = AnalystSkill(
        skill_id="exp_skill",
        skill_name="Experimental",
        category=SkillCategory.developer,
        availability=SkillAvailability.experimental,
        permissions=["metadata.read"],
    )
    updated = register_skill(registry, experimental)
    assert len(list_skills(updated, availability="available")) == 14
    assert len(list_skills(updated, availability=SkillAvailability.experimental)) == 1
    assert all(item["availability"] == "available" for item in discover_skills(updated, available_only=True))
    assert any(item["skill_id"] == "exp_skill" for item in discover_skills(updated, available_only=False))


def test_validation_and_broken_dependency():
    registry = build_skill_registry()
    assert validate_skills(registry)["valid"] is True

    broken = AnalystSkill(
        skill_id="broken_skill",
        skill_name="Broken",
        category=SkillCategory.developer,
        dependencies=["does_not_exist"],
        permissions=["metadata.read"],
    )
    updated = register_skill(registry, broken)
    result = validate_skills(updated)
    assert result["valid"] is False
    assert any("Missing dependency skill" in issue for issue in result["issues"])

    duplicate = registry.model_copy(deep=True)
    duplicate.skills = list(duplicate.skills) + [duplicate.skills[0].model_copy(deep=True)]
    dup_result = validate_skills(duplicate)
    assert dup_result["valid"] is False
    assert any("Duplicate skill_id" in issue for issue in dup_result["issues"])


def test_metadata_and_future_buckets():
    registry = build_skill_registry()
    for key in ANALYST_SKILL_FUTURE_EXTENSION_KEYS:
        assert key in registry.metadata.future_extensions
        assert registry.metadata.future_extensions[key] == {}
    assert "tool_execution" in registry.metadata.future_extensions
    assert "prediction_tools" in registry.metadata.future_extensions
    assert registry.metadata.debug["skill_count"] == 14

    skill = find_skill(registry, "sql_lab")
    assert skill is not None
    assert "execute" not in skill.description.lower() or "does not execute" in skill.description.lower()


def test_immutability():
    registry = build_skill_registry()
    snapshot = registry.model_dump()
    found = find_skill(registry, "insight_viewer")
    assert found is not None
    found.skill_name = "mutated"
    listed = list_skills(registry)
    listed[0].skill_name = "mutated_list"
    discover_skills(registry)
    skills_by_category(registry, SkillCategory.analytics)
    skills_by_object(registry, "dataset")
    validate_skills(registry)
    assert registry.model_dump() == snapshot

    custom = AnalystSkill(
        skill_id="temp",
        skill_name="Temp",
        category=SkillCategory.developer,
    )
    register_skill(registry, custom)
    assert registry.model_dump() == snapshot
