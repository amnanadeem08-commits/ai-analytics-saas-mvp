# v1.0 RC — Migration Checklist

- [ ] Backup existing `data/` directory
- [ ] Run `alembic upgrade head`
- [ ] Verify `datasets.json` and metadata files intact
- [ ] Confirm storage objects migrated under `data/storage/`
- [ ] Smoke test auth login
- [ ] Run `pytest -q`
- [ ] Hit `/api/v1/release/validation`
