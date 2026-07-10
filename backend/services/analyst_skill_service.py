from __future__ import annotations

from backend.models.ai_insight_models import utc_now_iso
from backend.models.analyst_skill_models import (
    ANALYST_SKILL_SCHEMA_VERSION,
    AnalystSkill,
    AnalystSkillRegistry,
    SkillAvailability,
    SkillCategory,
    SkillRegistryMetadata,
    empty_analyst_skill_future_extensions,
)

# Canonical built-in skills. Discovery metadata only — no execution bindings.
_BUILTIN_SKILL_SPECS: tuple[dict[str, object], ...] = (
    {
        "skill_id": "insight_viewer",
        "skill_name": "Insight Viewer",
        "category": SkillCategory.analytics,
        "description": "View Universal AI Insights without regenerating them.",
        "required_inputs": ["insight_id | insight_collection"],
        "produced_outputs": ["insight_view"],
        "supported_modes": ["executive", "business", "analyst", "technical", "audit"],
        "required_objects": ["insight"],
        "dependencies": [],
        "permissions": ["intelligence.read"],
    },
    {
        "skill_id": "validation_viewer",
        "skill_name": "Validation Viewer",
        "category": SkillCategory.analytics,
        "description": "View Validation Reports for existing insights.",
        "required_inputs": ["validation_id | validation_report"],
        "produced_outputs": ["validation_view"],
        "supported_modes": ["analyst", "technical", "audit"],
        "required_objects": ["validation"],
        "dependencies": ["insight_viewer"],
        "permissions": ["intelligence.read"],
    },
    {
        "skill_id": "decision_viewer",
        "skill_name": "Decision Viewer",
        "category": SkillCategory.business_intelligence,
        "description": "View Decision Intelligence recommendations.",
        "required_inputs": ["decision_id | decision_collection"],
        "produced_outputs": ["decision_view"],
        "supported_modes": ["executive", "business", "analyst", "audit"],
        "required_objects": ["decision"],
        "dependencies": ["insight_viewer", "validation_viewer"],
        "permissions": ["intelligence.read"],
    },
    {
        "skill_id": "root_cause_viewer",
        "skill_name": "Root Cause Viewer",
        "category": SkillCategory.analytics,
        "description": "View Root Cause Analysis results.",
        "required_inputs": ["root_cause_id | root_cause_collection"],
        "produced_outputs": ["root_cause_view"],
        "supported_modes": ["business", "analyst", "technical", "audit"],
        "required_objects": ["root_cause"],
        "dependencies": ["insight_viewer", "decision_viewer"],
        "permissions": ["intelligence.read"],
    },
    {
        "skill_id": "executive_reasoning_viewer",
        "skill_name": "Executive Reasoning Viewer",
        "category": SkillCategory.business_intelligence,
        "description": "View Executive Reasoning narratives and priorities.",
        "required_inputs": ["reasoning_id | reasoning_collection"],
        "produced_outputs": ["executive_reasoning_view"],
        "supported_modes": ["executive", "business", "audit"],
        "required_objects": ["executive_reasoning"],
        "dependencies": ["decision_viewer", "root_cause_viewer", "validation_viewer"],
        "permissions": ["intelligence.read"],
    },
    {
        "skill_id": "storyboard_viewer",
        "skill_name": "Storyboard Viewer",
        "category": SkillCategory.visualization,
        "description": "View Executive Storyboard slides and sections.",
        "required_inputs": ["storyboard_id | executive_storyboard"],
        "produced_outputs": ["storyboard_view"],
        "supported_modes": ["executive", "business"],
        "required_objects": ["storyboard"],
        "dependencies": ["executive_reasoning_viewer"],
        "permissions": ["intelligence.read"],
    },
    {
        "skill_id": "bundle_viewer",
        "skill_name": "Bundle Viewer",
        "category": SkillCategory.metadata,
        "description": "View Intelligence Bundle summary, statistics, and references.",
        "required_inputs": ["bundle_id | intelligence_bundle"],
        "produced_outputs": ["bundle_view"],
        "supported_modes": ["analyst", "technical", "audit"],
        "required_objects": ["intelligence_bundle"],
        "dependencies": [
            "insight_viewer",
            "validation_viewer",
            "decision_viewer",
            "root_cause_viewer",
            "executive_reasoning_viewer",
            "storyboard_viewer",
        ],
        "permissions": ["intelligence.read"],
    },
    {
        "skill_id": "registry_viewer",
        "skill_name": "Registry Viewer",
        "category": SkillCategory.metadata,
        "description": "View Intelligence Registry assets and dependency graph metadata.",
        "required_inputs": ["registry_id | intelligence_registry"],
        "produced_outputs": ["registry_view"],
        "supported_modes": ["technical", "audit", "developer"],
        "required_objects": ["intelligence_registry"],
        "dependencies": ["bundle_viewer"],
        "permissions": ["intelligence.read", "metadata.read"],
    },
    {
        "skill_id": "sql_lab",
        "skill_name": "SQL Lab",
        "category": SkillCategory.data_access,
        "description": "Discover SQL Lab capability metadata. Does not execute SQL.",
        "required_inputs": ["dataset_id", "sql_query?"],
        "produced_outputs": ["sql_lab_capability"],
        "supported_modes": ["analyst", "technical", "developer"],
        "required_objects": ["dataset"],
        "dependencies": ["dataset_explorer"],
        "permissions": ["sql_lab.read"],
        "availability": SkillAvailability.available,
    },
    {
        "skill_id": "dax_lab",
        "skill_name": "DAX Lab",
        "category": SkillCategory.data_access,
        "description": "Discover DAX Lab capability metadata. Does not execute DAX.",
        "required_inputs": ["dataset_id", "dax_expression?"],
        "produced_outputs": ["dax_lab_capability"],
        "supported_modes": ["analyst", "technical", "developer"],
        "required_objects": ["dataset"],
        "dependencies": ["dataset_explorer"],
        "permissions": ["dax_lab.read"],
    },
    {
        "skill_id": "report_builder",
        "skill_name": "Report Builder",
        "category": SkillCategory.reporting,
        "description": "Discover Report Builder capability metadata. Does not build reports.",
        "required_inputs": ["dataset_id", "report_config?"],
        "produced_outputs": ["report_builder_capability"],
        "supported_modes": ["business", "analyst"],
        "required_objects": ["dataset", "report"],
        "dependencies": ["dataset_explorer", "dashboard_viewer"],
        "permissions": ["reports.read"],
    },
    {
        "skill_id": "dashboard_viewer",
        "skill_name": "Dashboard Viewer",
        "category": SkillCategory.visualization,
        "description": "Discover Dashboard Viewer capability metadata. Does not render dashboards.",
        "required_inputs": ["dataset_id", "dashboard_id?"],
        "produced_outputs": ["dashboard_view_capability"],
        "supported_modes": ["executive", "business", "analyst"],
        "required_objects": ["dataset", "dashboard"],
        "dependencies": ["dataset_explorer"],
        "permissions": ["dashboards.read"],
    },
    {
        "skill_id": "dataset_explorer",
        "skill_name": "Dataset Explorer",
        "category": SkillCategory.data_access,
        "description": "Discover Dataset Explorer capability metadata. Does not query data.",
        "required_inputs": ["dataset_id"],
        "produced_outputs": ["dataset_explorer_capability"],
        "supported_modes": ["analyst", "technical", "developer"],
        "required_objects": ["dataset"],
        "dependencies": [],
        "permissions": ["datasets.read"],
    },
    {
        "skill_id": "metadata_explorer",
        "skill_name": "Metadata Explorer",
        "category": SkillCategory.metadata,
        "description": "Discover Metadata Explorer capability for schemas and catalogs.",
        "required_inputs": ["dataset_id?", "object_type?"],
        "produced_outputs": ["metadata_explorer_capability"],
        "supported_modes": ["technical", "audit", "developer"],
        "required_objects": ["metadata"],
        "dependencies": ["dataset_explorer", "registry_viewer"],
        "permissions": ["metadata.read"],
    },
)


