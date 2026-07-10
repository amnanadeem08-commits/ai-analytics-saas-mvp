# v1.0.0 — Configuration Checklist

- [x] `JWT_SECRET` documented as required (≥32 chars) in production
- [x] `ENV_PROFILE` / `APP_ENV` documented
- [x] `CORS_ALLOWED_ORIGINS` documented (restrict in production)
- [x] `DATABASE_URL` documented
- [x] `STORAGE_BACKEND` / object storage documented
- [x] `QUEUE_BACKEND` documented
- [x] Rate limit and auth lockout env vars documented
- [x] HSTS / CSP flags documented
- [x] `MAX_UPLOAD_SIZE_MB` reviewed
- [x] `/api/v1/system/config` redacted exposure confirmed
- [x] `docker/.env.example` updated for v1.0.0
