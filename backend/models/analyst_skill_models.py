from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

ANALYST_SKILL_SCHEMA_VERSION = "1.0.0"

# Reserved empty buckets for future execution layers. Placeholders only.
# Owners:
#   tool_execution      → Actual tool invocation
#   llm_tools           → LLM tool-calling bindings
#   external_connectors → External system connectors
#   plugins             → Plugin marketplace
#   python_runtime      → Sandboxed Python execution
#   sql_execution       → Live SQL execution
#   workflow_actions    → Workflow action bindings
#   agent_skills        → Multi-agent skill routing
#   prediction_tools    → Prediction Engine tools
#   simulation_tools    → Simulation tools
#   automation_tools    → Automation Engine tools
ANALYST_SKILL_FUTURE_EXTENSION_KEYS: tuple[str, ...] = (
    "tool_execution",
    "llm_tools",
    "external_connectors",
    "plugins",
    "python_runtime",
    "sql_execution",
    "workflow_actions",
    "agent_skills",
    "prediction_tools",
    "simulation_tools",
    "automation_tools",
)


def empty_analyst_skill_future_extensions() -> dict[str, dict[str, Any]]:
    return {key: {} for key in ANALYST_SKILL_FUTURE_EXTENSION_KEYS}


class SkillCategory(str, Enum):
    analytics = "Analytics"
    reporting = "Reporting"
    visualization = "Visualization"
    business_intelligence = "Business Intelligence"
    data_access = "Data Access"
    administration = "Administration"
    metadata = "Metadata"
    developer = "Developer"


class SkillAvailability(str, Enum):
    available = "available"
    unavailable = "unavailable"
    deprecated = "deprecated"
    experimental = "experimental"


class AnalystSkill(BaseModel):
    """Catalog entry for one platform capability. Metadata only — never executes."""

    model_config = ConfigDict(extra="allow")

    skill_id: str
    skill_name: str
    category: SkillCategory
    description: str = ""
    required_inputs: list[str] = Field(default_factory=list)
    produced_outputs: list[str] = Field(default_factory=list)
    supported_modes: list[str] = Field(default_factory=list)
    required_objects: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    availability: SkillAvailability = SkillAvailability.available
    version: str = ANALYST_SKILL_SCHEMA_VERSION
    metadata: dict[str, Any] = Field(default_factory=dict)


class SkillRegistryMetadata(BaseModel):
    legacy: dict[str, Any] = Field(default_factory=dict)
    debug: dict[str, Any] = Field(default_factory=dict)
    custom: dict[str, Any] = Field(default_factory=dict)
    future_extensions: dict[str, Any] = Field(
        default_factory=empty_analyst_skill_future_extensions
    )


class AnalystSkillRegistry(BaseModel):
    """Read-only catalog of discoverable platform skills."""

    model_config = ConfigDict(extra="allow")

    registry_id: str
    schema_version: str = ANALYST_SKILL_SCHEMA_VERSION
    skills: list[AnalystSkill] = Field(default_factory=list)
    generated_at: str = ""
    metadata: SkillRegistryMetadata = Field(default_factory=SkillRegistryMetadata)
