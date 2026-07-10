# v1.0.0 — Deployment Checklist

- [x] Configuration checklist complete
- [x] Dependencies pinned (`requirements*.txt`)
- [x] `python -m compileall backend frontend` verified
- [x] API start command documented (`uvicorn backend.main:app`)
- [x] Worker start command documented
- [x] Liveness `/api/v1/live` documented
- [x] Readiness `/api/v1/ready` documented
- [x] Release validation `/api/v1/release/validation` documented
- [x] Monitoring endpoints documented
- [x] Docker Compose path documented under `docker/`
