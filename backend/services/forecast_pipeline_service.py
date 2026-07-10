from __future__ import annotations

from backend.models.ai_insight_models import utc_now_iso
from backend.models.forecast_pipeline_models import (
    ALLOWED_STAGE_TRANSITIONS,
    CANONICAL_PIPELINE_STAGE_IDS,
    CANONICAL_PIPELINE_STAGE_NAMES,
    FORECAST_PIPELINE_SCHEMA_VERSION,
    ExecutionMode,
    ForecastPipeline,
    ForecastPipelineMetadata,
    PipelineDependencyEdge,
    PipelineDependencyGraph,
    PipelineStage,
    PipelineStatistics,
    PipelineStatus,
    PipelineSummary,
    StageStatus,
    empty_forecast_pipeline_future_extensions,
)

_STAGE_DESCRIPTIONS: dict[str, str] = {
    "dataset": "Resolve dataset context for forecasting. Metadata only.",
    "preparation": "Prepare inputs for forecasting. Metadata only.",
    "feature_engineering": "Declare feature engineering stage. No feature logic.",
    "forecast_adapter": "Select / bind forecast adapter contract. No execution.",
    "prediction": "Produce prediction objects via Prediction Engine. Not executed here.",
    "prediction_validation": "Validate predictions against outcomes. Not executed here.",
    "explanation": "Explain forecast outputs. Metadata only.",
    "cleanup": "Cleanup temporary forecast artifacts. Metadata only.",
    "output": "Emit forecast pipeline outputs. Metadata only.",
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


def pipeline_dependencies(pipeline: ForecastPipeline) -> PipelineDependencyGraph:
    """Build a metadata-only stage dependency graph."""
    by_id = {stage.stage_id: stage for stage in pipeline.stages}
    nodes = [stage.stage_id for stage in sorted(pipeline.stages, key=lambda s: s.stage_order)]
    edges: list[PipelineDependencyEdge] = []
    for stage in pipeline.stages:
        for dep_id in stage.dependencies:
            edges.append(
                PipelineDependencyEdge(
                    from_stage_id=stage.stage_id,
                    to_stage_id=dep_id,
                    edge_kind="depends_on",
                )
            )
            if dep_id not in by_id:
                continue
    return PipelineDependencyGraph(
        nodes=nodes,
        edges=edges,
        canonical_order=list(CANONICAL_PIPELINE_STAGE_IDS),
    )


def list_stages(pipeline: ForecastPipeline) -> list[PipelineStage]:
    """Return deep-copied stages ordered by stage_order."""
    ordered = sorted(pipeline.stages, key=lambda stage: stage.stage_order)
    return [stage.model_copy(deep=True) for stage in ordered]


def find_stage(pipeline: ForecastPipeline, stage_id: str) -> PipelineStage | None:
    for stage in pipeline.stages:
        if stage.stage_id == stage_id:
            return stage.model_copy(deep=True)
    return None


def next_stage(pipeline: ForecastPipeline) -> PipelineStage | None:
    """Return the next incomplete stage after current_stage (metadata only)."""
    ordered = sorted(pipeline.stages, key=lambda stage: stage.stage_order)
    if not ordered:
        return None

    if pipeline.current_stage is None:
        for stage in ordered:
            if stage.stage_status not in {StageStatus.completed, StageStatus.skipped}:
                return stage.model_copy(deep=True)
        return None

    found_current = False
    for stage in ordered:
        if stage.stage_id == pipeline.current_stage:
            found_current = True
            continue
        if found_current and stage.stage_status not in {
            StageStatus.completed,
            StageStatus.skipped,
        }:
            return stage.model_copy(deep=True)
    return None


def previous_stage(pipeline: ForecastPipeline) -> PipelineStage | None:
    """Return the previous stage before current_stage (metadata only)."""
    ordered = sorted(pipeline.stages, key=lambda stage: stage.stage_order)
    if not ordered or pipeline.current_stage is None:
        return None

    previous: PipelineStage | None = None
    for stage in ordered:
        if stage.stage_id == pipeline.current_stage:
            return previous.model_copy(deep=True) if previous is not None else None
        previous = stage
    return None


def pipeline_statistics(pipeline: ForecastPipeline) -> PipelineStatistics:
    completed = pending = failed = skipped = waiting = ready = running = 0
    required = optional = 0

    for stage in pipeline.stages:
        if stage.required:
            required += 1
        else:
            optional += 1
        if stage.stage_status == StageStatus.completed:
            completed += 1
        elif stage.stage_status == StageStatus.pending:
            pending += 1
        elif stage.stage_status == StageStatus.failed:
            failed += 1
        elif stage.stage_status == StageStatus.skipped:
            skipped += 1
        elif stage.stage_status == StageStatus.waiting:
            waiting += 1
        elif stage.stage_status == StageStatus.ready:
            ready += 1
        elif stage.stage_status == StageStatus.running:
            running += 1

    total = len(pipeline.stages)
    done = completed + skipped
    completion = round((done / total) * 100.0, 2) if total else 0.0

    return PipelineStatistics(
        total_stages=total,
        completed=completed,
        pending=pending,
        failed=failed,
        skipped=skipped,
        waiting=waiting,
        ready=ready,
        running=running,
        completion_percentage=completion,
        required_stage_count=required,
        optional_stage_count=optional,
    )


def pipeline_summary(pipeline: ForecastPipeline) -> PipelineSummary:
    stats = pipeline_statistics(pipeline)
    current_name = None
    if pipeline.current_stage:
        stage = find_stage(pipeline, pipeline.current_stage)
        current_name = stage.stage_name if stage is not None else pipeline.current_stage
    return PipelineSummary(
        pipeline_name=pipeline.pipeline_name,
        version=pipeline.pipeline_version,
        adapter=pipeline.adapter_id or "",
        current_stage=current_name,
        execution_mode=pipeline.execution_mode.value,
        overall_status=pipeline.pipeline_status.value,
        total_stages=stats.total_stages,
        completion_percentage=stats.completion_percentage,
    )


def validate_pipeline(pipeline: ForecastPipeline) -> dict[str, object]:
    """Structural integrity checks only — never executes the pipeline."""
    issues: list[str] = []

    if not pipeline.pipeline_id:
        issues.append("Missing pipeline_id")
    if not pipeline.pipeline_name:
        issues.append("Missing pipeline_name")

    if pipeline.execution_mode not in ExecutionMode:
        issues.append(f"Invalid execution_mode: {pipeline.execution_mode}")
    if pipeline.pipeline_status not in PipelineStatus:
        issues.append(f"Invalid pipeline_status: {pipeline.pipeline_status}")

    if not pipeline.stages:
        issues.append("Empty pipeline")

    seen_ids: set[str] = set()
    seen_orders: set[int] = set()
    stage_ids = {stage.stage_id for stage in pipeline.stages}

    for stage in pipeline.stages:
        if not stage.stage_id:
            issues.append("Stage missing stage_id")
            continue
        if stage.stage_id in seen_ids:
            issues.append(f"Duplicate stage_id: {stage.stage_id}")
        seen_ids.add(stage.stage_id)

        if stage.stage_order in seen_orders:
            issues.append(f"Duplicate stage_order: {stage.stage_order}")
        seen_orders.add(stage.stage_order)

        if stage.stage_status not in StageStatus:
            issues.append(f"Invalid stage_status: {stage.stage_id}")

        for dep_id in stage.dependencies:
            if dep_id not in stage_ids:
                issues.append(f"Broken dependency: {stage.stage_id} -> {dep_id}")

    # Required canonical stages for default-shaped pipelines (when using canonical ids).
    present_canonical = [sid for sid in CANONICAL_PIPELINE_STAGE_IDS if sid in stage_ids]
    if present_canonical:
        missing_required = [
            sid for sid in CANONICAL_PIPELINE_STAGE_IDS if sid not in stage_ids
        ]
        # Only flag missing required if pipeline claims to be a full canonical pipeline
        # (has at least dataset + output or majority of stages).
        if len(present_canonical) >= 5 and missing_required:
            for sid in missing_required:
                issues.append(f"Missing required stage: {sid}")

    if pipeline.current_stage and pipeline.current_stage not in stage_ids:
        issues.append(f"current_stage not in stages: {pipeline.current_stage}")

    for stage_id in pipeline.completed_stages:
        if stage_id not in stage_ids:
            issues.append(f"completed_stages references unknown stage: {stage_id}")
    for stage_id in pipeline.failed_stages:
        if stage_id not in stage_ids:
            issues.append(f"failed_stages references unknown stage: {stage_id}")
    for stage_id in pipeline.skipped_stages:
        if stage_id not in stage_ids:
            issues.append(f"skipped_stages references unknown stage: {stage_id}")

    # Invalid stage transitions encoded in metadata.debug (optional declared transitions).
    for stage in pipeline.stages:
        declared = stage.metadata.get("transition_from")
        if declared is None:
            continue
        try:
            from_status = StageStatus(str(declared))
        except ValueError:
            issues.append(f"Invalid transition_from on {stage.stage_id}: {declared}")
            continue
        allowed = ALLOWED_STAGE_TRANSITIONS.get(from_status, frozenset())
        if stage.stage_status not in allowed and stage.stage_status != from_status:
            issues.append(
                f"Invalid stage transition: {stage.stage_id} "
                f"{from_status.value} -> {stage.stage_status.value}"
            )

    required_extensions = set(empty_forecast_pipeline_future_extensions().keys())
    missing_extensions = sorted(
        required_extensions - set(pipeline.metadata.future_extensions.keys())
    )
    if missing_extensions:
        issues.append(f"Missing future_extensions: {', '.join(missing_extensions)}")

    graph_nodes = set(pipeline.dependencies.nodes)
    if graph_nodes and graph_nodes != stage_ids:
        missing = sorted(stage_ids - graph_nodes)
        extra = sorted(graph_nodes - stage_ids)
        if missing:
            issues.append(f"Dependency graph missing nodes: {', '.join(missing)}")
        if extra:
            issues.append(f"Dependency graph has unknown nodes: {', '.join(extra)}")

    return {
        "valid": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "pipeline_id": pipeline.pipeline_id,
        "stage_count": len(pipeline.stages),
    }


def build_pipeline(
    *,
    pipeline_name: str,
    stages: list[PipelineStage],
    dataset_id: str | None = None,
    adapter_id: str | None = None,
    adapter_type: str | None = None,
    execution_mode: ExecutionMode | str = ExecutionMode.manual,
    pipeline_status: PipelineStatus | str = PipelineStatus.draft,
    pipeline_id: str | None = None,
    pipeline_version: str = FORECAST_PIPELINE_SCHEMA_VERSION,
) -> ForecastPipeline:
    """Build a forecast pipeline from provided stage metadata. No execution."""
    now = utc_now_iso()
    mode = (
        execution_mode
        if isinstance(execution_mode, ExecutionMode)
        else ExecutionMode(str(execution_mode))
    )
    status = (
        pipeline_status
        if isinstance(pipeline_status, PipelineStatus)
        else PipelineStatus(str(pipeline_status))
    )
    stages_c = [stage.model_copy(deep=True) for stage in stages]
    stages_c.sort(key=lambda stage: stage.stage_order)

    completed = [s.stage_id for s in stages_c if s.stage_status == StageStatus.completed]
    failed = [s.stage_id for s in stages_c if s.stage_status == StageStatus.failed]
    skipped = [s.stage_id for s in stages_c if s.stage_status == StageStatus.skipped]

    current = None
    for stage in stages_c:
        if stage.stage_status not in {StageStatus.completed, StageStatus.skipped}:
            current = stage.stage_id
            break

    resolved_id = pipeline_id or f"pipeline_{dataset_id or 'empty'}_{now.replace(':', '').replace('-', '')}"
    pipeline = ForecastPipeline(
        pipeline_id=resolved_id,
        pipeline_name=pipeline_name,
        pipeline_version=pipeline_version,
        dataset_id=dataset_id,
        adapter_id=adapter_id,
        adapter_type=adapter_type,
        execution_mode=mode,
        pipeline_status=status,
        stages=stages_c,
        current_stage=current,
        completed_stages=completed,
        failed_stages=failed,
        skipped_stages=skipped,
        dependencies=PipelineDependencyGraph(),
        created_at=now,
        updated_at=now,
        metadata=ForecastPipelineMetadata(
            legacy={"schema": FORECAST_PIPELINE_SCHEMA_VERSION},
            debug={"stage_count": len(stages_c)},
            custom={},
            future_extensions=empty_forecast_pipeline_future_extensions(),
        ),
    )
    pipeline.dependencies = pipeline_dependencies(pipeline)
    return pipeline


def build_default_pipeline(
    *,
    dataset_id: str | None = None,
    adapter_id: str | None = None,
    adapter_type: str | None = None,
    execution_mode: ExecutionMode | str = ExecutionMode.manual,
    pipeline_name: str = "Default Forecast Pipeline",
) -> ForecastPipeline:
    """Build the canonical forecast pipeline representation. Metadata only."""
    stages: list[PipelineStage] = []
    for order, (stage_id, stage_name) in enumerate(
        zip(CANONICAL_PIPELINE_STAGE_IDS, CANONICAL_PIPELINE_STAGE_NAMES, strict=True),
        start=1,
    ):
        deps: list[str] = []
        if order > 1:
            deps = [CANONICAL_PIPELINE_STAGE_IDS[order - 2]]
        stages.append(
            PipelineStage(
                stage_id=stage_id,
                stage_name=stage_name,
                stage_order=order,
                stage_status=StageStatus.pending,
                required=True,
                dependencies=deps,
                description=_STAGE_DESCRIPTIONS.get(stage_id, ""),
                metadata={"canonical": True},
            )
        )

    return build_pipeline(
        pipeline_name=pipeline_name,
        stages=stages,
        dataset_id=dataset_id,
        adapter_id=adapter_id,
        adapter_type=adapter_type,
        execution_mode=execution_mode,
        pipeline_status=PipelineStatus.ready,
    )


def copy_pipeline(
    pipeline: ForecastPipeline,
    *,
    pipeline_id: str | None = None,
    pipeline_name: str | None = None,
) -> ForecastPipeline:
    """Deep-copy a pipeline with a new id/name. Does not mutate the original."""
    now = utc_now_iso()
    copy = pipeline.model_copy(deep=True)
    copy.pipeline_id = pipeline_id or f"copy_{pipeline.pipeline_id}_{now.replace(':', '').replace('-', '')}"
    if pipeline_name is not None:
        copy.pipeline_name = pipeline_name
    copy.created_at = now
    copy.updated_at = now
    copy.dependencies = pipeline_dependencies(copy)
    return copy
