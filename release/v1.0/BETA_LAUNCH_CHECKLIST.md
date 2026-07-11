# v1.0.1 — Beta Launch Checklist

> Branch: `release/1.0` · Tag: `v1.0.1` · Feature freeze active

## Already complete (engineering)

- [x] Production JWT fail-fast (KI-007)
- [x] Production CORS fail-fast (KI-006)
- [x] Durable storage metadata (KI-009)
- [x] FE architecture gate TD-010 (`arch_check` green)
- [x] Compose static verification (`python docker/verify_prod_compose.py`)
- [x] E2E smoke with real sample (`python scripts/e2e_smoke.py`)
- [x] Branches pushed: `main`, `release/1.0`, `develop`
- [x] Annotated tag `v1.0.1` pushed to origin

## Operator actions (required before public beta)

### 1. GitHub Release notes

`gh` must be authenticated on the operator machine:

```bash
gh auth login
gh release create v1.0.1 --title "Data Bot AI v1.0.1 — production hardening beta" --generate-notes
```

Or open: https://github.com/amnanadeem08-commits/ai-analytics-saas-mvp/releases/new?tag=v1.0.1

- [ ] GitHub Release published for `v1.0.1`

### 2. Live Docker Compose (prod profile)

Requires Docker Desktop installed and running:

```bash
cd docker
copy .env.production.example .env.production
# Set AUTH_JWT_SECRET / JWT_SECRET (≥32 chars) and CORS_ALLOWED_ORIGINS (no *)
docker compose --env-file .env.production --profile prod up --build -d
python verify_prod_compose.py --live
python ../scripts/e2e_smoke.py
```

- [ ] Docker Desktop installed
- [ ] `.env.production` secrets set (never commit)
- [ ] `compose --profile prod` healthy (`/api/v1/live`, `/api/v1/ready`)
- [ ] Live verify script PASS
- [ ] E2E smoke PASS against running API (optional re-run)

### 3. Production config (minimum)

| Variable | Required value |
|----------|----------------|
| `APP_ENV` | `production` |
| `AUTH_JWT_SECRET` / `JWT_SECRET` | unique ≥32 chars |
| `CORS_ALLOWED_ORIGINS` | explicit https origins (no `*`) |
| `STORAGE_BACKEND` | `postgres` |
| `DATABASE_URL` | production Postgres URL |
| `QUEUE_BACKEND` | `redis` |
| `OBJECT_STORAGE_BACKEND` | `s3` (recommended) or durable volume |
| `BILLING_GATEWAY` | `stripe` + keys **if** taking payment |

- [ ] Secrets + CORS set in target environment
- [ ] DB migrated (`alembic upgrade head`)
- [ ] Backups scheduled (see `BACKUP_CHECKLIST.md`)

### 4. Beta cohort

- [ ] Invite list approved (email / org accounts)
- [ ] Support channel defined (email / chat)
- [ ] Known limitations shared (KI-001 Stripe keys, KI-004 no K8s, KI-005 no SSO)
- [ ] Feedback intake process ready

### 5. Go / No-go

- [ ] All engineering boxes above remain green
- [ ] Operator boxes 1–4 complete
- [ ] **GO** recorded with date + owner

## Freeze policy

```text
release/1.0  → bug fixes + security only
develop      → v1.1 features
```
