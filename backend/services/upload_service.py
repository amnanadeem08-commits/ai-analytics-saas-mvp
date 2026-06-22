from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from fastapi import UploadFile

from backend.core.config import settings
from backend.core.dataset_record import DatasetRecord, DATASET_STATUS_READY
from backend.processing.data_cleaner import clean_dataframe
from backend.processing.overview_service import build_dataset_overview
from backend.processing.table_loader import load_table
from backend.storage.dataset_registry import save_dataset_record
from backend.storage.local_storage import save_processed_dataframe
from backend.storage.metadata_store import add_dataset
from backend.utils.file_utils import safe_filename
from backend.utils.validation_utils import validate_tabular_upload_size


logger = logging.getLogger(__name__)
UPLOAD_CHUNK_SIZE = 4 * 1024 * 1024


def _prewarm_dataset_cache(dataset_id: str) -> None:
    """Prime expensive first-hit analytics so first page navigation is responsive."""
    from backend.services.dashboard_service import build_dashboard_view
    from backend.services.insight_service import get_insights
    from backend.services.visual_builder_service import discover_visual_builder_schema

    started = perf_counter()
    build_dashboard_view(dataset_id)
    get_insights(dataset_id)
    discover_visual_builder_schema(dataset_id)
    logger.info("upload_prewarm dataset=%s seconds=%.3f", dataset_id, perf_counter() - started)


async def _stream_upload(file: UploadFile, destination: Path) -> tuple[int, str]:
    size = 0
    digest = hashlib.sha256()
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with destination.open("wb") as target:
            while chunk := await file.read(UPLOAD_CHUNK_SIZE):
                size += len(chunk)
                if size > settings.max_upload_size_bytes:
                    raise ValueError(
                        f"File is too large ({size / 1024 / 1024:.1f} MB read). "
                        f"Maximum size is {settings.MAX_UPLOAD_SIZE_MB} MB."
                    )
                digest.update(chunk)
                target.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return size, digest.hexdigest()


async def upload_dataset(file: UploadFile) -> dict:
    """Stream, validate, clean, profile, and register a tabular dataset."""
    started = perf_counter()
    original_filename = safe_filename(file.filename or "dataset.csv")
    dataset_id = f"ds_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}"
    stored_filename = f"{dataset_id}_{original_filename}"
    processed_filename = f"{dataset_id}_processed.csv"
    original_path = settings.UPLOADS_DIR / stored_filename

    stream_started = perf_counter()
    size_bytes, file_hash = await _stream_upload(file, original_path)
    try:
        validate_tabular_upload_size(original_filename, size_bytes)
    except Exception:
        original_path.unlink(missing_ok=True)
        raise
    logger.info(
        "upload_stream dataset=%s size_mb=%.2f seconds=%.3f",
        dataset_id,
        size_bytes / 1024 / 1024,
        perf_counter() - stream_started,
    )

    parse_started = perf_counter()
    raw_df = load_table(original_path)
    processed_df = clean_dataframe(raw_df)
    logger.info(
        "upload_parse dataset=%s rows=%s columns=%s seconds=%.3f",
        dataset_id,
        len(processed_df),
        len(processed_df.columns),
        perf_counter() - parse_started,
    )
    processed_df.attrs["_dataset_cache_key"] = f"{dataset_id}:{file_hash}"
    if processed_df.empty:
        raise ValueError("Dataset has no usable rows after cleaning.")

    profile_started = perf_counter()
    overview = build_dataset_overview(processed_df)
    logger.info("upload_profile dataset=%s seconds=%.3f", dataset_id, perf_counter() - profile_started)

    processed_path = save_processed_dataframe(processed_df, processed_filename)
    record = DatasetRecord(
        dataset_id=dataset_id,
        original_filename=original_filename,
        stored_filename=stored_filename,
        processed_filename=processed_filename,
        dataframe=processed_df,
        original_path=str(original_path.as_posix()),
        processed_path=str(Path(processed_path).as_posix()),
        overview=overview,
        column_schema=overview["column_schema"],
        column_groups=overview["column_groups"],
        status=DATASET_STATUS_READY,
        upload_time=datetime.now(timezone.utc).isoformat(),
        file_hash=file_hash,
    )
    metadata = save_dataset_record(record)
    add_dataset(metadata)
    try:
        _prewarm_dataset_cache(dataset_id)
    except Exception:
        logger.exception("upload_prewarm_failed dataset=%s", dataset_id)
    logger.info("upload_complete dataset=%s seconds=%.3f", dataset_id, perf_counter() - started)
    return metadata