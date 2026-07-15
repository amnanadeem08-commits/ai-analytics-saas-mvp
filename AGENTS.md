# AGENTS.md — Data Bot AI

**Start here:** [`pios/README.md`](pios/README.md)

This repository uses a **Project Intelligence Operating System (PIOS)**. Do not begin feature work from a large pasted prompt.

## Minimum protocol

```text
Read PIOS.
Read current project status.
Read current sprint.
Run impact_analyze.
Implement next task.
Run validation.
Update PIOS (complete_task).
Stop.
```

## Key paths

| Need | Path |
|------|------|
| Entrypoint | `pios/README.md` |
| Live status | `pios/05_status/PROJECT_STATUS.md` |
| Current sprint | `pios/04_sprints/CURRENT_SPRINT.md` |
| Architecture | `pios/02_architecture/` |
| Standards / gates | `pios/03_standards/` |
| Deep handbook | `documentation/README.md` |
| ADRs | `docs/architecture/` |

## Tools

```bash
python pios/tools/refresh_status.py
python pios/tools/impact_analyze.py --task "..."
python pios/tools/arch_check.py
python pios/tools/complete_task.py --summary "..."
python pios/tools/recommend_sprint.py
```

## Cursor Cloud specific instructions

Python deps live in a local virtualenv at `venv/` (gitignored). Activate it before running anything: `source venv/bin/activate`. The startup update script recreates/refreshes `venv/` and installs `khaldun-ai-website/` npm deps, so no manual install is normally needed.

Services (run each from repo root with the venv active; all bind to localhost):

| Service | Command | URL |
|---------|---------|-----|
| Backend API (FastAPI) | `uvicorn backend.main:app --reload` | http://127.0.0.1:8000 (`/docs`, `/health`, `/api/v1/ready`) |
| Frontend (Streamlit) | `streamlit run frontend/streamlit_app.py` | http://localhost:8501 |
| Marketing site (Next.js, separate/optional) | `npm --prefix khaldun-ai-website run dev` | http://localhost:3000 |

Checks / gates:
- Lint / architecture gate (Python): `python pios/tools/arch_check.py` (there is no ruff/flake8/black config).
- Tests: `pytest` (677 tests, ~80s, run offline). Quick E2E smoke: `python scripts/e2e_smoke.py`.
- Website lint: `npm --prefix khaldun-ai-website run lint`.

Non-obvious caveats:
- Runs fully offline/local-first by default: SQLite/in-memory storage, local object storage, in-memory queue. Postgres, Redis, worker, and S3 are all optional (see `docker/docker-compose.yml`) and not needed for dev or tests.
- The default LLM is a built-in deterministic `MockLLMProvider`. The AI Analyst / AI Chat therefore return canned "Mock structured response" text unless real provider keys are set (`OPENAI_API_KEY` / `ANTHROPIC_API_KEY`, etc.). This is expected, not a bug.
- The Streamlit frontend needs the backend running and reads `API_BASE_URL` (default `http://127.0.0.1:8000`). Some Streamlit pages transparently fall back to "local Streamlit analysis mode" if a backend request times out, so a page can still render KPIs even when it reports the backend as unavailable.
- Production mode (`APP_ENV=production`) refuses to boot without a strong `AUTH_JWT_SECRET` (≥32 chars) and explicit `CORS_ALLOWED_ORIGINS`; keep `APP_ENV=development` (the default) for local dev.
