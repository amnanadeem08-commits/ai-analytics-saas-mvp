# ADR-004 KPIRegistry

## Problem
KPI selection rules were mixed into multiple services and not modular per domain.

## Decision
Create `KPIRegistry` with domain providers returning KPI definitions and calculations.

## Alternatives Considered
- Keep KPI rules in Domain Intelligence service only.
- Encode KPIs in static profile metadata without provider behavior.

## Consequences
- KPI provider selection is centralized and testable.
- Domain-specific KPI logic can be replaced independently.

## Future Extension Points
- Add provider metadata for executive importance and calculation hints.
- Support hybrid providers backed by benchmarks or external engines.
