# Configuration Guide — v1.0 RC

Configuration is loaded from environment variables and `backend/config/` (Sprint 8.5).

## Profiles

`ENV_PROFILE`: `development` | `staging` | `production`

## Security

| Variable | Default | Notes |
|----------|---------|-------|
| `JWT_SECRET` | — | Required in production |
| `CSRF_ENABLED` | false | Enable for cookie-based UI |
| `RATE_LIMIT_REQUESTS` | 120 | Per IP+path window |
| `AUTH_MAX_FAILED_ATTEMPTS` | 5 | Brute-force threshold |
| `SECURITY_HSTS_ENABLED` | false | Enable behind HTTPS |

## Performance

| Variable | Default |
|----------|---------|
| `MAX_UPLOAD_SIZE_MB` | 200 |

## Data

| Variable | Default |
|----------|---------|
| `DATABASE_URL` | sqlite local |
| `STORAGE_BACKEND` | local |
| `QUEUE_BACKEND` | memory |

## CORS

| Variable | Default |
|----------|---------|
| `CORS_ALLOWED_ORIGINS` | `*` |
| `CORS_ALLOW_CREDENTIALS` | false when origins is `*` |

Read-only config exposure: `GET /api/v1/system/config`
