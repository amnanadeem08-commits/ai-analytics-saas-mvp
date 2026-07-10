from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

PROMPT_SCHEMA_VERSION = "1.0.0"


class PromptType(str, Enum):
    analyst_prompt = "analyst_prompt"
    planner_prompt = "planner_prompt"
    insight_prompt = "insight_prompt"
    reporting_prompt = "reporting_prompt"
    validation_prompt = "validation_prompt"


class PromptTemplate(BaseModel):
    model_config = ConfigDict(extra="allow")

    prompt_id: str
    prompt_type: PromptType
    name: str
    template: str
    required_variables: list[str] = Field(default_factory=list)
    description: str = ""
    version: str = "1.0.0"
    enabled: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class RenderedPrompt(BaseModel):
    model_config = ConfigDict(extra="allow")

    prompt_id: str
    prompt_type: str = ""
    rendered_text: str = ""
    variables_used: list[str] = Field(default_factory=list)
    missing_variables: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
