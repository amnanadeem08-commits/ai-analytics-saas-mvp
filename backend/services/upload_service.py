from __future__ import annotations

"""Upload service — delegates to dataset_service + storage layer (Sprint 8.4)."""

import logging

from fastapi import UploadFile

logger = logging.getLogger(__name__)


async def upload_dataset(file: UploadFile) -> dict:
    """Stream, validate, clean, profile, and register a tabular dataset via storage layer."""
    from backend.services import dataset_service

    metadata = await dataset_service.create_dataset(file)
    logger.info(
        "upload_complete dataset=%s storage_object=%s",
        metadata.get("dataset_id"),
        metadata.get("storage_object_id"),
    )
    return metadata
