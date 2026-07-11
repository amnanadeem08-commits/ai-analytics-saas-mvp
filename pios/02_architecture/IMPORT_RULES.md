# Import Rules

## Python package conventions

- Prefer absolute imports from package roots: `from backend.services.x import ...`
- Frontend local helpers stay under `frontend.utils` / `frontend.services`
- Tests may import backend/frontend packages; production code must not import `tests`

## Cross-boundary

| From | May import | Must not import |
|------|------------|-----------------|
| `frontend.*` | `frontend.*`, stdlib, third-party UI/data libs | `backend.services`, `backend.repositories`, `backend.database` |
| `backend.api.routes` | services, models, core/config | streamlit, frontend |
| `backend.services` | models, repos, storage, rag, registry, utils | streamlit, frontend |
| `backend.repositories` | database models, sqlalchemy | streamlit, frontend, api routes |

## Enforcement

```bash
python pios/tools/arch_check.py
```
