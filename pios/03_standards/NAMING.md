# Naming Conventions

| Kind | Convention | Example |
|------|------------|---------|
| Services | `*_service.py` | `data_cleaning_service.py` |
| Routes | `*_routes.py` | `dataset_routes.py` |
| Models | `*_models.py` or domain name | `dataset_models.py` |
| Streamlit pages | `*_page.py` | `dataset_page.py` |
| API clients | `*_client.py` | under `frontend/api/` |
| Tests | `test_*.py` | `tests/test_*.py` |
| ADRs | `ADR-NNN-Title.md` | `ADR-001-DomainContext.md` |

Use snake_case for Python modules/functions; PascalCase for Pydantic models and classes.
