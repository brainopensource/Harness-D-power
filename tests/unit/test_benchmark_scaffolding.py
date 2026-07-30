"""Unit tests for Block 2 scaffolding — benchmark domain models and adapter placeholders."""

from __future__ import annotations

import pytest

from sagiha.adapters.benchmark.harvester import GitCommitHarvester
from sagiha.adapters.benchmark.runner import LocalTaskRunner
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


@pytest.mark.asyncio
async def test_harvester_returns_empty_list() -> None:
    harvester = GitCommitHarvester()
    tasks = await harvester.harvest("/tmp/fake-repo")
    assert tasks == []


@pytest.mark.asyncio
async def test_harvester_validate_returns_false() -> None:
    harvester = GitCommitHarvester()
    task = _make_task()
    valid = await harvester.validate_task(task, "/tmp/fake-repo")
    assert valid is False


@pytest.mark.asyncio
async def test_runner_returns_not_implemented() -> None:
    runner = LocalTaskRunner()
    task = _make_task()
    result = await runner.run_task(task, "test-agent")
    assert result.resolved is False
    assert result.error is not None
    assert "Not implemented" in result.error


@pytest.mark.asyncio
async def test_runner_suite_completes() -> None:
    runner = LocalTaskRunner()
    task = _make_task()
    suite = BenchmarkSuite(
        suite_id="suite-001",
        repo="test",
        tasks=(task,),
    )
    run = await runner.run_suite(suite, "test-agent")
    assert run.status == "completed"
    assert len(run.results) == 1
