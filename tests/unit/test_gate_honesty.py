"""H1 proving tests: the coding gates are real git checks, not literals.

Before PR-1a, `GateEvaluator.evaluate` returned `no_new_suppressions=True,
tests_unmodified=True, coverage_not_decreased=True, diff_within_bounds=True`
unconditionally. Every one of these tests passes trivially against that code, which
is the point: they are written to fail against it and to hold afterwards.

`tests_unmodified` is the gate the T3 evaluation-capture threat model rests on and the
one `Config` refuses to let you disable. A run that edits its own tests must not admit.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from sagiha.composition import build_kernel
from sagiha.domain.config import Config, GatesConfig, ModelConfig, TelemetryConfig, WorkspaceConfig
from sagiha.domain.control import RunContext
from sagiha.domain.work import GateReport
from sagiha.outer_loop.evaluator.gate_evaluator import GateEvaluator


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()


def _init_repo(repo: Path) -> str:
    """A git repo with one commit. Returns the base sha."""
    repo.mkdir(parents=True, exist_ok=True)
    (repo / "tests").mkdir()
    (repo / "mod.py").write_text("VALUE = 1\n", encoding="utf-8")
    (repo / "tests" / "test_mod.py").write_text(
        "from mod import VALUE\n\n\ndef test_value():\n    assert VALUE == 1\n", encoding="utf-8"
    )
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    return _git(repo, "rev-parse", "HEAD")


def _evaluator(repo: Path, gates: GatesConfig | None = None) -> GateEvaluator:
    gates = gates or GatesConfig()
    config = Config(
        model=ModelConfig(mode="replay"),
        workspace=WorkspaceConfig(root=str(repo)),
        telemetry=TelemetryConfig(trajectory_db=str(repo / ".traj.db")),
        gates=gates,
    )
    # The gates never call the model; replay mode just needs a cassette to exist.
    cassette = repo / "cassette.json"
    cassette.write_text("[]", encoding="utf-8")
    kernel = build_kernel(config, cassette_path=str(cassette))
    return GateEvaluator(
        policy_engine=kernel.policy_engine,
        resource_governor=kernel.resource_governor,
        tool_registry=kernel.tool_registry,
        bus=kernel.bus,
        max_diff_lines=gates.max_diff_lines,
        require_coverage_not_decreased=gates.require_coverage_not_decreased,
    )


def _ctx(repo: Path, base: str) -> RunContext:
    return RunContext(
        run_id="gate-honesty",
        autonomy_level="interactive",
        workspace_root=str(repo),
        budget_remaining_usd=5.0,
        base_commit=base,
    )


def _task(task_id: str = "t"):
    from sagiha.agency.run_loop import make_task

    # A criterion that always passes, so acceptance never masks a gate failure.
    return make_task("goal", checks=["true"], task_id=task_id)


@pytest.mark.asyncio
async def test_editing_tests_fails_tests_unmodified_and_blocks_admission(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    base = _init_repo(repo)

    # The agent edits its own grader — the T3 threat, verbatim.
    (repo / "tests" / "test_mod.py").write_text("def test_value():\n    assert True\n", encoding="utf-8")

    report = await _evaluator(repo).evaluate(_task(), _ctx(repo, base))

    assert report.tests_unmodified is False
    assert report.admitted is False, "a run that rewrote its own tests must never admit"


@pytest.mark.asyncio
async def test_untouched_tests_pass_tests_unmodified(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    base = _init_repo(repo)
    (repo / "mod.py").write_text("VALUE = 2\n", encoding="utf-8")  # source only

    report = await _evaluator(repo).evaluate(_task(), _ctx(repo, base))

    assert report.tests_unmodified is True
    assert report.admitted is True


@pytest.mark.asyncio
async def test_adding_a_new_test_file_fails_tests_unmodified(tmp_path: Path) -> None:
    """Creating a test is evaluation capture just as much as editing one.

    `git diff` ignores untracked files, so without an intent-to-add stage this passes
    while the agent has planted its own grader.
    """
    repo = tmp_path / "repo"
    base = _init_repo(repo)
    (repo / "tests" / "test_planted.py").write_text("def test_ok(): assert True\n", encoding="utf-8")

    report = await _evaluator(repo).evaluate(_task(), _ctx(repo, base))

    assert report.tests_unmodified is False
    assert report.admitted is False


@pytest.mark.asyncio
async def test_oversized_diff_fails_diff_within_bounds(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    base = _init_repo(repo)
    (repo / "big.py").write_text("x = 1\n" * 50, encoding="utf-8")

    gates = GatesConfig(max_diff_lines=10)
    report = await _evaluator(repo, gates).evaluate(_task(), _ctx(repo, base))

    assert report.diff_within_bounds is False
    assert report.admitted is False


@pytest.mark.asyncio
async def test_small_diff_passes_diff_within_bounds(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    base = _init_repo(repo)
    (repo / "mod.py").write_text("VALUE = 2\n", encoding="utf-8")

    report = await _evaluator(repo, GatesConfig(max_diff_lines=10)).evaluate(_task(), _ctx(repo, base))

    assert report.diff_within_bounds is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "suppression",
    [
        "x = 1  # type: ignore",
        "y = 2  # noqa",
        "z = 3  # pragma: no cover",
        "@pytest.mark.skip\ndef test_x(): ...",
    ],
)
async def test_added_suppression_fails_no_new_suppressions(tmp_path: Path, suppression: str) -> None:
    repo = tmp_path / "repo"
    base = _init_repo(repo)
    (repo / "mod.py").write_text(f"VALUE = 1\n{suppression}\n", encoding="utf-8")

    report = await _evaluator(repo).evaluate(_task(), _ctx(repo, base))

    assert report.no_new_suppressions is False
    assert report.admitted is False


@pytest.mark.asyncio
async def test_preexisting_suppression_is_not_a_new_one(tmp_path: Path) -> None:
    """Only ADDED lines are scanned. A suppression already in the base is not the run's fault."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "tests").mkdir()
    (repo / "mod.py").write_text("VALUE = 1  # type: ignore\n", encoding="utf-8")
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    base = _git(repo, "rev-parse", "HEAD")

    # Touch an unrelated line; the pre-existing ignore stays put.
    (repo / "mod.py").write_text("VALUE = 1  # type: ignore\nOTHER = 2\n", encoding="utf-8")

    report = await _evaluator(repo).evaluate(_task(), _ctx(repo, base))

    assert report.no_new_suppressions is True


