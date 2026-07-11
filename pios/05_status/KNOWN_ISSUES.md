# Known Issues — Data Bot AI v1.0.0 (canonical)

> Canonical copy. Root [`KNOWN_ISSUES.md`](../../KNOWN_ISSUES.md) mirrors this file.

Formally documented limitations and production-hardening status for v1.0.0.

| ID | Area | Issue | Severity | Status | Mitigation / Plan |
|----|------|-------|----------|--------|-------------------|
| KI-001 | Billing | Payment gateway available (Stripe) but requires ops keys; default remains internal | Medium | Mitigated | Set `BILLING_GATEWAY=stripe` + `STRIPE_*` secrets in production |
| KI-002 | Persistence | Commercial stores are SQL-capable; default local still memory unless DB backend enabled | Medium | Mitigated | Set `STORAGE_BACKEND=sqlite` or `postgres` (+ `DATABASE_URL`) for durable billing |
| KI-003 | Storage | S3 provider implemented via boto3; configure bucket/credentials for cloud | Low | Mitigated | Set `OBJECT_STORAGE_BACKEND=s3` + `S3_BUCKET` (+ AWS creds or IAM) |
| KI-004 | Deploy | No Kubernetes manifests | Low | Accepted | Docker Compose + process manager; K8s out of scope for 1.0 |
| KI-005 | Integrations | No enterprise SSO / IdP | Low | Accepted | Local JWT auth; SSO on roadmap |
| KI-006 | CORS | Production refuses wildcard/missing origins; ops must set explicit list | Medium | **Mitigated 2026-07-11** | Set `CORS_ALLOWED_ORIGINS` to comma-separated https origins before prod boot |
| KI-007 | Secrets | Production JWT fail-fast enforced; ops must still supply ≥32-char secret | High (ops) | **Mitigated 2026-07-11** | App refuses `APP_ENV=production` boot without strong `AUTH_JWT_SECRET`/`JWT_SECRET` |
| KI-008 | Pandas | `select_dtypes(include=["object"])` emits Pandas 4 deprecation warnings | Low | Accepted | Non-blocking; cleanup planned as a patch |
| KI-009 | Storage | Object storage metadata catalog is durable (file or SQLAlchemy) | High | **Mitigated 2026-07-11** | Default file index; SQL when DB enabled; auto file→SQL migration |

## Release Gate Decision

KI-006, KI-007, and KI-009 are mitigated in code. Remaining pre-beta hygiene: **TD-010**, Docker Compose verification, E2E smoke. Feature freeze recommended on `release/1.0`.
