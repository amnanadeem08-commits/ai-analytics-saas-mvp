from __future__ import annotations

import asyncio

import pytest

from uuid import uuid4

from backend.services import dataset_service, storage_service


SAMPLE_CSV = b"region,sales\nNorth,100\nSouth,150\n"


def setup_function():
    storage_service.reset_storage()
    dataset_service.reset_datasets()


def test_create_dataset_links_storage_object():
    from io import BytesIO

    from starlette.datastructures import UploadFile

    file = UploadFile(filename="sales.csv", file=BytesIO(SAMPLE_CSV))
    meta = asyncio.run(dataset_service.create_dataset(file))
    assert meta.get("dataset_id")
    assert meta.get("storage_object_id")
    summary = dataset_service.dataset_summary(meta["dataset_id"])
    assert summary["version_count"] >= 1


def test_new_version_increments_storage_version():
    obj = storage_service.upload(SAMPLE_CSV, "sales.csv", artifact_type="dataset")
    dataset_id = f"ds_test_{uuid4().hex[:8]}"
    from backend.storage.metadata_store import add_dataset

    add_dataset(
        {
            "dataset_id": dataset_id,
            "original_filename": "sales.csv",
            "storage_object_id": obj.object_id,
            "overview": {"row_count": 2, "column_count": 2},
            "upload_time": "2024-01-01T00:00:00Z",
            "file_hash": "abc",
        }
    )
    updated = dataset_service.new_version(dataset_id, SAMPLE_CSV + b"East,90\n", "sales_v2.csv")
    assert updated.get("storage_version", 0) >= 2


def test_dataset_archive_restore_delete():
    obj = storage_service.upload(SAMPLE_CSV, "sales.csv", artifact_type="dataset")
    dataset_id = f"ds_lifecycle_{uuid4().hex[:8]}"
    from backend.storage.metadata_store import add_dataset

    add_dataset(
        {
            "dataset_id": dataset_id,
            "original_filename": "sales.csv",
            "storage_object_id": obj.object_id,
            "overview": {},
            "upload_time": "2024-01-01T00:00:00Z",
        }
    )
    archived = dataset_service.archive_dataset(dataset_id)
    assert archived.get("dataset_status") == "archived"
    restored = dataset_service.restore_dataset(dataset_id)
    assert restored.get("dataset_status") == "active"
    deleted = dataset_service.delete_dataset(dataset_id)
    assert deleted.get("dataset_status") == "deleted"
