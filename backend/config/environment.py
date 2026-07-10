from __future__ import annotations

from enum import Enum


class EnvironmentProfile(str, Enum):
    development = "development"
    testing = "testing"
    production = "production"

    @classmethod
    def from_string(cls, value: str) -> "EnvironmentProfile":
        normalized = (value or "development").strip().lower()
        for member in cls:
            if member.value == normalized:
                return member
        return cls.development

    @property
    def is_production(self) -> bool:
        return self is EnvironmentProfile.production

    @property
    def is_testing(self) -> bool:
        return self is EnvironmentProfile.testing

    @property
    def is_development(self) -> bool:
        return self is EnvironmentProfile.development
