from __future__ import annotations

from backend.models.forecast_pipeline_models import (
    CANONICAL_PIPELINE_STAGE_IDS,
    FORECAST_PIPELINE_FUTURE_EXTENSION_KEYS,
    ExecutionMode,
    PipelineStage,
    PipelineStatus,
    StageStatus,
)
from backend.services.forecast_pipeline_service import (
    build_default_pipeline,
    build_pipeline,
    copy_pipeline,
    find_stage,
    list_stages,
    next_stage,
    pipeline_dependencies,
    pipeline_statistics,
    pipeline_summary,
    previous_stage,
    validate_pipeline,
)


def test_default_pipeline_creation_and_ordering():
    pipeline = build_default_pipeline(
        dataset_id="sales_q1",
        adapter_id="statistical_adapter",
        adapter_type="Statistical",
        execution_mode=ExecutionMode.manual,
    )
    assert pipeline.pipeline_status == PipelineStatus.ready
    assert pipeline.dataset_id == "sales_q1"
    assert pipeline.adapter_id == "statistical_adapter"
    assert len(pipeline.stages) == 9
    assert [s.stage_id for s in list_stages(pipeline)] == list(CANONICAL_PIPELINE_STAGE_IDS)
    assert [s.stage_order for s in list_stages(pipeline)] == list(range(1, 10))
    assert validate_pipeline(pipeline)["valid"] is True


def test_pipeline_creation_custom_stages():
    stages = [
        PipelineStage(stage_id="a", stage_name="A", stage_order=1, required=True),
        PipelineStage(
            stage_id="b",
            stage_name="B",
            stage_order=2,
            required=True,
            dependencies=["a"],
        ),
    ]
    pipeline = build_pipeline(
        pipeline_name="Custom",
        stages=stages,
        dataset_id="ds1",
        execution_mode="batch",
        pipeline_status="draft",
    )
    assert pipeline.execution_mode == ExecutionMode.batch
    assert pipeline.current_stage == "a"
    assert find_stage(pipeline, "b") is not None
    assert validate_pipeline(pipeline)["valid"] is True


def test_dependency_graph():
    pipeline = build_default_pipeline(dataset_id="sales_q1")
    graph = pipeline_dependencies(pipeline)
    assert graph.nodes == list(CANONICAL_PIPELINE_STAGE_IDS)
    assert graph.canonical_order == list(CANONICAL_PIPELINE_STAGE_IDS)
    assert len(graph.edges) == 8
    assert graph.edges[0].from_stage_id == "preparation"
    assert graph.edges[0].to_stage_id == "dataset"
    assert graph.edges[-1].from_stage_id == "output"
    assert graph.edges[-1].to_stage_id == "cleanup"
    assert pipeline.dependencies.nodes == graph.nodes


def test_summary_and_statistics():
    pipeline = build_default_pipeline(
        dataset_id="sales_q1",
        adapter_id="hybrid_adapter",
    )
    summary = pipeline_summary(pipeline)
    assert summary.pipeline_name == pipeline.pipeline_name
    assert summary.adapter == "hybrid_adapter"
    assert summary.total_stages == 9
    assert summary.completion_percentage == 0.0
    assert summary.execution_mode == ExecutionMode.manual.value

    stats = pipeline_statistics(pipeline)
    assert stats.total_stages == 9
    assert stats.pending == 9
    assert stats.required_stage_count == 9
    assert stats.optional_stage_count == 0
    assert stats.completion_percentage == 0.0

    # Mark some stages completed via a rebuilt pipeline copy
    stages = list_stages(pipeline)
    stages[0] = stages[0].model_copy(update={"stage_status": StageStatus.completed})
    stages[1] = stages[1].model_copy(update={"stage_status": StageStatus.skipped})
    updated = build_pipeline(
        pipeline_name=pipeline.pipeline_name,
        stages=stages,
        dataset_id=pipeline.dataset_id,
        adapter_id=pipeline.adapter_id,
        pipeline_status=PipelineStatus.running,
    )
    stats2 = pipeline_statistics(updated)
    assert stats2.completed == 1
    assert stats2.skipped == 1
    assert stats2.completion_percentage == round((2 / 9) * 100.0, 2)


