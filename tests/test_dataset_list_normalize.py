from __future__ import annotations

from backend.models.dataset_models import DatasetMetadata
from backend.services.dataset_service import _normalize_dataset_metadata, get_all_datasets


def test_normalize_partial_storage_metadata() -> None:
    raw = {
        "dataset_id": "ds_test_manual",
        "original_filename": "sales.csv",
        "storage_object_id": "obj_x",
        "overview": {"row_count": 2, "column_count": 2},
        "upload_time": "2024-01-01T00:00:00Z",
        "file_hash": "abc",
    }
    normalized = _normalize_dataset_metadata(raw)
    model = DatasetMetadata.model_validate(normalized)
    assert model.dataset_id == "ds_test_manual"
    assert model.stored_filename == "sales.csv"
    assert model.row_count == 2
    assert model.column_count == 2
    assert model.columns == []


def test_get_all_datasets_skips_deleted_and_validates() -> None:
    for item in get_all_datasets():
        assert str(item.get("status", "")).lower() != "deleted"
        DatasetMetadata.model_validate(item)
