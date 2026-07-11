# Dependency Rules

Machine-checked rules live in [`../MANIFEST.yaml`](../MANIFEST.yaml) under `dependency_rules`. Run:

```bash
python pios/tools/arch_check.py
```

## Allowed direction

```text
frontend → (HTTP) → backend.api.routes → backend.services → backend.repositories|storage|queue|rag
```

## Hard bans

| ID | Rule |
|----|------|
| FE_NO_BACKEND_SERVICES | `frontend/` must not import `backend.services` |
| FE_NO_BACKEND_REPOS | `frontend/` must not import `backend.repositories` |
| SERVICES_NO_STREAMLIT | `backend/services/` must not import `streamlit` |
| SERVICES_NO_FRONTEND | `backend/` must not import `frontend` |

### Known legacy violation (do not extend)

- `frontend/app_pages/ai_insights_page.py` imports `backend.services.*` — tracked as **TD-010**. New code must use HTTP API clients instead.

## Advisory

| ID | Rule |
|----|------|
| ROUTES_THIN | `backend/api/routes/` should avoid direct `backend.repositories` imports (prefer services) |

## Plugin / registry note

Domain behavior flows through registries (`DomainRegistry`, `KPIRegistry`, `VisualizationRegistry`, `MetricRegistry`) into `DomainContext` — see ADRs 001–007.
