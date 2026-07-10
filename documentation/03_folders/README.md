# 03 — Folder Documentation

## Top-level

| Folder | Purpose | Inputs | Outputs | Extension points |
|--------|---------|--------|---------|------------------|
| `backend/` | FastAPI app + domain logic | HTTP, env, files | JSON, files, metrics | New routes/services |
| `frontend/` | Streamlit UI | User actions, API | Rendered pages | New pages/clients |
| `tests/` | Automated verification | Fixtures, TestClient | Pass/fail | New test modules |
| `docs/` | ADRs + release guides | Authors | Markdown | New ADRs |
| `documentation/` | This Engineering Handbook | Repo analysis | Handbook | New chapters |
| `release/` | Checklists for v1.0 / RC | Release process | Gate evidence | Patch checklists |
| `docker/` | Compose + Dockerfiles | Env template | Containers | New services |
| `deploy/` | Deploy helper scripts | Ops | Process starts | New scripts |
| `alembic/` | SQL migrations | Models | Schema versions | New revisions |
| `data/` | Runtime + samples | Uploads | Datasets/storage | New samples |
| `scripts/` | Tooling (handbook gen/export) | — | Artifacts | New tools |

## Important backend files

| Path | Responsibility |
|------|----------------|
| `backend/main.py` | App factory, middleware, router includes, lifespan |
| `backend/core/config.py` | Paths, version, upload limits, ensure dirs |
| `backend/api/error_handlers.py` | HTTP error mapping |
| `backend/api/auth_dependencies.py` | Current user / permission deps |
| `backend/database/session.py` | Engine + pooling + session scope |
| `backend/repositories/registry.py` | Backend switching memory/SQL |

## Important frontend files

| Path | Responsibility |
|------|----------------|
| `frontend/streamlit_app.py` | Entry, nav groups, page routing |
| `frontend/utils/session_state.py` | Session keys |
| `frontend/utils/auth_state.py` | Auth session helpers |
| `frontend/api/*.py` | Typed HTTP clients |

## Best practices

- Keep business logic in services, not routes
- Prefer repository interfaces for persistence
- Paginate list endpoints (`performance.pagination`)
- Do not commit secrets or `data/*.db`
