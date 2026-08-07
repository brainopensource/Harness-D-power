"""Evaluator conformance (TASK-019): mock and real TCB evaluator share the
tri-state B4 contract — exit 0 = PASSED, exit 1 = FAILED, everything else
(hash mismatch, missing command, any other exit code) = NONE, never FAILED."""

from __future__ import annotations

import os
import sys

import pytest
from tests.aether.mocks import FakeEvaluator

from aether.domain.gate import GateStatus
from aether.domain.ids import RunId, TaskId
from aether.domain.workspace import WorktreeRef
from aether.measurement.evaluator import RealEvaluator, hash_command
from aether.ports.evaluator import EvalSpec, Evaluator


@pytest.fixture
def worktree_dir(tmp_path):  # noqa: ANN001
    worktrees_root = tmp_path / "worktrees"
    run_id = "run-1"
    worktree_id = "wt-1"
    path = worktrees_root / run_id / worktree_id
    path.mkdir(parents=True)
    return str(worktrees_root), WorktreeRef(
        worktree_id=worktree_id, run_id=RunId(run_id), base_commit="a" * 40, abs_hint=str(path)
    )


def _spec(worktree: WorktreeRef, command: str, timeout_ms: int = 5000) -> EvalSpec:
    return EvalSpec(
        task_id=TaskId("t1"),
        worktree=worktree,
        image_digest="sha256:" + "a" * 64,
        test_command_hash=hash_command(command),
        timeout_ms=timeout_ms,
    )


@pytest.mark.parametrize("evaluator", [FakeEvaluator(), None])
async def test_evaluator_satisfies_protocol(evaluator, worktree_dir) -> None:  # noqa: ANN001
    worktrees_root, _ = worktree_dir
    instance = evaluator or RealEvaluator(worktrees_root, resolve_command=lambda spec: "true")
    assert isinstance(instance, Evaluator)


async def test_real_evaluator_exit_0_is_passed(worktree_dir) -> None:  # noqa: ANN001
    worktrees_root, worktree = worktree_dir
    command = f"{sys.executable} -c \"import sys; sys.exit(0)\""
    evaluator = RealEvaluator(worktrees_root, resolve_command=lambda spec: command)

    report = await evaluator.evaluate(_spec(worktree, command))

    assert report.status == GateStatus.PASSED
    assert report.instrument_error is None


async def test_real_evaluator_exit_1_is_failed_not_none(worktree_dir) -> None:  # noqa: ANN001
    worktrees_root, worktree = worktree_dir
    command = f"{sys.executable} -c \"import sys; sys.exit(1)\""
    evaluator = RealEvaluator(worktrees_root, resolve_command=lambda spec: command)

    report = await evaluator.evaluate(_spec(worktree, command))

    assert report.status == GateStatus.FAILED
    assert report.instrument_error is None


async def test_real_evaluator_other_exit_code_is_none_not_failed(worktree_dir) -> None:  # noqa: ANN001
    worktrees_root, worktree = worktree_dir
    command = f"{sys.executable} -c \"import sys; sys.exit(2)\""
    evaluator = RealEvaluator(worktrees_root, resolve_command=lambda spec: command)

    report = await evaluator.evaluate(_spec(worktree, command))

    assert report.status == GateStatus.NONE
    assert report.instrument_error is not None


async def test_real_evaluator_missing_command_is_none_not_failed(worktree_dir) -> None:  # noqa: ANN001
    worktrees_root, worktree = worktree_dir
    command = "definitely_not_a_real_binary_xyz"
    evaluator = RealEvaluator(worktrees_root, resolve_command=lambda spec: command)

    report = await evaluator.evaluate(_spec(worktree, command))

    assert report.status == GateStatus.NONE
    assert report.instrument_error is not None


async def test_real_evaluator_command_hash_mismatch_is_none(worktree_dir) -> None:  # noqa: ANN001
    worktrees_root, worktree = worktree_dir
    actual_command = f"{sys.executable} -c \"import sys; sys.exit(0)\""
    evaluator = RealEvaluator(worktrees_root, resolve_command=lambda spec: actual_command)

    spec = EvalSpec(
        task_id=TaskId("t1"),
        worktree=worktree,
        image_digest="sha256:" + "a" * 64,
        test_command_hash=hash_command("a completely different command"),
        timeout_ms=5000,
    )
    report = await evaluator.evaluate(spec)

    assert report.status == GateStatus.NONE
    assert "hash mismatch" in (report.instrument_error or "")


async def test_real_evaluator_timeout_is_none(worktree_dir) -> None:  # noqa: ANN001
    worktrees_root, worktree = worktree_dir
    command = f"{sys.executable} -c \"import time; time.sleep(5)\""
    evaluator = RealEvaluator(worktrees_root, resolve_command=lambda spec: command)

    report = await evaluator.evaluate(_spec(worktree, command, timeout_ms=200))

    assert report.status == GateStatus.NONE
    assert "timed out" in (report.instrument_error or "")
