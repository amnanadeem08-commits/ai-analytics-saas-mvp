# Internal Repository Map (Phase 1 Analysis)

Generated for Data Bot AI v1.0 Engineering Handbook.

## Counts (filesystem)

| Artifact | Count |
|----------|------:|
| `tests/**/test_*.py` | 125 |
| `backend/api/routes/*_routes.py` | 28 |
| `backend/services/*_service.py` | 89 |
| `frontend/app_pages/*_page.py` | 34+ |
| `backend/models/*.py` | 49 |
| Release gate pytest | 634 passed |

## Backend packages

`ai`, `api`, `config`, `core`, `database`, `jobs`, `logging`, `models`, `monitoring`, `performance`, `processing`, `queue`, `rag`, `registry`, `reliability`, `repositories`, `security`, `services`, `storage`, `storyboard`, `utils`, `workers`

## Mounted routers in `create_app()`

upload, dataset, analytics, insight, intelligence, visual_builder, report, theme, branding, sql_lab, dax, system, analyst, workflow, evaluation, knowledge, auth, organization, workspace, rbac, job, storage, monitoring, billing, apikey, admin, release

## Not verified mounts

- `rag_routes.py` exists with prefix `/rag` but is **not** included in `backend/main.py` `create_app()` as of the handbook generation snapshot.

## Frontend nav groups

Home · AI Workspace · Data · Analytics · AI (Legacy) · Reports · Advanced · Account · Administration · Commercial · Operations

## Test folders

admin, api, apikeys, auth, billing, database, frontend, infrastructure, jobs, load, organizations, performance, rbac, release, reliability, repositories_sqlalchemy, security, storage + root AI/analytics tests
