from __future__ import annotations

from typing import Any

from backend.models.ai_insight_models import utc_now_iso
from backend.models.forecast_dataset_models import (
    FORECAST_DATASET_SCHEMA_VERSION,
    READINESS_VALIDATION_SECTIONS,
    ForecastDatasetMetadata,
    ForecastDatasetReadiness,
    ForecastDatasetStatistics,
    ForecastDatasetSummary,
    ReadinessStatus,
    ReadinessValidationResult,
    TimeGranularity,
    ValidationCheckStatus,
    empty_forecast_dataset_future_extensions,
)

# Metadata-only score weights. No dataframe / statistical quality evaluation.
_SCORE_WEIGHTS: dict[str, float] = {
    "dataset_identity": 15.0,
    "time_column": 20.0,
    "target_column": 20.0,
    "feature_columns": 10.0,
    "record_count": 10.0,
    "granularity": 10.0,
    "completeness_metadata": 15.0,
}


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _parse_granularity(raw: Any) -> TimeGranularity:
    if raw is None or raw == "":
        return TimeGranularity.unknown
    if isinstance(raw, TimeGranularity):
        return raw
    text = str(raw).strip().lower()
    aliases = {
        "h": TimeGranularity.hourly,
        "hour": TimeGranularity.hourly,
        "hourly": TimeGranularity.hourly,
        "d": TimeGranularity.daily,
        "day": TimeGranularity.daily,
        "daily": TimeGranularity.daily,
        "w": TimeGranularity.weekly,
        "week": TimeGranularity.weekly,
        "weekly": TimeGranularity.weekly,
        "m": TimeGranularity.monthly,
        "month": TimeGranularity.monthly,
        "monthly": TimeGranularity.monthly,
        "q": TimeGranularity.quarterly,
        "quarter": TimeGranularity.quarterly,
        "quarterly": TimeGranularity.quarterly,
        "y": TimeGranularity.yearly,
        "year": TimeGranularity.yearly,
        "yearly": TimeGranularity.yearly,
        "custom": TimeGranularity.custom,
    }
    return aliases.get(text, TimeGranularity.unknown)


def readiness_score(
    *,
    dataset_id: str | None,
    time_column: str | None,
    target_column: str | None,
    feature_columns: list[str] | None,
    record_count: int | None,
    time_granularity: TimeGranularity,
    missing_values: dict[str, Any] | None,
) -> float:
    """Compute a metadata-only readiness score. Never inspects dataframe values."""
    score = 0.0
    if dataset_id:
        score += _SCORE_WEIGHTS["dataset_identity"]
    if time_column:
        score += _SCORE_WEIGHTS["time_column"]
    if target_column:
        score += _SCORE_WEIGHTS["target_column"]
    if feature_columns:
        score += _SCORE_WEIGHTS["feature_columns"]
    if record_count is not None and record_count > 0:
        score += _SCORE_WEIGHTS["record_count"]
    if time_granularity != TimeGranularity.unknown:
        score += _SCORE_WEIGHTS["granularity"]
    if missing_values is not None and isinstance(missing_values, dict):
        # Presence of completeness metadata earns the weight; values are not analyzed.
        score += _SCORE_WEIGHTS["completeness_metadata"]
    return round(min(100.0, max(0.0, score)), 2)


def _status_from_score(score: float, *, has_critical_failures: bool) -> ReadinessStatus:
    if has_critical_failures:
        if score >= 50:
            return ReadinessStatus.partially_ready
        return ReadinessStatus.not_ready
    if score >= 95:
        return ReadinessStatus.excellent
    if score >= 75:
        return ReadinessStatus.ready
    if score >= 40:
        return ReadinessStatus.partially_ready
    if score > 0:
        return ReadinessStatus.not_ready
    return ReadinessStatus.unknown


