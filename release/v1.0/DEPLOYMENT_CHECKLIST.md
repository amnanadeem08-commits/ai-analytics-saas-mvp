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
- [x] Production Compose env template (`.env.production.example`) with JWT + CORS requirements
- [x] `docker/verify_prod_compose.py` static gate (live probes when Docker available)
- [x] Backend compose healthcheck on `/api/v1/live`; worker/frontend wait for healthy backend
