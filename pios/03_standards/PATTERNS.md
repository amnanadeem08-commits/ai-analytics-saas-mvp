# Design Patterns

| Pattern | Where used |
|---------|------------|
| Registry / plugin | Domain, KPI, Visualization, Metric registries |
| Repository | `backend/repositories` (memory + SQLAlchemy) |
| Provider / adapter | Storage backends, LLM providers |
| Middleware pipeline | FastAPI middleware stack in `backend/main.py` |
| Session state facade | Streamlit `session_state` helpers |
| Workflow / planner | AI analyst planning + tool registry |

Prefer extending these patterns over introducing a parallel architecture.
