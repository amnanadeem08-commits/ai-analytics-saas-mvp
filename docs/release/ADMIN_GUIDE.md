# Admin Guide — v1.0 RC

## Platform Admin

Users with `UserRole.admin` or `metadata.platform_admin=true` can access `/api/v1/admin/*`.

## Capabilities

- User directory and audit log review
- Organization oversight
- System metrics snapshot
- Usage and billing inspection (no live payment gateway in RC)

## API Keys

Organization API keys are managed at `/api/v1/api-keys`. Keys are shown once at creation; only hashes are stored.

## Quotas

Subscription plans (`free`, `pro`, `enterprise`) define usage quotas enforced by `usage_service`.

## Monitoring

Use `/api/v1/metrics` and `/api/v1/system/status` for operational dashboards.

## Security Operations

- Review `/api/v1/release/security/audit`
- Rotate `JWT_SECRET` on compromise
- Enable `SECURITY_HSTS_ENABLED` behind TLS