def readiness_recommendations(
    *,
    dataset_id: str | None,
    time_column: str | None,
    target_column: str | None,
    feature_columns: list[str] | None,
    record_count: int | None,
    time_granularity: TimeGranularity,
    missing_values: dict[str, Any] | None,
    duplicate_feature_names: bool,
) -> list[str]:
    """Rule-based metadata recommendations. No forecasting advice beyond readiness."""
    recommendations: list[str] = []
    if not dataset_id:
        recommendations.append("Provide a dataset_id before forecasting readiness can be confirmed.")
    if not time_column:
        recommendations.append("Declare a time_column for time-index readiness.")
    if not target_column:
        recommendations.append("Declare a target_column for forecast target readiness.")
    if not feature_columns:
        recommendations.append("Optionally declare feature_columns for multivariate forecast readiness.")
    if record_count is None:
        recommendations.append("Provide record_count metadata (do not require dataframe inspection).")
    elif record_count <= 0:
        recommendations.append("record_count must be greater than zero.")
    if time_granularity == TimeGranularity.unknown:
        recommendations.append("Declare time_granularity (hourly/daily/weekly/monthly/...).")
    if missing_values is None:
        recommendations.append("Provide missing_values metadata map for completeness tracking.")
    if duplicate_feature_names:
        recommendations.append("Remove duplicate feature column names from metadata.")
    if not recommendations:
        recommendations.append("Metadata readiness looks complete for future forecasting engines.")
    return recommendations


def list_validations(readiness: ForecastDatasetReadiness) -> list[ReadinessValidationResult]:
    return [item.model_copy(deep=True) for item in readiness.validation_results]


def find_validation(
    readiness: ForecastDatasetReadiness,
    validation_id: str,
) -> ReadinessValidationResult | None:
    for item in readiness.validation_results:
        if item.validation_id == validation_id:
            return item.model_copy(deep=True)
    return None


def dataset_statistics(readiness: ForecastDatasetReadiness) -> ForecastDatasetStatistics:
    passed = failed = warning = 0
    missing_fields: list[str] = []
    for item in readiness.validation_results:
        if item.status == ValidationCheckStatus.passed:
            passed += 1
        elif item.status == ValidationCheckStatus.failed:
            failed += 1
            if item.field:
                missing_fields.append(item.field)
        elif item.status == ValidationCheckStatus.warning:
            warning += 1
    return ForecastDatasetStatistics(
        validation_count=len(readiness.validation_results),
        warning_count=len(readiness.warnings),
        recommendation_count=len(readiness.recommendations),
        missing_fields=_unique(missing_fields),
        passed_checks=passed,
        failed_checks=failed,
    )


def dataset_summary(readiness: ForecastDatasetReadiness) -> ForecastDatasetSummary:
    return ForecastDatasetSummary(
        dataset_name=readiness.dataset_name or readiness.dataset_id or "",
        status=readiness.readiness_status.value,
        overall_score=readiness.overall_score,
        record_count=readiness.record_count,
        time_column=readiness.time_column,
        target_column=readiness.target_column,
        granularity=readiness.time_granularity.value,
        recommendation_count=len(readiness.recommendations),
        warning_count=len(readiness.warnings),
    )


def validate_dataset_readiness(readiness: ForecastDatasetReadiness) -> dict[str, object]:
    """Structural integrity of a readiness object. Never inspects dataframes."""
    issues: list[str] = []

    if not readiness.readiness_id:
        issues.append("Missing readiness_id")
    if not readiness.dataset_id:
        issues.append("Missing dataset_id")
    if not readiness.target_column:
        issues.append("Missing target_column")
    if not readiness.time_column:
        issues.append("Missing time_column")

    if readiness.record_count is not None and readiness.record_count < 0:
        issues.append("Negative record_count")
    if readiness.record_count == 0:
        issues.append("Empty dataset")

    if readiness.time_granularity not in TimeGranularity:
        issues.append(f"Invalid granularity: {readiness.time_granularity}")

    feature_names = [name.strip().lower() for name in readiness.feature_columns if name]
    if len(feature_names) != len(set(feature_names)):
        issues.append("Duplicate feature names")

    seen_validation_ids: set[str] = set()
    for item in readiness.validation_results:
        if not item.validation_id:
            issues.append("Validation missing validation_id")
            continue
        if item.validation_id in seen_validation_ids:
            issues.append(f"Duplicate validation_id: {item.validation_id}")
        seen_validation_ids.add(item.validation_id)

    required_extensions = set(empty_forecast_dataset_future_extensions().keys())
    missing_extensions = sorted(
        required_extensions - set(readiness.metadata.future_extensions.keys())
    )
    if missing_extensions:
        issues.append(f"Missing future_extensions: {', '.join(missing_extensions)}")

    return {
        "valid": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "readiness_id": readiness.readiness_id,
        "sections": list(READINESS_VALIDATION_SECTIONS),
    }


