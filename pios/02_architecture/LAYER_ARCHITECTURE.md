# Layer Architecture

```mermaid
flowchart TB
  subgraph Presentation
    ST[Streamlit pages + clients]
  end
  subgraph API
    R[Route modules]
    MW[Middleware]
  end
  subgraph Domain
    S[Services]
    M[Models]
  end
  subgraph Infrastructure
    REP[Repositories]
    STG[Storage]
    QUE[Queue]
    MON[Monitoring]
  end
  ST --> R --> S
  R --> MW
  S --> M
  S --> REP
  S --> STG
  S --> QUE
  S --> MON
```

## Layer rules

1. **Presentation** talks to the API via HTTP clients; no direct DB/storage access for server-backed features.
2. **Routes** are thin: validate input, call services, return responses.
3. **Services** own business logic and orchestrate repos/storage/AI.
4. **Repositories / storage / queue** are infrastructure behind interfaces when possible.
5. **Registries/plugins** resolve domain behavior (`DomainContext` canonical).

Deep reference: [`documentation/02_architecture/README.md`](../../documentation/02_architecture/README.md), [`docs/architecture/README.md`](../../docs/architecture/README.md)
