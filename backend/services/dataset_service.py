from __future__ import annotations

"""Dataset service — tabular access + storage-backed lifecycle (Sprint 8.4)."""

import hashlib
import logging
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

import pandas as pd
from fastapi import UploadFile

from backend.core.config import settings
from backend.core.constants import DEFAULT_PREVIEW_ROWS, MAX_PREVIEW_ROWS
from backend.core.dataset_record import DATASET_STATUS_READY, DatasetRecord
from backend.core.exceptions import DatasetNotFoundError
from backend.models.storage_models import ArtifactType, DatasetStatus, StorageObject
from backend.processing.data_cleaner import clean_dataframe
from backend.processing.overview_service import build_dataset_overview
from backend.processing.table_loader import load_table
from backend.services import storage_service
from backend.services.storage_service import StorageError
from backend.storage.dataset_registry import load_dataset_record, save_dataset_record
from backend.storage.local_storage import save_processed_dataframe
from backend.storage.metadata_store import add_dataset, get_dataset, list_datasets, save_datasets
from backend.utils.file_utils import safe_filename
from backend.utils.response_utils import dataframe_preview
from backend.utils.validation_utils import validate_tabular_upload_size

logger = logging.getLogger(__name__)
UPLOAD_CHUNK_SIZE = 4 * 1024 * 1024

_DATASET_STORAGE_INDEX: dict[str, str] = {}


