# 12 — Pictorial Evidence

Automated UI screenshots were **not captured in this documentation generation run** (headless Streamlit screenshot automation: **Not verified** in repo tooling).

## Manual screenshot checklist

For each item: capture PNG into `documentation/assets/screenshots/`.

| # | Title | Purpose | What must be visible | Proves |
|---|-------|---------|----------------------|--------|
| 1 | Login | Auth | Email/password form | Auth UI |
| 2 | Register | Auth | Registration form | Signup |
| 3 | Home / Dashboard | Analytics | KPI cards or overview | Core analytics |
| 4 | AI Analyst | AI | Query box + response | Analyst runtime |
| 5 | Workflow Monitor | Workflows | Execution list/detail | Workflow UI |
| 6 | Storage Manager | Storage | File list/upload | Storage |
| 7 | Knowledge Center | RAG/Knowledge | Ingest/search UI | Knowledge |
| 8 | Evaluation Dashboard | Quality | Scores | Evaluation |
| 9 | Job Monitor | Jobs | Job table/status | Async jobs |
| 10 | Organizations | Tenancy | Org list/create | Orgs |
| 11 | Roles/Permissions | RBAC | Role UI | RBAC |
| 12 | Settings | Branding/theme | Theme controls | Settings |
| 13 | System Health | Ops | Health status | Monitoring |
| 14 | Release Validation | Release | `/release/validation` via UI or API client | Release gates |
| 15 | API Docs | OpenAPI | FastAPI `/docs` | API evidence |

### Caption template

> **Figure X — {Title}.** Captured from Data Bot AI v1.0.0 Streamlit UI. Demonstrates {Purpose}.
