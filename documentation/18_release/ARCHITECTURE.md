# Architecture Guide — v1.0 RC

## Overview

AI Analytics SaaS MVP is a local-first analytics platform with a FastAPI backend, Streamlit frontend, and modular service architecture introduced across Sprints 7.x–8.7.

## Layers

| Layer | Location | Responsibility |
|-------|----------|----------------|
| API Gateway | `backend/api/routes/` | HTTP endpoints, auth dependencies |
| Services | `backend/services/` | Business logic |
| Models | `backend/models/` | Domain DTOs / Pydantic schemas |
| Persistence | `backend/repositories/`, `backend/database/` | SQLAlchemy + in-memory adapters |
| Storage | `backend/storage/` | Object storage abstraction |
| Queue / Jobs | `backend/queue/`, `backend/jobs/` | Background execution |
| Performance | `backend/performance/` | Cache, pagination, streaming (8.7) |
| Security | `backend/security/` | JWT, headers, rate limits, CSRF (8.7) |
| Reliability | `backend/reliability/` | Shutdown, retries, circuit breakers (8.7) |
| Monitoring | `backend/monitoring/` | Health, metrics, tracing (8.5) |

## Request Flow

```
Client → Security middleware → Monitoring → Auth context → Route → Service → Repository/Storage
```

## Multi-tenancy

Organizations and workspaces scope data. RBAC evaluates permissions at system, organization, and workspace levels.

## AI Runtime

Workflow engine orchestrates analyst sessions, RAG retrieval, evaluation, and intelligence bundles without coupling to HTTP.

## Deployment Topology (MVP)

Single-node deployment: API process + optional worker process + local/SQLite or PostgreSQL storage. Redis optional for queue scaling.