def test_next_previous_find_stage():
    pipeline = build_default_pipeline(dataset_id="sales_q1")
    assert find_stage(pipeline, "prediction") is not None
    assert find_stage(pipeline, "missing") is None

    # current_stage starts at first incomplete (dataset)
    assert pipeline.current_stage == "dataset"
    nxt = next_stage(pipeline)
    assert nxt is not None
    assert nxt.stage_id == "preparation"

    prev = previous_stage(pipeline)
    assert prev is None  # current is first

    # Move current to feature_engineering via copy + update
    moved = pipeline.model_copy(update={"current_stage": "feature_engineering"}, deep=True)
    assert previous_stage(moved).stage_id == "preparation"
    assert next_stage(moved).stage_id == "forecast_adapter"


def test_validation_errors():
    empty = build_pipeline(pipeline_name="Empty", stages=[])
    result = validate_pipeline(empty)
    assert result["valid"] is False
    assert any("Empty pipeline" in issue for issue in result["issues"])

    stages = [
        PipelineStage(stage_id="dup", stage_name="A", stage_order=1),
        PipelineStage(stage_id="dup", stage_name="B", stage_order=2),
    ]
    dup_id = build_pipeline(pipeline_name="DupID", stages=stages)
    assert any("Duplicate stage_id" in i for i in validate_pipeline(dup_id)["issues"])

    stages2 = [
        PipelineStage(stage_id="a", stage_name="A", stage_order=1),
        PipelineStage(stage_id="b", stage_name="B", stage_order=1),
    ]
    dup_order = build_pipeline(pipeline_name="DupOrder", stages=stages2)
    assert any("Duplicate stage_order" in i for i in validate_pipeline(dup_order)["issues"])

    broken = build_pipeline(
        pipeline_name="Broken",
        stages=[
            PipelineStage(
                stage_id="a",
                stage_name="A",
                stage_order=1,
                dependencies=["missing"],
            )
        ],
    )
    assert any("Broken dependency" in i for i in validate_pipeline(broken)["issues"])

    bad_transition = build_pipeline(
        pipeline_name="BadTransition",
        stages=[
            PipelineStage(
                stage_id="a",
                stage_name="A",
                stage_order=1,
                stage_status=StageStatus.completed,
                metadata={"transition_from": "pending"},
            )
        ],
    )
    assert any("Invalid stage transition" in i for i in validate_pipeline(bad_transition)["issues"])


def test_copy_pipeline_and_future_buckets():
    pipeline = build_default_pipeline(dataset_id="sales_q1", adapter_id="statistical_adapter")
    for key in FORECAST_PIPELINE_FUTURE_EXTENSION_KEYS:
        assert key in pipeline.metadata.future_extensions
        assert pipeline.metadata.future_extensions[key] == {}

    copied = copy_pipeline(pipeline, pipeline_name="Copied Pipeline")
    assert copied.pipeline_id != pipeline.pipeline_id
    assert copied.pipeline_name == "Copied Pipeline"
    assert [s.stage_id for s in copied.stages] == [s.stage_id for s in pipeline.stages]
    assert validate_pipeline(copied)["valid"] is True


def test_immutability():
    pipeline = build_default_pipeline(dataset_id="sales_q1")
    snapshot = pipeline.model_dump()
    found = find_stage(pipeline, "dataset")
    assert found is not None
    found.stage_name = "mutated"
    listed = list_stages(pipeline)
    listed[0].stage_name = "mutated_list"
    next_stage(pipeline)
    previous_stage(pipeline)
    pipeline_summary(pipeline)
    pipeline_statistics(pipeline)
    pipeline_dependencies(pipeline)
    validate_pipeline(pipeline)
    copy_pipeline(pipeline)
    assert pipeline.model_dump() == snapshot
