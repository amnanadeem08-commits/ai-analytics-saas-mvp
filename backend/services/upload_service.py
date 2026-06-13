from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from backend.core.dataset_record import DatasetRecord, DATASET_STATUS_READY
from backend.processing.data_cleaner import clean_dataframe
from backend.processing.overview_service import build_dataset_overview
from backend.processing.table_loader import load_table
from backend.storage.dataset_registry import save_dataset_record
from backend.storage.local_storage import save_processed_dataframe, save_uploaded_file
from backend.storage.metadata_store import add_dataset
from backend.utils.file_utils import safe_filename
from backend.utils.validation_utils import validate_tabular_upload


async def upload_dataset(file: UploadFile) -> dict:
    """Validate, save, clean, and register a tabular dataset."""
    content = await file.read()
    validate_tabular_upload(file.filename or "", content)

    original_filename = safe_filename(file.filename or "dataset.csv")
    dataset_id = f"ds_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}"

    stored_filename = f"{dataset_id}_{original_filename}"
    processed_filename = f"{dataset_id}_processed.csv"

    original_path = save_uploaded_file(content, stored_filename)
    raw_df = load_table(original_path)
    processed_df = clean_dataframe(raw_df)

    if processed_df.empty:
        raise ValueError("Dataset has no usable rows after cleaning.")

    processed_path = save_processed_dataframe(processed_df, processed_filename)
    file_hash = hashlib.sha256(content).hexdigest()
    overview = build_dataset_overview(processed_df)

    record = DatasetRecord(
        dataset_id=dataset_id,
        original_filename=original_filename,
        stored_filename=stored_filename,
        processed_filename=processed_filename,
        dataframe=processed_df,
        original_path=str(Path(original_path).as_posix()),
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
    return metadata
