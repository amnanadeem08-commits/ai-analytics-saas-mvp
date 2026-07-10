from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from backend.models.ai_insight_models import ValidationStatus

VALIDATION_ENGINE_VERSION = "1.0.0"


class CheckStatus(str, Enum):
    passed = "passed"
    failed = "failed"
    warning = "warning"


class ValidationFinding(BaseModel):
    validator: str
    check_id: str
    status: CheckStatus
    message: str


class ValidatorResult(BaseModel):
    """Independent output from a single validator module."""

    validator: str
    passed_checks: list[str] = Field(default_factory=list)
    failed_checks: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    findings: list[ValidationFinding] = Field(default_factory=list)
    score: float = 100.0

    @property
    def has_failures(self) -> bool:
        return bool(self.failed_checks)


class ValidationReport(BaseModel):
    overall_status: ValidationStatus
    score: float = Field(ge=0.0, le=100.0)
    passed_checks: list[str] = Field(default_factory=list)
    failed_checks: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    findings: list[ValidationFinding] = Field(default_factory=list)
    validator_version: str = VALIDATION_ENGINE_VERSION
    validated_at: str
