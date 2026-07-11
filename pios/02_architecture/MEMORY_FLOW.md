# Memory Flow

AI Analyst memory is handled by `memory_service` within the analyst runtime.

## Expected behavior (verified modules exist)

1. Conversation / session context captured for multi-turn analysis
2. Memory consulted during planning and tool selection
3. Memory updates after successful analyst steps

## Constraints

- Do not treat memory as durable enterprise knowledge — RAG/knowledge ingestion is the durable path
- Clear/isolation expectations for multi-tenant contexts must respect auth/RBAC boundaries

Deep reference: [`documentation/08_ai/README.md`](../../documentation/08_ai/README.md)
