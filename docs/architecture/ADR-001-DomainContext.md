# ADR-001 DomainContext

## Problem
Domain metadata was passed between services as loosely coupled dictionaries, which increased key drift risk and duplicated interpretation logic.

## Decision
Introduce a strongly typed `DomainContext` model as the canonical object produced by Domain Intelligence and consumed by downstream services.

## Alternatives Considered
- Keep dictionary payloads and enforce conventions with tests only.
- Use Pydantic models only at API boundaries and keep dictionaries internally.

## Consequences
- Internal contracts are clearer and easier to evolve.
- Adapters are required to preserve backward compatibility for existing dictionary payloads.

## Future Extension Points
- Add richer RAG integration providers on `DomainContext`.
- Add versioned `DomainContext` schema migration if required.