def _build_validation_results(
    *,
    dataset_id: str | None,
    time_column: str | None,
    target_column: str | None,
    feature_columns: list[str],
    record_count: int | None,
    time_granularity: TimeGranularity,
    missing_values: dict[str, Any] | None,
    duplicate_feature_names: bool,
) -> list[ReadinessValidationResult]:
    results: list[ReadinessValidationResult] = []

    def add(
        validation_id: str,
        section: str,
        check_name: str,
        status: ValidationCheckStatus,
        message: str,
        field: str = "",
    ) -> None:
        results.append(
            ReadinessValidationResult(
                validation_id=validation_id,
                section=section,
                check_name=check_name,
                status=status,
                message=message,
                field=field,
            )
        )

    add(
        "val_dataset_identity",
        "Dataset Identity",
        "dataset_id_present",
        ValidationCheckStatus.passed if dataset_id else ValidationCheckStatus.failed,
        "dataset_id is present." if dataset_id else "dataset_id is missing.",
        "dataset_id",
    )
    add(
        "val_time_index",
        "Time Index",
        "time_column_present",
        ValidationCheckStatus.passed if time_column else ValidationCheckStatus.failed,
        "time_column is present." if time_column else "time_column is missing.",
        "time_column",
    )
    add(
        "val_target_variable",
        "Target Variable",
        "target_column_present",
        ValidationCheckStatus.passed if target_column else ValidationCheckStatus.failed,
        "target_column is present." if target_column else "target_column is missing.",
        "target_column",
    )
    add(
        "val_feature_availability",
        "Feature Availability",
        "feature_columns_declared",
        ValidationCheckStatus.passed
        if feature_columns
        else ValidationCheckStatus.warning,
        "feature_columns declared."
        if feature_columns
        else "feature_columns not declared (optional for univariate).",
        "feature_columns",
    )
    if duplicate_feature_names:
        add(
            "val_feature_duplicates",
            "Feature Availability",
            "feature_names_unique",
            ValidationCheckStatus.failed,
            "Duplicate feature column names detected in metadata.",
            "feature_columns",
        )
    else:
        add(
            "val_feature_duplicates",
            "Feature Availability",
            "feature_names_unique",
            ValidationCheckStatus.passed,
            "Feature column names are unique.",
            "feature_columns",
        )

    if record_count is None:
        add(
            "val_data_completeness_count",
            "Data Completeness",
            "record_count_present",
            ValidationCheckStatus.failed,
            "record_count metadata is missing.",
            "record_count",
        )
    elif record_count < 0:
        add(
            "val_data_completeness_count",
            "Data Completeness",
            "record_count_non_negative",
            ValidationCheckStatus.failed,
            "record_count is negative.",
            "record_count",
        )
    elif record_count == 0:
        add(
            "val_data_completeness_count",
            "Data Completeness",
            "dataset_non_empty",
            ValidationCheckStatus.failed,
            "Empty dataset (record_count == 0).",
            "record_count",
        )
    else:
        add(
            "val_data_completeness_count",
            "Data Completeness",
            "record_count_present",
            ValidationCheckStatus.passed,
            "record_count metadata is present and positive.",
            "record_count",
        )

    add(
        "val_data_completeness_missing",
        "Data Completeness",
        "missing_values_metadata",
        ValidationCheckStatus.passed
        if missing_values is not None
        else ValidationCheckStatus.warning,
        "missing_values metadata provided."
        if missing_values is not None
        else "missing_values metadata not provided.",
        "missing_values",
    )
    add(
        "val_data_consistency_granularity",
        "Data Consistency",
        "granularity_declared",
        ValidationCheckStatus.passed
        if time_granularity != TimeGranularity.unknown
        else ValidationCheckStatus.failed,
        f"time_granularity={time_granularity.value}",
        "time_granularity",
    )

    critical_ok = bool(dataset_id and time_column and target_column and record_count and record_count > 0)
    add(
        "val_forecast_compatibility",
        "Forecast Compatibility",
        "minimum_forecast_metadata",
        ValidationCheckStatus.passed if critical_ok else ValidationCheckStatus.failed,
        "Minimum forecast metadata present."
        if critical_ok
        else "Minimum forecast metadata incomplete.",
        "forecast_compatibility",
    )
    return results


