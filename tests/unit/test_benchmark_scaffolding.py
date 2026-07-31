"""Unit tests for benchmark domain models.

`adapters/benchmark/` and `ports/benchmark.py` were deleted (ADR-0024) — `e0/` is the sole
implementation and its own tests live in `test_harvester.py`, `test_benchmark_runner.py`, and
`test_e0_statistics.py`. This file keeps only the domain-model round-trip coverage that has nothing
to do with the deleted stub adapters.
"""

from __future__ import annotations

from sagiha.domain.benchmark import (
    BenchmarkResult,
    BenchmarkSuite,
    HarvestedTask,
)


def _make_task() -> HarvestedTask:
    return HarvestedTask(
        task_id="task-001",
        repo="brainopensource/Harness-D-power",
        base_commit="abc123",
        target_commit="def456",
        diff_summary="Fix failing test in module X",
        failing_test_cmd="pytest tests/test_x.py -x",
        files_changed=("src/x.py",),
    )


def test_harvested_task_model_round_trip() -> None:
    task = _make_task()
    serialized = task.model_dump_json()
    restored = HarvestedTask.model_validate_json(serialized)
    assert restored.task_id == task.task_id
    assert restored.base_commit == task.base_commit
    assert restored.files_changed == ("src/x.py",)
    assert restored.validated is False


def test_benchmark_result_model_round_trip() -> None:
    result = BenchmarkResult(
        task_id="task-001",
        agent_id="sagiha-default",
        resolved=True,
        steps=5,
        wall_clock_s=12.3,
    )
    serialized = result.model_dump_json()
    restored = BenchmarkResult.model_validate_json(serialized)
    assert restored.resolved is True
    assert restored.steps == 5


def test_benchmark_suite_model_round_trip() -> None:
    task = _make_task()
    suite = BenchmarkSuite(
        suite_id="suite-001",
        repo="brainopensource/Harness-D-power",
        tasks=(task,),
    )
    serialized = suite.model_dump_json()
    restored = BenchmarkSuite.model_validate_json(serialized)
    assert len(restored.tasks) == 1
    assert restored.tasks[0].task_id == "task-001"
