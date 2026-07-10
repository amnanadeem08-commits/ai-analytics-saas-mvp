# Disaster Recovery Guide — v1.0 RC

## Backup Scope

| Asset | Location | Priority |
|-------|----------|----------|
| Database | `data/app.db` or PostgreSQL | Critical |
| Storage objects | `data/storage/` | Critical |
| Metadata JSON | `data/metadata/` | High |
| Configuration | Environment / secrets manager | Critical |

## RPO / RTO (MVP targets)

- **RPO**: 24 hours (daily backup)
- **RTO**: 4 hours (single-node restore)

## Recovery Steps

1. Stop API and worker processes
2. Restore database from latest backup
3. Restore `data/storage` and `data/metadata`
4. Verify `JWT_SECRET` and env match pre-incident or re-issue tokens
5. Run migrations: `alembic upgrade head`
6. Start services and validate `/api/v1/release/validation`

## Failure Modes

| Scenario | Mitigation |
|----------|------------|
| API crash | Process manager restart; liveness probe |
| DB corruption | Restore from backup |
| Storage loss | Restore object store snapshot |
| Secret leak | Rotate JWT_SECRET; invalidate sessions |

## Testing DR

Quarterly restore drill to staging environment recommended.
