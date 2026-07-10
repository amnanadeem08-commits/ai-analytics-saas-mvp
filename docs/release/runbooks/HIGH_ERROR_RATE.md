# Runbook: High Error Rate

## Symptoms

- Spike in `/api/v1/metrics` error counters
- Rate limit 429 responses

## Steps

1. Identify failing route from monitoring middleware logs
2. Check `/api/v1/release/performance` for slow queries
3. Review circuit breaker status in performance snapshot
4. Temporarily increase `RATE_LIMIT_REQUESTS` if legitimate traffic spike
5. Scale worker process if job backlog growing
