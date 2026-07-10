# ADR-005 VisualizationRegistry

## Problem
Visualization recommendation logic was scattered and difficult to keep consistent across sections and domains.

## Decision
Introduce `VisualizationRegistry` to resolve policies, rank chart suitability, and provide fallback chart options.

## Alternatives Considered
- Keep chart selection in UI and service-specific helpers.
- Use one global chart ranking without domain awareness.

## Consequences
- Visualization policy becomes explicit and domain-aware.
- Section-aware recommendations can be consumed consistently.

## Future Extension Points
- Add KPI-aware scoring models and user feedback loops.
- Integrate chart performance telemetry into ranking.
