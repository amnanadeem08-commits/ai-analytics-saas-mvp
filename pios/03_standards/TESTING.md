# Testing Standards

1. Add/adjust unit tests next to the behavior changed
2. Prefer pure helper tests for frontend logic extracted from pages
3. API/service changes need route or service tests under `tests/`
4. Release-affecting work must pass the full suite and E2E release tests
5. Do not delete failing tests to “green” CI — fix the product or update assertions intentionally

## Commands

```bash
pytest
pytest tests/release/test_e2e_production.py
python pios/tools/arch_check.py
```

Evidence at v1.0.0 release: **634 passed**, **125** `test_*.py` files.
