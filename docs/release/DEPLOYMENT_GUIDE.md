# Deployment Guide — v1.0 RC

## Prerequisites

- Python 3.11+
- `pip install -r requirements.txt`
- Optional: PostgreSQL, Redis

## Environment

Copy `docker/.env.example` or set:

| Variable | Description |
|----------|-------------|
| `JWT_SECRET` | ≥32 char signing secret (required in production) |
| `DATABASE_URL` | `sqlite:///./data/app.db` or PostgreSQL URL |
| `QUEUE_BACKEND` | `memory` or `redis` |
| `STORAGE_BACKEND` | DB store: `memory`, `sqlite`, or `postgres` |
| `OBJECT_STORAGE_BACKEND` | Files: `local` or `s3` (+ `S3_BUCKET` / AWS creds) |
| `CORS_ALLOWED_ORIGINS` | Comma-separated origins |
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

```bash
cd docker && docker compose up --build
```

## Health Checks

- Liveness: `GET /api/v1/live`
- Readiness: `GET /api/v1/ready`
- Full health: `GET /api/v1/monitoring/health`

## Post-deploy Validation

```bash
curl http://localhost:8000/api/v1/release/validation
```