def build_dataset_readiness(
    *,
    dataset_id: str | None = None,
    dataset_name: str = "",
    time_column: str | None = None,
    target_column: str | None = None,
    feature_columns: list[str] | None = None,
    record_count: int | None = None,
    time_granularity: TimeGranularity | str | None = None,
    missing_values: dict[str, Any] | None = None,
    duplicate_records: int | None = None,
    date_range: dict[str, Any] | None = None,
    recommended_frequency: str = "",
) -> ForecastDatasetReadiness:
    """Build a metadata-only dataset readiness assessment.

    Does not load datasets, inspect dataframes, train, or forecast.
    """
    now = utc_now_iso()
    features = list(feature_columns or [])
    feature_keys = [name.strip().lower() for name in features if name]
    duplicate_feature_names = len(feature_keys) != len(set(feature_keys))
    granularity = _parse_granularity(time_granularity)
    missing_meta = dict(missing_values) if missing_values is not None else None

    score = readiness_score(
        dataset_id=dataset_id,
        time_column=time_column,
        target_column=target_column,
        feature_columns=features,
        record_count=record_count,
        time_granularity=granularity,
        missing_values=missing_meta,
    )
    validations = _build_validation_results(
        dataset_id=dataset_id,
        time_column=time_column,
        target_column=target_column,
        feature_columns=features,
        record_count=record_count,
        time_granularity=granularity,
        missing_values=missing_meta,
        duplicate_feature_names=duplicate_feature_names,
    )
    critical_failures = any(
        item.status == ValidationCheckStatus.failed
        and item.field in {"dataset_id", "time_column", "target_column", "record_count"}
        for item in validations
    )
    status = _status_from_score(score, has_critical_failures=critical_failures)
    recommendations = readiness_recommendations(
        dataset_id=dataset_id,
        time_column=time_column,
        target_column=target_column,
        feature_columns=features,
        record_count=record_count,
        time_granularity=granularity,
        missing_values=missing_meta,
        duplicate_feature_names=duplicate_feature_names,
    )
    warnings = [
        item.message
        for item in validations
        if item.status in {ValidationCheckStatus.warning, ValidationCheckStatus.failed}
    ]

    if not recommended_frequency and granularity != TimeGranularity.unknown:
        recommended_frequency = granularity.value

    readiness_id = f"readiness_{dataset_id or 'unknown'}_{now.replace(':', '').replace('-', '')}"
    return ForecastDatasetReadiness(
        readiness_id=readiness_id,
        dataset_id=dataset_id,
        dataset_name=dataset_name or (dataset_id or ""),
        readiness_status=status,
        overall_score=score,
        time_column=time_column,
        target_column=target_column,
        feature_columns=features,
        record_count=record_count,
        time_granularity=granularity,
        missing_values=missing_meta or {},
        duplicate_records=duplicate_records,
        date_range=dict(date_range or {}),
        recommended_frequency=recommended_frequency,
        warnings=warnings,
        recommendations=recommendations,
        validation_results=validations,
        created_at=now,
        updated_at=now,
        metadata=ForecastDatasetMetadata(
            legacy={"schema": FORECAST_DATASET_SCHEMA_VERSION},
            debug={
                "section_count": len(READINESS_VALIDATION_SECTIONS),
                "validation_count": len(validations),
                "score_weights": dict(_SCORE_WEIGHTS),
            },
            custom={},
            future_extensions=empty_forecast_dataset_future_extensions(),
        ),
    )
