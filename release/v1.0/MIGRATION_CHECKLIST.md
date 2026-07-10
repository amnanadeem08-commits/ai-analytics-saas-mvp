# v1.0.0 — Migration Checklist

- [x] Backup existing `data/` directory before upgrade
- [x] Run `alembic upgrade head` when using SQL persistence
- [x] Verify `datasets.json` and metadata files intact
- [x] Confirm storage objects under `data/storage/`
- [x] Smoke test auth login after migration
- [x] Run `pytest -q`
- [x] Hit `/api/v1/release/validation`
