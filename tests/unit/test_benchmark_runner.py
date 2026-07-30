"""Unit tests for BenchmarkRunner."""

from __future__ import annotations

from pathlib import Path

import pytest

from sagiha.domain.benchmark import BenchmarkSuite, HarvestedTask
from sagiha.e0.runner import BenchmarkRunner


@pytest.mark.asyncio
async def test_benchmark_runner_single_task(tmp_path: Path) -> None:
    task = HarvestedTask(
        task_id="t1",
        repo=str(tmp_path),
        base_commit="c1",
        target_commit="c2",
        diff_summary="fix thing",
        failing_test_cmd="true",
        files_changed=("src/a.py",),
    )
    suite = BenchmarkSuite(suite_id="s1", repo=str(tmp_path), tasks=(task,))

    runner = BenchmarkRunner(
        suite=suite,
        model_mode="replay",
        cassette_path="tests/fixtures/replay_smoke/cassette.json",
        workspace_root=str(tmp_path),
    )

    result = await runner.run_single_task(task)
    assert result.task_id == "t1"
    assert isinstance(result.resolved, bool)
    assert result.wall_clock_s > 0


@pytest.mark.asyncio
async def test_benchmark_runner_suite_run(tmp_path: Path) -> None:
    task = HarvestedTask(
        task_id="t1",
        repo=str(tmp_path),
        base_commit="c1",
        target_commit="c2",
        diff_summary="fix thing",
        failing_test_cmd="true",
        files_changed=("src/a.py",),
    )
    suite = BenchmarkSuite(suite_id="s1", repo=str(tmp_path), tasks=(task,))

    runner = BenchmarkRunner(
        suite=suite,
        model_mode="replay",
        cassette_path="tests/fixtures/replay_smoke/cassette.json",
        workspace_root=str(tmp_path),
    )

    run = await runner.run_suite(run_id="run-123")
    assert run.run_id == "run-123"
    assert run.suite_id == "s1"
    assert len(run.results) == 1
    assert run.status == "completed"
