from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import pandas as pd


@dataclass(slots=True)
class KPIProvider:
    domain: str
    aliases: tuple[str, ...] = field(default_factory=tuple)

    def build_kpis(
        self,
        df: pd.DataFrame,
        *,
        detection: dict[str, Any],
        classifier: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        del detection, classifier, context
        return []


@dataclass(slots=True)
class FunctionKPIProvider(KPIProvider):
    handler: Callable[[pd.DataFrame, dict[str, Any], dict[str, Any], dict[str, Any] | None], list[dict[str, Any]]] | None = None

    def build_kpis(
        self,
        df: pd.DataFrame,
        *,
        detection: dict[str, Any],
        classifier: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        if not self.handler:
            return []
        return self.handler(df, detection, classifier, context)


class KPIRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, KPIProvider] = {}
        self._alias_index: dict[str, str] = {}

    def register(self, provider: KPIProvider) -> None:
        domain_key = provider.domain.strip()
        self._providers[domain_key] = provider
        self._alias_index[domain_key.lower()] = domain_key
        for alias in provider.aliases:
            self._alias_index[alias.strip().lower()] = domain_key

    def resolve(self, domain: str | None) -> KPIProvider | None:
        if not domain:
            return self._providers.get("Generic Business Dataset")
        key = self._alias_index.get(str(domain).strip().lower(), str(domain).strip())
        return self._providers.get(key) or self._providers.get("Generic Business Dataset")

    def registered_domains(self) -> list[str]:
        return sorted(self._providers)
