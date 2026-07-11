# Storage Flow

## Object storage

- Abstraction under `backend/storage/`
- MVP production path: **local filesystem** (`STORAGE_BACKEND=local`)
- S3 provider is a **stub** (KI-003) — completion planned post-1.0

## Dataset / artifact lifecycle

1. Upload lands in `data/uploads`
2. Processed artifacts in `data/processed`
3. Metadata JSON under `data/metadata`
4. Optional SQL persistence via repositories + Alembic for platform entities

## Commercial stores (known limitation)

Billing, usage, API keys, and some auth stores remain **in-memory** in v1.0 (KI-002) — restart clears commercial state.

Deep reference: [`documentation/10_database/README.md`](../../documentation/10_database/README.md), [`KNOWN_ISSUES`](../05_status/KNOWN_ISSUES.md)
