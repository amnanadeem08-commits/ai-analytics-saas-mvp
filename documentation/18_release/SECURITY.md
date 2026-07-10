# Security Guide — v1.0 RC

## Controls Implemented (Sprint 8.7)

- Security headers (CSP, X-Frame-Options, nosniff)
- Configurable CORS policy
- Optional CSRF middleware
- Per-IP rate limiting
- Login brute-force lockout
- Input sanitization utilities
- Secrets validation on release checks
- Dependency audit helper

## Authentication

- JWT access + refresh tokens
- Password policy validation
- Audit events for auth actions

## RBAC

Layered permission evaluation with explicit deny support.

## Recommendations for Production

1. Set strong `JWT_SECRET` (≥32 characters)
2. Restrict `CORS_ALLOWED_ORIGINS` to known frontends
3. Enable TLS termination at reverse proxy
4. Enable `SECURITY_HSTS_ENABLED` when using HTTPS
5. Run `GET /api/v1/release/security/audit` after deploy
6. Pin dependencies and scan regularly

## Incident Response

See `DISASTER_RECOVERY_GUIDE.md` and runbooks in `docs/release/runbooks/`.
