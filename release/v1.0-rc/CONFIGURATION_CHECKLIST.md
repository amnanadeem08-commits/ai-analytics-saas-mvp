# v1.0 RC — Configuration Checklist

- [ ] `JWT_SECRET` set (≥32 chars)
- [ ] `ENV_PROFILE=production`
- [ ] `CORS_ALLOWED_ORIGINS` restricted
- [ ] `DATABASE_URL` points to production DB
- [ ] `STORAGE_BACKEND` configured
- [ ] `QUEUE_BACKEND` configured (redis if multi-worker)
- [ ] `RATE_LIMIT_REQUESTS` tuned
- [ ] `SECURITY_HSTS_ENABLED=true` (if TLS)
- [ ] `MAX_UPLOAD_SIZE_MB` reviewed
- [ ] `/api/v1/system/config` reviewed (redacted)
