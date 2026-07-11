from __future__ import annotations

"""Helpers to migrate StorageObject catalogs between metadata stores (KI-009)."""

import logging

from backend.storage.interfaces import StorageMetadataStore

_log = logging.getLogger("ai_analytics.storage.migrate")


def migrate_metadata_store(
    source: StorageMetadataStore,
    target: StorageMetadataStore,
    *,
    skip_existing: bool = True,
) -> dict[str, int]:
    """Copy all objects from ``source`` into ``target``.

    Returns counts: ``copied``, ``skipped``, ``total``.
    """
    copied = 0
    skipped = 0
    objects = source.list()
    for obj in objects:
        if skip_existing and target.get(obj.object_id) is not None:
            skipped += 1
            continue
        target.save(obj)
        copied += 1
    _log.info(
        "Storage metadata migration complete: copied=%s skipped=%s total=%s",
        copied,
        skipped,
        len(objects),
    )
    return {"copied": copied, "skipped": skipped, "total": len(objects)}
