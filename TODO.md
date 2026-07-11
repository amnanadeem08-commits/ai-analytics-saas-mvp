# TODO

## Complete

- [x] Phase 0.3 AI Business Column Suggestions
- [x] Billing gateway (internal + Stripe)
- [x] Persistent commercial stores (memory + SQLAlchemy)
- [x] S3 object storage provider (boto3 + moto tests)
- [x] Production JWT fail-fast (KI-007 / TD-007)
- [x] Durable storage metadata (KI-009 / TD-011)
- [x] Production CORS hardening (KI-006 / TD-006)
- [x] TD-010 FE layer boundary (`ai_insights_page`)
- [x] Production Docker Compose verification (static gate; live requires Docker Desktop)
- [x] End-to-end smoke test with real datasets (`scripts/e2e_smoke.py`)
- [x] Cut `release/1.0` + `develop`; confirm `v1.0.0` tag (GA); hardening on `main` as `232574f`

## Next (beta launch ops)

- [ ] Push `main`, `release/1.0`, `develop` to origin
- [ ] Tag `v1.0.1` on hardening tip (recommended patch) or publish beta notes from `release/1.0`
- [ ] Live Docker Compose `--profile prod` on a Docker host
- [ ] Beta user invite / go-live checklist
