# ADR-003 DomainRegistry

## Problem
Domain behavior routing via if/elif does not scale as supported domains increase.

## Decision
Introduce plugin-based `DomainRegistry` with a common `DomainPlugin` interface and resolvable aliases.

## Alternatives Considered
- Continue domain profile lookups with branching in each service.
- Use dynamic imports without a formal plugin contract.

## Consequences
- Adding a domain becomes registration + plugin implementation.
- Existing domains can share profile-backed plugin behavior by default.

## Future Extension Points
- Load plugins from external packages.
- Add plugin capability declarations and health checks.
