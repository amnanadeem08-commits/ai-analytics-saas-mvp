# ADR-002 DomainPolicy

## Problem
Domain language transformations and prompt routing logic were spread across services, making consistency difficult.

## Decision
Centralize language/prompt transformation into `domain_policy_service` and expose policy through `DomainContext.language_policy`.

## Alternatives Considered
- Keep policy logic in each consumer service.
- Move policy entirely into static config files without runtime module.

## Consequences
- Healthcare and other domain-specific terminology controls are uniformly applied.
- Services now consume policy rather than hardcoding substitutions.

## Future Extension Points
- Add domain policy validation tests for every registered plugin.
- Externalize policy definitions to configuration bundles.
