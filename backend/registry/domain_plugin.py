from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd


class DomainPlugin(ABC):
    name: str
    aliases: tuple[str, ...] = ()

    # Optional placeholders for future RAG integration providers.
    knowledge_pack_id: str | None = None
    benchmark_provider: str | None = None
    glossary_provider: str | None = None
    executive_guidance_provider: str | None = None

    @abstractmethod
    def build_context(self, *, detection: dict[str, Any], classifier: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_kpis(self, df: pd.DataFrame, *, detection: dict[str, Any], classifier: dict[str, Any]) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_storyboard(self, *, classifier: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_dashboard(self, *, classifier: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_language_policy(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_visualization_policy(self, *, classifier: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_recommendations(self, *, classifier: dict[str, Any], profile: dict[str, Any]) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def get_suggested_questions(self, *, classifier: dict[str, Any], profile: dict[str, Any]) -> list[str]:
        raise NotImplementedError
