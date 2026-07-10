#!/usr/bin/env python3
"""Generate Data Bot AI v1.0 Engineering Handbook under /documentation.

Documentation only — does not modify business logic.
Source of truth: repository layout and known release artifacts.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "documentation"


def w(rel: str, content: str) -> None:
    path = DOC / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")
    print("wrote", path.relative_to(ROOT))


def main() -> None:
    w(
        "README.md",
        """
# Data Bot AI v1.0 — Engineering Handbook

**Official documentation package** for Data Bot AI version **1.0.0**.

This handbook is simultaneously:

| Role | Audience |
|------|----------|
| Software Engineering Documentation | Engineers |
| AI Architecture Documentation | AI/ML engineers |
| Data Science & Statistics Notes | Analysts |
| Power BI Learning Guide | BI practitioners |
| System Design Documentation | Architects |
| Portfolio Case Study | Hiring managers |
| Interview Preparation Guide | Candidates |
| Enterprise / Onboarding Manual | New team members |
| Technical Evidence | Auditors / reviewers |

## Version & Evidence

| Item | Value | Source |
|------|-------|--------|
| Product version | `1.0.0` | `backend/core/config.py` |
| App name | AI Analytics SaaS MVP (Data Bot AI) | settings |
| Test suite (release gate) | **634 passed** | Release verification 2026-07-10 |
| Test files (`test_*.py`) | **125** | `tests/` |
| Backend services (`*_service.py`) | **89** | `backend/services/` |
| API route modules | **28** | `backend/api/routes/` |
| Streamlit page modules | **34+** | `frontend/app_pages/` |
| Domain models | **49** | `backend/models/` |
| Git tag | `v1.0.0` | GitHub release |

## How to read this handbook

1. Start with [01 Executive Summary](01_executive_summary/README.md)
2. Study [02 Architecture](02_architecture/README.md)
3. Drill into folders, workflows, API, frontend as needed
4. Use Learning / Interview / Portfolio sections for career prep

## Documentation standards

See [20 Standards](20_standards/README.md).

**Rule:** Never invent features. Items not confirmed in the repository are labeled **Not verified**.

## Export formats

See [19 Formats](19_formats/README.md) and `scripts/export_handbook.py`.

## Repository map (top level)

```
ai-analytics-saas-mvp/
├── backend/          # FastAPI application
├── frontend/         # Streamlit UI
├── tests/            # pytest suite
├── docs/             # ADR + release guides
├── documentation/    # THIS handbook (v1.0 master docs)
├── release/          # v1.0 / v1.0-rc checklists
├── docker/           # Compose + Dockerfiles
├── deploy/           # Deploy scripts
├── alembic/          # DB migrations
├── data/             # Local data (samples committed; runtime data gitignored)
└── requirements*.txt # Pinned dependencies
```
""",
    )

    # ---- 01 Executive Summary ----
    w(
        "01_executive_summary/README.md",
        """
# 01 — Executive Summary

## What is Data Bot AI?

Data Bot AI (repository product name: **AI Analytics SaaS MVP**) is a **local-first analytics and AI analyst platform**. Users upload CSV/Excel datasets, explore KPIs and charts, run natural-language analysis through an AI Analyst runtime, manage knowledge/RAG, execute workflows and background jobs, and operate the platform with auth, RBAC, storage, monitoring, and commercial controls.

**Verified version:** `1.0.0` (`backend/core/config.py`, GitHub tag `v1.0.0`).

## Business problem solved

Organizations need a single place to:

1. Ingest tabular business data without a heavy BI stack
2. Produce dashboards, KPIs, and executive narratives quickly
3. Ask questions in natural language with governed AI workflows
4. Keep multi-tenant identity, storage, jobs, and observability in one product

## Target users

| Persona | Needs (verified by UI/API surface) |
|---------|-------------------------------------|
| Business analyst | Upload, clean, dashboard, charts, reports |
| Data / AI practitioner | AI Analyst, workflows, knowledge, evaluation |
| Platform admin | Orgs, RBAC, health, metrics, admin dashboard |
| Commercial operator | Plans, usage, API keys, invoices (no live payment gateway) |

## Major capabilities (verified)

- Dataset upload (CSV/XLSX), cleaning, profiling, analytics dashboards
- Charts, pivot, visual builder, SQL Lab, DAX Studio
- Reports (PDF/PPT), storyboard, geospatial/location insights
- AI Analyst (`/api/v1`), workflows, evaluation, knowledge ingestion
- RAG-related services and `/rag` route module (**mount in `main.py`: Not verified** — `rag_routes.py` exists; not listed in `create_app()` includes as of v1.0.0)
- Auth (JWT), organizations, workspaces, RBAC
- Jobs/queue/workers, object storage lifecycle
- Monitoring, metrics, release validation
- Billing plans/usage/API keys/admin (in-memory commercial stores for MVP)

