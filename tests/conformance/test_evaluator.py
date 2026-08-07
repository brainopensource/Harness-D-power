"""Evaluator conformance (TASK-019): mock and real TCB evaluator share the
tri-state B4 contract — exit 0 = PASSED, exit 1 = FAILED, everything else
(hash mismatch, missing command, any other exit code) = NONE, never FAILED."""

from __future__ import annotations

import sys

import pytest

from aether.domain.gate import GateStatus
from aether.domain.ids import RunId, TaskId
from aether.domain.sandbox import ContainerResult, ContainerSpec
from aether.domain.workspace import WorktreeRef
from aether.measurement.evaluator import RealEvaluator, hash_command
from aether.ports.evaluator import EvalSpec, Evaluator
from tests.aether.mocks import FakeEvaluator


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


# --- Contained mode (TASK-016). The B3 container's own canary lives in
# tests/integration/test_b3_canary.py and needs a real runtime; these prove the
# *mapping* is identical on the contained path, with no runtime required. ---


class _StubSandbox:
    """Structurally a `SandboxRunner`; records the spec it was handed."""

    def __init__(self, result: ContainerResult) -> None:
        self._result = result
        self.seen: ContainerSpec | None = None

    async def run(self, spec: ContainerSpec) -> ContainerResult:
        self.seen = spec
        return self._result


async def test_uncontained_evaluator_reports_that_it_is_not_contained(worktree_dir) -> None:  # noqa: ANN001
    """The floor runner reads this: a number taken on an uncontained
    instrument is not publishable (measurement.md §2 B3)."""
    worktrees_root, _ = worktree_dir
    assert RealEvaluator(worktrees_root, resolve_command=lambda spec: "true").is_contained is False


async def test_contained_evaluator_maps_exit_codes_the_same_way(worktree_dir) -> None:  # noqa: ANN001
    worktrees_root, worktree = worktree_dir
    for exit_code, expected in ((0, GateStatus.PASSED), (1, GateStatus.FAILED), (2, GateStatus.NONE)):
        sandbox = _StubSandbox(ContainerResult(exit_code=exit_code, stdout="out"))
        evaluator = RealEvaluator(worktrees_root, resolve_command=lambda spec: "true", sandbox=sandbox)
        report = await evaluator.evaluate(_spec(worktree, "true"))
        assert report.status == expected
        assert evaluator.is_contained is True


async def test_a_container_that_never_started_is_none_not_failed(worktree_dir) -> None:  # noqa: ANN001
    """B3 x B4: an instrument that could not run is not a test result."""
    worktrees_root, worktree = worktree_dir
    sandbox = _StubSandbox(ContainerResult(launch_error="podman not on PATH"))
    evaluator = RealEvaluator(worktrees_root, resolve_command=lambda spec: "true", sandbox=sandbox)

    report = await evaluator.evaluate(_spec(worktree, "true"))

    assert report.status == GateStatus.NONE
    assert "container did not start" in (report.instrument_error or "")


async def test_contained_timeout_is_none(worktree_dir) -> None:  # noqa: ANN001
    worktrees_root, worktree = worktree_dir
    sandbox = _StubSandbox(ContainerResult(timed_out=True))
    evaluator = RealEvaluator(worktrees_root, resolve_command=lambda spec: "true", sandbox=sandbox)

    report = await evaluator.evaluate(_spec(worktree, "true"))

    assert report.status == GateStatus.NONE
    assert "timed out" in (report.instrument_error or "")


async def test_the_image_digest_from_the_manifest_reaches_the_container_spec(worktree_dir) -> None:  # noqa: ANN001
    """The manifest pins the environment; the container is created from that
    digest, never from a tag."""
    worktrees_root, worktree = worktree_dir
    sandbox = _StubSandbox(ContainerResult(exit_code=0))
    evaluator = RealEvaluator(worktrees_root, resolve_command=lambda spec: "true", sandbox=sandbox)

    await evaluator.evaluate(_spec(worktree, "true"))

    assert sandbox.seen is not None
    assert sandbox.seen.image_digest == "sha256:" + "a" * 64
    assert sandbox.seen.worktree_host_path.endswith("run-1/wt-1")


async def test_a_second_evaluation_sees_the_new_candidate_not_a_stale_cache(worktree_dir) -> None:  # noqa: ANN001
    """B3's failure mode in miniature, and the one the repair edge exposed.

    CPython invalidates a cached `.pyc` on (mtime seconds, source size). A
    repair iteration that flips one character inside the same second satisfies
    both, so a stale bytecode cache would make the second evaluation score the
    *first* candidate's code. A gate that cannot see the diff it is scoring is
    the exact defect B3 names.
    """
    worktrees_root, worktree = worktree_dir
    from pathlib import Path

    path = Path(worktrees_root) / worktree.run_id / worktree.worktree_id
    (path / "calc.py").write_text("def add(a, b):\n    return a - b\n")
    (path / "run_tests.py").write_text(
        "import sys\nfrom calc import add\nsys.exit(0 if add(1, 2) == 3 else 1)\n"
    )
    command = f"{sys.executable} run_tests.py"
    evaluator = RealEvaluator(worktrees_root, resolve_command=lambda spec: command)

    first = await evaluator.evaluate(_spec(worktree, command))
    # Same length, same second — the two conditions CPython's cache check uses.
    (path / "calc.py").write_text("def add(a, b):\n    return a + b\n")
    second = await evaluator.evaluate(_spec(worktree, command))

    assert first.status == GateStatus.FAILED
    assert second.status == GateStatus.PASSED, "the evaluator scored a stale copy of the candidate"
    assert not (path / "__pycache__").exists()
