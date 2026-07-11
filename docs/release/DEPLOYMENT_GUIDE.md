# Deployment Guide — v1.0 RC

## Prerequisites

- Python 3.11+
- `pip install -r requirements.txt`
- Optional: PostgreSQL, Redis

## Environment

Copy `docker/.env.example` or set:

| Variable | Description |
|----------|-------------|
| `JWT_SECRET` / `AUTH_JWT_SECRET` | ≥32 char signing secret (**required** in production; app refuses to start otherwise) |
| `DATABASE_URL` | `sqlite:///./data/app.db` or PostgreSQL URL |
| `QUEUE_BACKEND` | `memory` or `redis` |
| `STORAGE_BACKEND` | DB store: `memory`, `sqlite`, or `postgres` |
| `OBJECT_STORAGE_BACKEND` | Files: `local` or `s3` (+ `S3_BUCKET` / AWS creds) |
| `STORAGE_METADATA_BACKEND` | Object catalog: `file` (default), `sqlalchemy` (when DB enabled), or `memory` (tests) |
| `CORS_ALLOWED_ORIGINS` | Comma-separated absolute origins. **Required in production** (wildcard `*` refused). Dev unset → localhost defaults; set `*` only for open local CORS. |
| `RATE_LIMIT_REQUESTS` | Requests per window (default 120) |
| `CSRF_ENABLED` | `true` for browser cookie flows |

## Run API

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

## Run Worker (optional)

```bash
python -m backend.workers.cli
```

## Docker

### Development

```bash
cd docker
docker compose --env-file .env.example --profile dev up --build
```

### Production profile

```bash
cd docker
copy .env.production.example .env.production
# Edit .env.production: set AUTH_JWT_SECRET / JWT_SECRET (≥32 chars) and CORS_ALLOWED_ORIGINS
docker compose --env-file .env.production --profile prod up --build -d
python verify_prod_compose.py --live
```

Static verification (no Docker daemon required):

```bash
python docker/verify_prod_compose.py
```

Production refuse-to-boot rules still apply inside containers (KI-006 CORS, KI-007 JWT).

## Health Checks

- Liveness: `GET /api/v1/live`
- Readiness: `GET /api/v1/ready`
- Full health: `GET /api/v1/monitoring/health`

## Post-deploy Validation

```bash
curl http://localhost:8000/api/v1/release/validation
python scripts/e2e_smoke.py
```
