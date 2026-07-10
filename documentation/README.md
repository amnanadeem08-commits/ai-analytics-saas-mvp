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
2. **Power BI / analytics readers:** [Data Bot AI Explained Like a Power BI Project](07_power_bi/DATA_BOT_AI_EXPLAINED_LIKE_POWER_BI.md)
3. Study [02 Architecture](02_architecture/README.md)
4. Drill into folders, workflows, API, frontend as needed
5. Use Learning / Interview / Portfolio sections for career prep

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
