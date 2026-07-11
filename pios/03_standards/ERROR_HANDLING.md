# Error Handling

1. Raise typed/domain errors at service boundaries; map to HTTP status in routes
2. Never swallow exceptions silently — log with context
3. User-facing messages should be plain English; keep stack traces in logs
4. Validation errors (bad upload, schema) return actionable detail
5. Operational secrets must never appear in error payloads