@pytest.mark.asyncio
async def test_coverage_gate_is_honest_none_not_fabricated_true(tmp_path: Path) -> None:
    """There is no Toolchain adapter and no baseline, so the honest answer is None."""
    repo = tmp_path / "repo"
    base = _init_repo(repo)

    report = await _evaluator(repo).evaluate(_task(), _ctx(repo, base))

    assert report.coverage_not_decreased is None
    # None must not block admission when the gate is not required...
    assert report.admitted is True


@pytest.mark.asyncio
async def test_required_coverage_gate_refuses_to_admit_on_none(tmp_path: Path) -> None:
    """...but if the config requires it, an unevaluable gate must fail closed."""
    repo = tmp_path / "repo"
    base = _init_repo(repo)

    gates = GatesConfig(require_coverage_not_decreased=True)
    report = await _evaluator(repo, gates).evaluate(_task(), _ctx(repo, base))

    assert report.coverage_not_decreased is None
    assert report.admitted is False


@pytest.mark.asyncio
async def test_absent_base_commit_fails_closed(tmp_path: Path) -> None:
    """No base ref means the gates cannot be evaluated. They must not report success."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    ctx = RunContext(
        run_id="no-base",
        autonomy_level="interactive",
        workspace_root=str(repo),
        budget_remaining_usd=5.0,
    )
    report = await _evaluator(repo).evaluate(_task(), ctx)

    assert report.tests_unmodified is not True
    assert report.diff_within_bounds is not True
    assert report.no_new_suppressions is not True
    assert report.admitted is False


def test_required_gates_drives_admission_not_hardcoded_field_names() -> None:
    """`admitted` computes over the evaluable set so an honest None can coexist with it."""
    report = GateReport(
        criteria=(),
        tests_unmodified=True,
        diff_within_bounds=True,
        no_new_suppressions=True,
        coverage_not_decreased=None,
        required_gates=frozenset({"tests_unmodified", "diff_within_bounds", "no_new_suppressions"}),
    )
    assert report.admitted is True

    # Widening the required set to include the unevaluable gate flips admission.
    stricter = report.model_copy(
        update={"required_gates": report.required_gates | {"coverage_not_decreased"}}
    )
    assert stricter.admitted is False