## Architecture overview

```mermaid
flowchart TB
  UI[Streamlit Frontend]
  API[FastAPI backend.main]
  SVC[Service Layer]
  REPO[Repositories]
  DB[(SQLite/Postgres)]
  STORE[Object Storage local/S3 stub]
  Q[Queue memory/Redis]
  AI[AI Runtime: LLM Agents RAG Workflow]

  UI -->|HTTP JSON| API
  API --> SVC
  SVC --> REPO --> DB
  SVC --> STORE
  SVC --> Q
  SVC --> AI
```

## Technology stack (pinned)

| Layer | Technology | Pin evidence |
|-------|------------|--------------|
| API | FastAPI 0.115.6, Uvicorn 0.32.1 | `requirements.txt` |
| UI | Streamlit 1.40.2 | `requirements.txt` |
| Data | pandas 2.2.3, Plotly 6.8.0 | `requirements.txt` |
| ORM | SQLAlchemy 2.0.50, Alembic 1.14.0 | `requirements.txt` |
| Queue | redis 5.2.1 (optional) | `requirements.txt` |
| Export | reportlab, python-pptx, openpyxl, Pillow, kaleido, matplotlib | `requirements.txt` |
| Auth crypto | Custom JWT/HMAC + PBKDF2 (stdlib) | `backend/security/` |

## System lifecycle

1. **Develop** on `main`
2. **Test** with pytest (634 passed at v1.0.0 gate)
3. **Deploy** API (`uvicorn backend.main:app`) + Streamlit + optional worker
4. **Operate** via `/api/v1/live`, `/ready`, monitoring, release validation
5. **Maintain** hotfixes on `release/v1.0`

## Deployment model

- Single-node / Docker Compose (`docker/`)
- Local filesystem storage by default
- Optional PostgreSQL + Redis
- **Not verified / out of scope for 1.0:** Kubernetes manifests, live billing gateway, enterprise SSO

## Advantages

- End-to-end product surface (data → AI → ops → commercial)
- Local-first MVP with production hardening (Sprint 8.7)
- Large automated test suite
- Documented release gates and known limitations

## Limitations

See root `KNOWN_ISSUES.md` (KI-001…KI-008): no payment gateway, some in-memory stores, S3 stub, no K8s, no SSO, permissive CORS defaults, JWT secret must be set in production.

## Future roadmap

See root `ROADMAP.md`: billing gateway, SQL commercial stores, S3 completion, K8s, SSO, forecast plugins, UI polish.
""",
    )

    # ---- 02 Architecture ----
    w(
        "02_architecture/README.md",
        """
# 02 — Architecture Handbook

## Layer diagram

```mermaid
flowchart TB
  subgraph Presentation
    ST[Streamlit pages + clients]
  end
  subgraph API
    R[Route modules]
    MW[Middleware: CORS GZip Security RateLimit CSRF Monitoring Auth]
  end
  subgraph Domain
    S[Services ~89 modules]
    M[Pydantic / domain models]
  end
  subgraph Infrastructure
    REP[Repositories memory/SQLAlchemy]
    STG[Storage providers]
    QUE[Queue backends]
    MON[Monitoring + Logging]
    REL[Reliability: circuit retry timeout shutdown]
    PERF[Performance: cache pagination streaming]
  end
  ST --> R --> S
  R --> MW
  S --> M
  S --> REP
  S --> STG
  S --> QUE
  S --> MON
  S --> REL
  S --> PERF
```

## Middleware order (`backend/main.py`)

Last added = outermost. Approximate request path:

1. CORSMiddleware (env-driven origins)
2. GZipMiddleware (min 500 bytes)
3. SecurityHeadersMiddleware
4. RateLimitMiddleware
5. CSRFMiddleware (optional via `CSRF_ENABLED`)
6. MonitoringMiddleware
7. AuthContextMiddleware (non-blocking bearer attach)

Lifespan: graceful shutdown via `backend.reliability.shutdown`.

## Frontend architecture

- Entry: `frontend/streamlit_app.py`
- Navigation: `_NAV_GROUPS` sidebar expanders (Home, AI Workspace, Data, Analytics, AI Legacy, Reports, Advanced, Account, Administration, Commercial, Operations)
- Pages: `frontend/app_pages/*_page.py`
- API clients: `frontend/api/*_client.py` + legacy `frontend/api_client/`
- Session: `frontend/utils/session_state.py`, `auth_state.py`

## Backend packages (verified folders)

