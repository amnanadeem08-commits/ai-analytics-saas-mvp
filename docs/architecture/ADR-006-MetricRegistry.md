# ADR-006 MetricRegistry

## Problem
Metric metadata (meaning, importance, preferred visuals) was not centrally managed.

## Decision
Create `MetricRegistry` with metric definitions and lookup utilities.

## Alternatives Considered
- Infer all metric behavior from metric names heuristically.
- Store metric metadata only in generated output payloads.

## Consequences
- Metric interpretation is reusable across dashboard, storyboard, and validation workflows.
- Registry provides a foundation for future metric suitability validator improvements.

## Future Extension Points
- Add benchmark compatibility providers.
- Add domain-specific metric override layers.