def _as_skill(spec: dict[str, object]) -> AnalystSkill:
    availability = spec.get("availability", SkillAvailability.available)
    if isinstance(availability, str):
        availability = SkillAvailability(availability)
    return AnalystSkill(
        skill_id=str(spec["skill_id"]),
        skill_name=str(spec["skill_name"]),
        category=spec["category"] if isinstance(spec["category"], SkillCategory) else SkillCategory(str(spec["category"])),
        description=str(spec.get("description", "")),
        required_inputs=list(spec.get("required_inputs", [])),  # type: ignore[arg-type]
        produced_outputs=list(spec.get("produced_outputs", [])),  # type: ignore[arg-type]
        supported_modes=list(spec.get("supported_modes", [])),  # type: ignore[arg-type]
        required_objects=list(spec.get("required_objects", [])),  # type: ignore[arg-type]
        dependencies=list(spec.get("dependencies", [])),  # type: ignore[arg-type]
        permissions=list(spec.get("permissions", [])),  # type: ignore[arg-type]
        availability=availability,  # type: ignore[arg-type]
        version=str(spec.get("version", ANALYST_SKILL_SCHEMA_VERSION)),
        metadata=dict(spec.get("metadata", {})),  # type: ignore[arg-type]
    )


def register_skill(
    registry: AnalystSkillRegistry,
    skill: AnalystSkill,
    *,
    replace: bool = True,
) -> AnalystSkillRegistry:
    """Register or replace one skill catalog entry. Does not mutate the input registry."""
    copy = registry.model_copy(deep=True)
    skills = list(copy.skills)
    skill_copy = skill.model_copy(deep=True)
    existing_idx = next((i for i, item in enumerate(skills) if item.skill_id == skill_copy.skill_id), None)
    if existing_idx is None:
        skills.append(skill_copy)
    elif replace:
        skills[existing_idx] = skill_copy
    else:
        return copy
    copy.skills = skills
    return copy


def find_skill(registry: AnalystSkillRegistry, skill_id: str) -> AnalystSkill | None:
    """Return a deep copy of one skill by id, or None."""
    for skill in registry.skills:
        if skill.skill_id == skill_id:
            return skill.model_copy(deep=True)
    return None


