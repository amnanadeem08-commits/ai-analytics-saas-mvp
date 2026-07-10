# CONTRIBUTING

## Branches

- `main` — new features
- `release/v1.0` — bug fixes, security patches, docs only

## Rules for release/v1.0

No architectural changes, no breaking API changes, no new product features.

## Dev loop

```bash
pip install -r requirements-dev.txt
pytest -q
python -m compileall backend frontend
```

## Docs

Update `documentation/` when behavior changes. Do not invent features.
