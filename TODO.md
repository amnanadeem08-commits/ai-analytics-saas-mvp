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
- [x] Cut `release/1.0` + `develop`; confirm `v1.0.0` tag (GA)
- [x] Push `main`, `release/1.0`, `develop` to origin
- [x] Tag `v1.0.1` pushed to origin
- [x] Beta launch checklist written (`release/v1.0/BETA_LAUNCH_CHECKLIST.md`)

## Next (operator / host with Docker + gh auth)

- [ ] Publish GitHub Release UI for `v1.0.1` (`gh auth login` required)
- [ ] Live Docker Compose `--profile prod` + `--live` verify
- [ ] Beta user invite / go-live sign-off
