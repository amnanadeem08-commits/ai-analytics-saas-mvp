# Plugin-Based Analytics Architecture

## Overview
The platform now resolves domain behavior through registries and plugins, with `DomainContext` as the canonical context object.

## Diagram
```mermaid
flowchart TD
    A[Dataset DataFrame] --> B[Domain Intelligence Pipeline]
    B --> C[DomainRegistry]
    B --> D[KPIRegistry]
    B --> E[VisualizationRegistry]
    B --> F[MetricRegistry]
    C --> G[DomainPlugin]
    G --> H[DomainContext]
    D --> H
    E --> H
    F --> H
    H --> I[Dashboard Service]
    H --> J[Dashboard Spec Service]
    H --> K[Executive Storyboard Service]
    H --> L[AI Business Insight Service]
    H --> M[Intelligence Routes]
```

## Registry Hierarchy
1. `DomainRegistry`: resolves plugin by domain/alias.
2. `KPIRegistry`: resolves KPI provider by domain.
3. `VisualizationRegistry`: resolves chart policy and ranking.
4. `MetricRegistry`: resolves metric semantics and strategies.

## Plugin Lifecycle
1. Domain detection determines candidate domain.
2. `DomainRegistry` resolves plugin.
3. Plugin provides templates, policies, recommendations, and suggested questions.
4. `KPIRegistry` and `VisualizationRegistry` enrich plugin output.
5. `DomainContext` is built and serialized to backward-compatible payloads.