class DatasetError(Exception):
    def __init__(self, message: str, *, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def reset_datasets() -> None:
    """Test helper."""
    _DATASET_STORAGE_INDEX.clear()
    clear_dataset_cache()


# ── Existing dataset read API (unchanged) ───────────────────────────────────


def get_all_datasets() -> list[dict]:
    return sorted(list_datasets(), key=lambda item: item.get("upload_time", ""), reverse=True)


def get_dataset_metadata(dataset_id: str) -> dict:
    return get_dataset(dataset_id)


@lru_cache(maxsize=8)
def _load_dataset_dataframe_cached(
    dataset_id: str,
    file_hash: str,
    parquet_path: str,
    processed_path: str,
) -> pd.DataFrame:
    if parquet_path and Path(parquet_path).exists():
        dataframe = pd.read_parquet(parquet_path)
    else:
        dataframe = pd.read_csv(processed_path)
    dataframe.attrs["_dataset_cache_key"] = f"{dataset_id}:{file_hash}"
    return dataframe


def load_dataset_dataframe(dataset_id: str) -> pd.DataFrame:
    metadata = get_dataset(dataset_id)
    return _load_dataset_dataframe_cached(
        dataset_id,
        metadata.get("file_hash", ""),
        metadata.get("parquet_path") or "",
        metadata.get("processed_path") or "",
    )


def clear_dataset_cache() -> None:
    _load_dataset_dataframe_cached.cache_clear()


def get_dataset_status(dataset_id: str) -> dict:
    metadata = get_dataset(dataset_id)
    return {
        "dataset_id": dataset_id,
        "status": metadata.get("status", "ready"),
        "row_count": int(metadata.get("row_count", 0)),
        "column_count": int(metadata.get("column_count", 0)),
        "error_message": metadata.get("error_message"),
    }


def get_dataset_overview(dataset_id: str) -> dict:
    metadata = get_dataset(dataset_id)
    overview = metadata.get("overview") or {}
    return {
        "dataset_id": dataset_id,
        "original_filename": metadata["original_filename"],
        "status": metadata.get("status", "ready"),
        **overview,
    }


def get_dataset_preview(dataset_id: str, rows: int = DEFAULT_PREVIEW_ROWS) -> dict:
    rows = max(1, min(rows, MAX_PREVIEW_ROWS))
    df = load_dataset_dataframe(dataset_id)
    return {
        "dataset_id": dataset_id,
        "columns": df.columns.tolist(),
        "rows": dataframe_preview(df, rows=rows),
        "preview_row_count": min(rows, len(df)),
    }


# ── Storage-backed lifecycle (Sprint 8.4) ─────────────────────────────────────


def _prewarm_dataset_cache(dataset_id: str) -> None:
    from backend.services.dashboard_service import build_dashboard_view
    from backend.services.insight_service import get_insights
    from backend.services.visual_builder_service import discover_visual_builder_schema

    started = perf_counter()
    build_dashboard_view(dataset_id)
    get_insights(dataset_id)
    discover_visual_builder_schema(dataset_id)
    logger.info("dataset_prewarm dataset=%s seconds=%.3f", dataset_id, perf_counter() - started)


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


def _process_dataframe(
    *,
    dataset_id: str,
    original_filename: str,
    stored_filename: str,
    original_path: Path,
    file_hash: str,
    storage_object_id: str | None = None,
    owner_id: str = "",
    organization_id: str = "",
    workspace_id: str = "",
) -> dict[str, Any]:
    processed_filename = f"{dataset_id}_processed.csv"
    raw_df = load_table(original_path)
    processed_df = clean_dataframe(raw_df)
    processed_df.attrs["_dataset_cache_key"] = f"{dataset_id}:{file_hash}"
    if processed_df.empty:
        raise ValueError("Dataset has no usable rows after cleaning.")

    overview = build_dataset_overview(processed_df)
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
    if storage_object_id:
        metadata["storage_object_id"] = storage_object_id
    metadata["owner_id"] = owner_id
    metadata["organization_id"] = organization_id
    metadata["workspace_id"] = workspace_id
    metadata["dataset_status"] = DatasetStatus.active.value
    _upsert_dataset_metadata(metadata)
    if storage_object_id:
        _DATASET_STORAGE_INDEX[dataset_id] = storage_object_id
    clear_dataset_cache()
    return metadata


async def create_dataset(
    file: UploadFile,
    *,
    owner_id: str = "",
    organization_id: str = "",
    workspace_id: str = "",
) -> dict[str, Any]:
    """Upload via storage service, then run existing tabular pipeline."""
    started = perf_counter()
    original_filename = safe_filename(file.filename or "dataset.csv")
    dataset_id = f"ds_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}"
    stored_filename = f"{dataset_id}_{original_filename}"
    original_path = settings.UPLOADS_DIR / stored_filename

    size_bytes, file_hash = await _stream_upload(file, original_path)
    try:
        validate_tabular_upload_size(original_filename, size_bytes)
    except Exception:
        original_path.unlink(missing_ok=True)
        raise

    content = original_path.read_bytes()
    storage_obj = storage_service.upload(
        content,
        original_filename,
        artifact_type=ArtifactType.dataset,
        owner_id=owner_id,
        organization_id=organization_id,
        workspace_id=workspace_id,
        content_type=file.content_type or "application/octet-stream",
        metadata={"dataset_id": dataset_id, "file_hash": file_hash},
        allow_duplicate=True,
    )

    metadata = _process_dataframe(
        dataset_id=dataset_id,
        original_filename=original_filename,
        stored_filename=stored_filename,
        original_path=original_path,
        file_hash=file_hash,
        storage_object_id=storage_obj.object_id,
        owner_id=owner_id,
        organization_id=organization_id,
        workspace_id=workspace_id,
    )
    try:
        _prewarm_dataset_cache(dataset_id)
    except Exception:
        logger.exception("dataset_prewarm_failed dataset=%s", dataset_id)
    logger.info(
        "create_dataset dataset=%s storage=%s seconds=%.3f",
        dataset_id,
        storage_obj.object_id,
        perf_counter() - started,
    )
    return metadata


def new_version(
    dataset_id: str,
    content: bytes,
    filename: str,
    *,
    owner_id: str = "",
    content_type: str = "application/octet-stream",
) -> dict[str, Any]:
    """Upload a new version for an existing dataset."""
    try:
        existing = get_dataset(dataset_id)
    except DatasetNotFoundError as exc:
        raise DatasetError(str(exc), status_code=404) from exc

    storage_object_id = existing.get("storage_object_id") or _DATASET_STORAGE_INDEX.get(dataset_id)
    if not storage_object_id:
        raise DatasetError(f"No storage object linked to dataset {dataset_id}", status_code=409)

    safe_name = safe_filename(filename)
    validate_tabular_upload_size(safe_name, len(content))
    storage_obj = storage_service.upload(
        content,
        safe_name,
        artifact_type=ArtifactType.dataset,
        object_id=storage_object_id,
        owner_id=owner_id or existing.get("owner_id", ""),
        organization_id=existing.get("organization_id", ""),
        workspace_id=existing.get("workspace_id", ""),
        content_type=content_type,
        metadata={"dataset_id": dataset_id},
        allow_duplicate=True,
    )

    stored_filename = f"{dataset_id}_{safe_name}"
    original_path = settings.UPLOADS_DIR / stored_filename
    original_path.write_bytes(content)
    file_hash = hashlib.sha256(content).hexdigest()
    metadata = _process_dataframe(
        dataset_id=dataset_id,
        original_filename=safe_name,
        stored_filename=stored_filename,
        original_path=original_path,
        file_hash=file_hash,
        storage_object_id=storage_object_id,
        owner_id=existing.get("owner_id", ""),
        organization_id=existing.get("organization_id", ""),
        workspace_id=existing.get("workspace_id", ""),
    )
    metadata["storage_version"] = storage_obj.current_version
    return metadata


def archive_dataset(dataset_id: str) -> dict[str, Any]:
    meta = _get_dataset_meta(dataset_id)
    storage_object_id = meta.get("storage_object_id") or _DATASET_STORAGE_INDEX.get(dataset_id)
    if storage_object_id:
        storage_service.archive(storage_object_id)
    meta["dataset_status"] = DatasetStatus.archived.value
    _update_dataset_meta(dataset_id, meta)
    return meta


def restore_dataset(dataset_id: str) -> dict[str, Any]:
    meta = _get_dataset_meta(dataset_id)
    storage_object_id = meta.get("storage_object_id") or _DATASET_STORAGE_INDEX.get(dataset_id)
    if storage_object_id:
        storage_service.restore(storage_object_id)
    meta["dataset_status"] = DatasetStatus.active.value
    _update_dataset_meta(dataset_id, meta)
    return meta


def delete_dataset(dataset_id: str) -> dict[str, Any]:
    meta = _get_dataset_meta(dataset_id)
    storage_object_id = meta.get("storage_object_id") or _DATASET_STORAGE_INDEX.get(dataset_id)
    if storage_object_id:
        storage_service.delete(storage_object_id)
    meta["dataset_status"] = DatasetStatus.deleted.value
    _update_dataset_meta(dataset_id, meta)
    _DATASET_STORAGE_INDEX.pop(dataset_id, None)
    return meta


def preview_dataset(dataset_id: str, *, limit: int = 25) -> dict[str, Any]:
    return get_dataset_preview(dataset_id, rows=limit)


def dataset_summary(dataset_id: str) -> dict[str, Any]:
    meta = _get_dataset_meta(dataset_id)
    storage_object_id = meta.get("storage_object_id") or _DATASET_STORAGE_INDEX.get(dataset_id)
    storage_obj: StorageObject | None = None
    if storage_object_id:
        storage_obj = storage_service.get_metadata(storage_object_id)
    return {
        "dataset_id": dataset_id,
        "filename": meta.get("original_filename"),
        "status": meta.get("dataset_status", DatasetStatus.active.value),
        "upload_time": meta.get("upload_time"),
        "storage_object_id": storage_object_id,
        "storage_version": meta.get("storage_version") or (storage_obj.current_version if storage_obj else None),
        "version_count": len(storage_obj.versions) if storage_obj else 0,
        "file_hash": meta.get("file_hash"),
        "row_count": meta.get("overview", {}).get("row_count"),
        "column_count": meta.get("overview", {}).get("column_count"),
    }


def list_dataset_summaries() -> list[dict[str, Any]]:
    return [dataset_summary(d["dataset_id"]) for d in list_datasets()]


def _get_dataset_meta(dataset_id: str) -> dict[str, Any]:
    try:
        return get_dataset(dataset_id)
    except DatasetNotFoundError as exc:
        raise DatasetError(str(exc), status_code=404) from exc


def _update_dataset_meta(dataset_id: str, meta: dict[str, Any]) -> None:
    datasets = list_datasets()
    for idx, item in enumerate(datasets):
        if item.get("dataset_id") == dataset_id:
            datasets[idx] = meta
            save_datasets(datasets)
            return
    raise DatasetError(f"Dataset '{dataset_id}' was not found.", status_code=404)


def _upsert_dataset_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    datasets = list_datasets()
    dataset_id = metadata.get("dataset_id")
    for idx, item in enumerate(datasets):
        if item.get("dataset_id") == dataset_id:
            datasets[idx] = metadata
            save_datasets(datasets)
            return metadata
    add_dataset(metadata)
    return metadata
