from __future__ import annotations

from backend.models.forecast_dataset_models import (
    FORECAST_DATASET_FUTURE_EXTENSION_KEYS,
    READINESS_VALIDATION_SECTIONS,
    ReadinessStatus,
    TimeGranularity,
    ValidationCheckStatus,
)
from backend.services.forecast_dataset_service import (
    build_dataset_readiness,
    dataset_statistics,
    dataset_summary,
    find_validation,
    list_validations,
    readiness_recommendations,
    readiness_score,
    validate_dataset_readiness,
)


def test_dataset_readiness_creation():
    readiness = build_dataset_readiness(
        dataset_id="sales_q1",
        dataset_name="Sales Q1",
        time_column="date",
        target_column="revenue",
        feature_columns=["region", "channel"],
        record_count=1200,
        time_granularity="daily",
        missing_values={"revenue": 0},
        date_range={"start": "2024-01-01", "end": "2024-03-31"},
    )
    assert readiness.dataset_id == "sales_q1"
    assert readiness.readiness_status in {
        ReadinessStatus.ready,
        ReadinessStatus.excellent,
        ReadinessStatus.partially_ready,
    }
    assert readiness.overall_score >= 75
    assert readiness.time_granularity == TimeGranularity.daily
    assert len(readiness.validation_results) >= 7
    assert set(READINESS_VALIDATION_SECTIONS).issubset(
        {item.section for item in readiness.validation_results}
    )


def test_validation_summary_statistics():
    readiness = build_dataset_readiness(
        dataset_id="sales_q1",
        time_column="date",
        target_column="revenue",
        feature_columns=["region"],
        record_count=100,
        time_granularity=TimeGranularity.weekly,
        missing_values={},
    )
    result = validate_dataset_readiness(readiness)
    assert result["valid"] is True

    summary = dataset_summary(readiness)
    assert summary.dataset_name
    assert summary.time_column == "date"
    assert summary.target_column == "revenue"
    assert summary.granularity == TimeGranularity.weekly.value

    stats = dataset_statistics(readiness)
    assert stats.validation_count == len(readiness.validation_results)
    assert stats.passed_checks >= 1
    assert find_validation(readiness, "val_dataset_identity") is not None
    assert len(list_validations(readiness)) == stats.validation_count


def test_score_and_recommendations():
    score = readiness_score(
        dataset_id="ds",
        time_column="ts",
        target_column="y",
        feature_columns=["a"],
        record_count=10,
        time_granularity=TimeGranularity.daily,
        missing_values={},
    )
    assert score == 100.0

    empty_score = readiness_score(
        dataset_id=None,
        time_column=None,
        target_column=None,
        feature_columns=[],
        record_count=None,
        time_granularity=TimeGranularity.unknown,
        missing_values=None,
    )
    assert empty_score == 0.0

    recs = readiness_recommendations(
        dataset_id=None,
        time_column=None,
        target_column=None,
        feature_columns=[],
        record_count=None,
        time_granularity=TimeGranularity.unknown,
        missing_values=None,
        duplicate_feature_names=False,
    )
    assert any("dataset_id" in item for item in recs)
    assert any("time_column" in item for item in recs)


def test_invalid_metadata_and_duplicates():
    incomplete = build_dataset_readiness(dataset_name="Incomplete")
    assert incomplete.readiness_status in {
        ReadinessStatus.not_ready,
        ReadinessStatus.unknown,
        ReadinessStatus.partially_ready,
    }
    result = validate_dataset_readiness(incomplete)
    assert result["valid"] is False
    assert any("Missing dataset_id" in issue for issue in result["issues"])
    assert any("Missing time_column" in issue for issue in result["issues"])
    assert any("Missing target_column" in issue for issue in result["issues"])

    empty = build_dataset_readiness(
        dataset_id="empty_ds",
        time_column="date",
        target_column="y",
        record_count=0,
    )
    assert any("Empty dataset" in issue for issue in validate_dataset_readiness(empty)["issues"])

    negative = build_dataset_readiness(
        dataset_id="neg",
        time_column="date",
        target_column="y",
        record_count=-1,
    )
    assert any("Negative record_count" in issue for issue in validate_dataset_readiness(negative)["issues"])

    dup_features = build_dataset_readiness(
        dataset_id="dup",
        time_column="date",
        target_column="y",
        feature_columns=["a", "A", "b"],
        record_count=10,
        time_granularity="daily",
        missing_values={},
    )
    assert any(
        item.check_name == "feature_names_unique" and item.status == ValidationCheckStatus.failed
        for item in dup_features.validation_results
    )
    assert any("Duplicate feature names" in issue for issue in validate_dataset_readiness(dup_features)["issues"])

    # Duplicate validation ids
    broken = incomplete.model_copy(deep=True)
    if len(broken.validation_results) >= 2:
        broken.validation_results[1] = broken.validation_results[1].model_copy(
            update={"validation_id": broken.validation_results[0].validation_id}
        )
        assert any(
            "Duplicate validation_id" in issue for issue in validate_dataset_readiness(broken)["issues"]
        )


def test_future_extension_buckets():
    readiness = build_dataset_readiness(dataset_id="sales_q1")
    for key in FORECAST_DATASET_FUTURE_EXTENSION_KEYS:
        assert key in readiness.metadata.future_extensions
        assert readiness.metadata.future_extensions[key] == {}
    assert "seasonality" in readiness.metadata.future_extensions
    assert "feature_engineering" in readiness.metadata.future_extensions
    assert "live_validation" in readiness.metadata.future_extensions


def test_immutability():
    readiness = build_dataset_readiness(
        dataset_id="sales_q1",
        time_column="date",
        target_column="revenue",
        record_count=50,
        time_granularity="monthly",
        missing_values={},
    )
    snapshot = readiness.model_dump()
    found = find_validation(readiness, "val_dataset_identity")
    assert found is not None
    found.message = "mutated"
    listed = list_validations(readiness)
    listed[0].message = "mutated_list"
    dataset_summary(readiness)
    dataset_statistics(readiness)
    validate_dataset_readiness(readiness)
    assert readiness.model_dump() == snapshot
