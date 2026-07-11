# Rejected Approaches

| Approach | Why rejected | Prefer instead |
|----------|--------------|----------------|
| Pass domain metadata as loose dicts everywhere | Key drift, duplicated interpretation | Typed `DomainContext` (ADR-001) |
| Pydantic only at API edge, dicts internally | Still drifts inside services | Canonical DomainContext end-to-end |
| Put business logic in Streamlit pages | Hard to test, violates layering | `frontend/services` + backend services |
| Frontend imports backend services directly | Breaks process/deployment boundaries | HTTP API clients |
| Ship silent auto-clean of user data | Surprising mutations | Recommendations-first DQ UX |
| Treat in-memory commercial stores as durable | Restart data loss | Document as KI/TD; migrate to SQL |

Add new rejections when a design alternative is explicitly declined.