| Package | Purpose |
|---------|---------|
| `api/` | Routes, middleware, auth deps, error handlers |
| `services/` | Business logic |
| `models/` | Domain schemas |
| `database/` | Engine, session, SQLAlchemy models |
| `repositories/` | Persistence abstraction |
| `storage/` | Object storage abstraction |
| `queue/` + `jobs/` + `workers/` | Async execution |
| `monitoring/` + `logging/` | Observability |
| `security/` | JWT, passwords, hardening |
| `performance/` + `reliability/` | Production readiness |
| `config/` | Typed settings loader |
| `processing/` | Cleaning, profiling, schema |
| `registry/` | Domain/KPI/visualization registries |
| `ai/`, `rag/`, `storyboard/` | Supporting AI/BI packages |

## AI Analyst Runtime (verified services)

Key modules (exist under `backend/services/`):

- `ai_analyst_service.py`, `ai_analyst_runtime_service.py`
- `planning_service.py`, `tool_selection_service.py`, `tool_registry_service.py`
- `agent_service.py`, `memory_service.py`
- `rag_service.py`, `embedding_service.py`, `vector_store_service.py`, `context_retrieval_service.py`
- `workflow_engine_service.py`
- `evaluation_service.py`, `ai_validation_service.py`, `output_validation_service.py`
- `llm_service.py` + `providers/` (openai, anthropic, local)

## Auth / RBAC / Orgs

- Auth: `auth_service.py`, `security/jwt_service.py`, `password_service.py`, routes `/api/v1/auth`
- Orgs/workspaces: `organization_service.py`, `workspace_service.py`
- RBAC: `rbac_service.py` (`evaluate_access`, `has_permission`)

## Jobs / Storage / Monitoring / Commercial

- Jobs: `job_service.py`, queue factory (memory/redis), workers CLI
- Storage: `storage_service.py`, local provider, S3 stub
- Monitoring: health, metrics, tracing, collectors
- Commercial: `billing_service`, `subscription_service`, `usage_service`, `api_key_service`, `admin_service`

## Sequence: authenticated API call

```mermaid
sequenceDiagram
  participant U as Streamlit
  participant M as Middleware
  participant R as Route
  participant S as Service
  U->>M: Bearer token + request
  M->>M: Rate limit / CSRF / headers / metrics
  M->>R: Auth context attached if valid
  R->>S: Domain operation
  S-->>R: Result / AuthError / ServiceError
  R-->>U: JSON response
```

## Dependency diagram (high level)

```mermaid
flowchart LR
  streamlit --> fastapi
  fastapi --> services
  services --> sqlalchemy
  services --> pandas
  services --> storage
  services --> queue
  services --> llm_providers
```

## Folder diagram

See [03 Folder Documentation](../03_folders/README.md).

## Class diagrams

Practical class diagrams are limited because many stores are dict-backed services rather than rich OOP hierarchies. Repository interfaces live in `backend/repositories/interfaces.py` with memory and SQLAlchemy implementations — see Database Handbook.
""",
    )

    w(
        "02_architecture/COMPONENT_CATALOG.md",
        """
# Component Catalog

## API route modules (28)

| Module | Prefix (from source) | Mounted in main.py |
|--------|----------------------|--------------------|
| upload_routes | (upload) | Yes |
| dataset_routes | `/datasets` | Yes |
| analytics_routes | `/analytics` | Yes |
| insight_routes | `/insights` | Yes |
| intelligence_routes | `/intelligence` | Yes |
| visual_builder_routes | `/visual-builder` | Yes |
| report_routes | `/report` | Yes |
| theme_routes | `/themes` | Yes |
| branding_routes | `/branding` | Yes |
| sql_lab_routes | `/sql-lab` | Yes |
| dax_routes | `/dax` | Yes |
| system_routes | `/api/v1` | Yes |
| analyst_routes | `/api/v1` | Yes |
| workflow_routes | `/api/v1` | Yes |
| evaluation_routes | `/api/v1` | Yes |
| knowledge_routes | `/api/v1` | Yes |
| auth_routes | `/api/v1/auth` | Yes |
| organization_routes | `/api/v1/organizations` | Yes |
| workspace_routes | `/api/v1/workspaces` | Yes |
| rbac_routes | `/api/v1` | Yes |
| job_routes | `/api/v1/jobs` | Yes |
| storage_routes | `/api/v1/storage` | Yes |
| monitoring_routes | `/api/v1` | Yes |
| billing_routes | `/api/v1/billing` | Yes |
| apikey_routes | `/api/v1/api-keys` | Yes |
| admin_routes | `/api/v1/admin` | Yes |
| release_routes | `/api/v1/release` | Yes |
| rag_routes | `/rag` | **Not verified** (file exists; not in `create_app()` includes) |

## Service domains (selected)

See `backend/services/` for the full list of 89 `*_service.py` files spanning analytics, AI, forecast, commercial, and platform domains.
""",
    )

    print("core docs batch 1 done")


if __name__ == "__main__":
    main()