def list_skills(
    registry: AnalystSkillRegistry,
    *,
    availability: SkillAvailability | str | None = None,
) -> list[AnalystSkill]:
    """Return deep-copied skills, optionally filtered by availability."""
    availability_value = availability.value if isinstance(availability, SkillAvailability) else availability
    results: list[AnalystSkill] = []
    for skill in registry.skills:
        if availability_value is not None and skill.availability.value != availability_value:
            continue
        results.append(skill.model_copy(deep=True))
    return results


def skills_by_category(
    registry: AnalystSkillRegistry,
    category: SkillCategory | str,
) -> list[AnalystSkill]:
    """Return deep-copied skills in one category."""
    category_value = category.value if isinstance(category, SkillCategory) else category
    return [
        skill.model_copy(deep=True)
        for skill in registry.skills
        if skill.category.value == category_value
    ]


def skills_by_object(
    registry: AnalystSkillRegistry,
    object_type: str,
) -> list[AnalystSkill]:
    """Return deep-copied skills that declare a required intelligence/platform object."""
    needle = object_type.strip().lower()
    return [
        skill.model_copy(deep=True)
        for skill in registry.skills
        if any(obj.lower() == needle for obj in skill.required_objects)
    ]


def discover_skills(
    registry: AnalystSkillRegistry,
    *,
    category: SkillCategory | str | None = None,
    object_type: str | None = None,
    mode: str | None = None,
    available_only: bool = True,
) -> list[dict[str, object]]:
    """Discover skill capabilities without executing them.

    Returns metadata cards: inputs, outputs, dependencies, supported objects.
    """
    category_value = category.value if isinstance(category, SkillCategory) else category
    mode_value = mode.strip().lower() if mode else None
    discovered: list[dict[str, object]] = []

    for skill in registry.skills:
        if available_only and skill.availability != SkillAvailability.available:
            continue
        if category_value is not None and skill.category.value != category_value:
            continue
        if object_type is not None:
            needle = object_type.strip().lower()
            if not any(obj.lower() == needle for obj in skill.required_objects):
                continue
        if mode_value is not None:
            supported = {m.lower() for m in skill.supported_modes}
            if mode_value not in supported:
                continue

        discovered.append(
            {
                "skill_id": skill.skill_id,
                "skill_name": skill.skill_name,
                "category": skill.category.value,
                "description": skill.description,
                "required_inputs": list(skill.required_inputs),
                "produced_outputs": list(skill.produced_outputs),
                "dependencies": list(skill.dependencies),
                "required_objects": list(skill.required_objects),
                "supported_modes": list(skill.supported_modes),
                "availability": skill.availability.value,
                "version": skill.version,
            }
        )
    return discovered


def validate_skills(registry: AnalystSkillRegistry) -> dict[str, object]:
    """Structural integrity report only — never modifies skills."""
    issues: list[str] = []
    seen_ids: set[str] = set()
    skill_ids = {skill.skill_id for skill in registry.skills}
    supported_categories = {item.value for item in SkillCategory}

    for skill in registry.skills:
        if not skill.skill_id:
            issues.append("Skill missing skill_id")
            continue
        if skill.skill_id in seen_ids:
            issues.append(f"Duplicate skill_id: {skill.skill_id}")
        seen_ids.add(skill.skill_id)

        if not skill.skill_name:
            issues.append(f"Missing skill_name: {skill.skill_id}")
        if skill.category.value not in supported_categories:
            issues.append(f"Unsupported category: {skill.skill_id} ({skill.category})")
        if not skill.version:
            issues.append(f"Missing version: {skill.skill_id}")

        for dep_id in skill.dependencies:
            if dep_id not in skill_ids:
                issues.append(f"Missing dependency skill: {skill.skill_id} -> {dep_id}")

    required_extensions = set(empty_analyst_skill_future_extensions().keys())
    missing_extensions = sorted(required_extensions - set(registry.metadata.future_extensions.keys()))
    if missing_extensions:
        issues.append(f"Missing future_extensions: {', '.join(missing_extensions)}")

    return {
        "valid": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "registry_id": registry.registry_id,
        "skill_count": len(registry.skills),
    }


def build_skill_registry(*, include_builtins: bool = True) -> AnalystSkillRegistry:
    """Build the read-only skill catalog. Metadata only — no execution."""
    now = utc_now_iso()
    skills: list[AnalystSkill] = []
    if include_builtins:
        skills = [_as_skill(spec) for spec in _BUILTIN_SKILL_SPECS]

    return AnalystSkillRegistry(
        registry_id=f"skill_registry_{now.replace(':', '').replace('-', '')}",
        schema_version=ANALYST_SKILL_SCHEMA_VERSION,
        skills=skills,
        generated_at=now,
        metadata=SkillRegistryMetadata(
            legacy={"schema": ANALYST_SKILL_SCHEMA_VERSION},
            debug={
                "skill_count": len(skills),
                "categories_present": sorted({s.category.value for s in skills}),
            },
            custom={},
            future_extensions=empty_analyst_skill_future_extensions(),
        ),
    )
