# v1.0.0 — Configuration Checklist

- [x] `JWT_SECRET` / `AUTH_JWT_SECRET` documented as required (≥32 chars) in production
- [x] Production refuses to boot with missing/weak/placeholder JWT secrets (KI-007 fail-fast)
- [x] `ENV_PROFILE` / `APP_ENV` documented
- [x] `CORS_ALLOWED_ORIGINS` documented (restrict in production)
- [x] Production refuses wildcard / missing CORS origins at startup (KI-006 fail-fast)
- [x] `DATABASE_URL` documented
- [x] `STORAGE_BACKEND` / object storage documented
- [x] `QUEUE_BACKEND` documented
- [x] Rate limit and auth lockout env vars documented
- [x] HSTS / CSP flags documented
- [x] `MAX_UPLOAD_SIZE_MB` reviewed
- [x] `/api/v1/system/config` redacted exposure confirmed
- [x] `docker/.env.example` updated for v1.0.0 / KI-007
