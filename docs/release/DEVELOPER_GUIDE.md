# Developer Guide — v1.0 RC

## Repository Layout

- `backend/` — FastAPI application
- `frontend/` — Streamlit UI
- `tests/` — pytest suite including `load/`, `security/`, `release/`
- `docs/release/` — production documentation

## Local Development

```bash
pip install -r requirements-dev.txt
pytest -q
python -m compileall backend frontend
```

## Adding Endpoints

1. Define Pydantic models in `backend/models/` or `backend/api/models/`
2. Implement service in `backend/services/`
3. Add route in `backend/api/routes/`
4. Register router in `backend/main.py`
5. Add tests under `tests/`

## Conventions

- API prefix: `/api/v1`
- Use `raise_api_error` / `map_service_exception` for HTTP errors
- Paginate list endpoints with `backend.performance.pagination.paginate`
- Instrument long operations with `backend.performance.query.timed_query`

## Test Helpers

Many in-memory services expose `reset_*()` functions for test isolation.
