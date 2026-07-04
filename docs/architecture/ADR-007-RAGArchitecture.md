# ADR-007 RAG Architecture Preparation

## Problem
Future domain-aware RAG requires standardized hooks for knowledge packs, benchmarks, glossary, and guidance providers.

## Decision
Reserve optional placeholders on `DomainContext` and `DomainPlugin`:
- `knowledge_pack_id`
- `benchmark_provider`
- `glossary_provider`
- `executive_guidance_provider`

## Alternatives Considered
- Delay all RAG-related fields until implementation starts.
- Introduce a separate RAG context object disconnected from domain context.

## Consequences
- Current architecture is RAG-ready without implementing retrieval now.
- Backward compatibility remains intact because fields are optional placeholders.

## Future Extension Points
- Implement knowledge pack resolution by domain plugin.
- Add benchmark retrieval and glossary APIs.
- Add secure domain-specific executive guidance prompts.
