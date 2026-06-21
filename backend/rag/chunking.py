from __future__ import annotations

import json
from typing import Any

import pandas as pd

from backend.processing.data_profiler import profile_dataframe
from backend.processing.schema_service import build_column_schema
from backend.rag.schemas import RagChunk
from backend.services.insight_service import get_insights


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def _compact_json(value: Any) -> str:
    return json.dumps(_json_safe(value), ensure_ascii=False, default=str, separators=(",", ":"))


def _safe_text(value: Any, max_chars: int = 900) -> str:
    text = str(value)
    return text if len(text) <= max_chars else f"{text[:max_chars]}..."


def _chunk_id(dataset_id: str, chunk_type: str, suffix: str | int) -> str:
    return f"{dataset_id}:{chunk_type}:{suffix}"


def build_rag_chunks(dataset_id: str, df: pd.DataFrame, max_row_samples: int = 20) -> list[RagChunk]:
    """Create compact semantic chunks from existing dataset artifacts and summaries."""
    chunks: list[RagChunk] = []
    column_schema = build_column_schema(df)
    profile = profile_dataframe(df)

    chunks.append(
        RagChunk(
            chunk_id=_chunk_id(dataset_id, "dataset_summary", "main"),
            dataset_id=dataset_id,
            chunk_type="dataset_summary",
            text=(
                f"Dataset {dataset_id} has {len(df)} rows and {len(df.columns)} columns. "
                f"Columns: {', '.join(map(str, df.columns.tolist()))}. "
                f"Duplicate rows: {profile.get('duplicate_rows', 0)}. "
                f"Total missing values: {profile.get('total_missing_values', 0)}."
            ),
            metadata={"row_count": len(df), "column_count": len(df.columns)},
        )
    )

    for column in column_schema:
        name = column["name"]
        chunks.append(
            RagChunk(
                chunk_id=_chunk_id(dataset_id, "schema_column", name),
                dataset_id=dataset_id,
                chunk_type="schema_column",
                text=(
                    f"Column {name}: dtype {column.get('dtype')}, semantic type {column.get('semantic_type')}, "
                    f"missing {column.get('missing_count')}, unique {column.get('unique_count')}, "
                    f"sample values {_compact_json(column.get('sample_values', []))}."
                ),
                metadata={
                    "column": name,
                    "dtype": column.get("dtype") or "",
                    "semantic_type": column.get("semantic_type") or "",
                    "missing_count": column.get("missing_count", 0),
                    "unique_count": column.get("unique_count", 0),
                },
            )
        )

    profile_sections = [
        "column_types",
        "numeric_summary",
        "categorical_summary",
        "date_summary",
        "outlier_summary",
        "correlation_summary",
        "trend_summary",
        "data_quality_score",
    ]
    for section in profile_sections:
        value = profile.get(section)
        if value:
            chunks.append(
                RagChunk(
                    chunk_id=_chunk_id(dataset_id, "profile_summary", section),
                    dataset_id=dataset_id,
                    chunk_type="profile_summary",
                    text=f"Profile section {section}: {_safe_text(_compact_json(value), max_chars=1400)}",
                    metadata={"section": section},
                )
            )

    try:
        insight_payload = get_insights(dataset_id)
        for index, insight in enumerate(insight_payload.get("insights", [])[:10]):
            title = insight.get("title") or insight.get("type") or f"Insight {index + 1}"
            chunks.append(
                RagChunk(
                    chunk_id=_chunk_id(dataset_id, "generated_insight", index),
                    dataset_id=dataset_id,
                    chunk_type="generated_insight",
                    text=f"Generated insight: {title}. {_compact_json(insight)}",
                    metadata={"insight_index": index, "title": title},
                )
            )
    except Exception:
        # Generated insights are optional. Indexing should still succeed without them.
        pass

    sample_count = max(0, min(max_row_samples, len(df)))
    if sample_count:
        sample_df = df.head(sample_count)
        for row_number, row in enumerate(sample_df.to_dict(orient="records"), start=1):
            chunks.append(
                RagChunk(
                    chunk_id=_chunk_id(dataset_id, "row_sample", row_number),
                    dataset_id=dataset_id,
                    chunk_type="row_sample",
                    text=f"Sample row {row_number}: {_safe_text(_compact_json(row), max_chars=1200)}",
                    metadata={"row_number": row_number, "sample_strategy": "head", "limited": True},
                )
            )

    return chunks
