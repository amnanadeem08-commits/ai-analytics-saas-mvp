# Runbook: API Unhealthy

## Symptoms

- `/api/v1/ready` returns `not_ready`
- Elevated 5xx rate

## Steps

1. Check `/api/v1/monitoring/health` dependency section
2. Verify database connectivity (`DATABASE_URL`)
3. Verify storage path permissions (`data/storage`)
4. Check queue backend if `QUEUE_BACKEND=redis`
5. Review logs (JSON structured, Sprint 8.5)
6. Restart API: `uvicorn backend.main:app`

## Escalation

If degraded > 15 minutes, initiate disaster recovery restore procedure.
