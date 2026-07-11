# PROJECT_STATUS

> Auto-maintained by `python pios/tools/refresh_status.py`. Last refresh: 2026-07-11 15:25 UTC

## Snapshot

| Field | Value |
|-------|-------|
| Product | Data Bot AI (AI Analytics SaaS MVP) |
| Current version | `1.0.0` (from `backend/core/config.py`) |
| Current sprint | Current Sprint — COMPLETE: E2E Smoke with Real Datasets |
| Git tag | `v1.0.0` |
| Test files (`test_*.py`) | **132** |
| Route modules | **28** |
| Service modules (`*_service.py`) | **89** |
| Known issues | **9** (see `KNOWN_ISSUES.md`) |
| Technical debt items | **11** (see `TECHNICAL_DEBT.md`) |

## Route modules

- `admin_routes.py`
- `analyst_routes.py`
- `analytics_routes.py`
- `apikey_routes.py`
- `auth_routes.py`
- `billing_routes.py`
- `branding_routes.py`
- `dataset_routes.py`
- `dax_routes.py`
- `evaluation_routes.py`
- `insight_routes.py`
- `intelligence_routes.py`
- `job_routes.py`
- `knowledge_routes.py`
- `monitoring_routes.py`
- `organization_routes.py`
- `rag_routes.py`
- `rbac_routes.py`
- `release_routes.py`
- `report_routes.py`
- `sql_lab_routes.py`
- `storage_routes.py`
- `system_routes.py`
- `theme_routes.py`
- `upload_routes.py`
- `visual_builder_routes.py`
- `workflow_routes.py`
- `workspace_routes.py`

## Completed features (v1.0)

- Dataset upload/cleaning/profiling/analytics dashboards
- Charts, pivot, visual builder, SQL Lab, DAX Studio
- Reports (PDF/PPT), storyboard, geospatial insights
- AI Analyst (`/api/v1`), workflows, evaluation, knowledge ingestion
- Auth (JWT), orgs, workspaces, RBAC
- Jobs/queue/workers, object storage lifecycle
- Monitoring, metrics, release validation
- Billing plans/usage/API keys/admin (in-memory commercial stores)

## Remaining roadmap

See [`../01_vision/ROADMAP.md`](../01_vision/ROADMAP.md)

## Next sprint recommendation

**Confirm / retag `v1.0.0` and beta launch on operator-created `release/1.0`** (feature freeze: bug fixes only). Commit pending production-hardening work first if desired.

Run `python pios/tools/recommend_sprint.py` for ranked detail.
