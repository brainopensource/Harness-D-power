"""The validity canary against a real repository (TASK-014).

`tests/aether/measurement/test_manifest.py` pins the *policy* with a scripted
instrument. This module pins the *instrument*: a real git repo, a real
worktree at a real base commit, a real gold patch applied by the real
`Workspace` adapter, and the real `RealEvaluator` running a real test command.
A canary screened on a different instrument than the benchmark later runs on
is a canary for something else.

Uses the uncontained evaluator so the suite runs anywhere; the contained path
is the same code with a `sandbox` injected (see tests/integration/test_b3_canary.py).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from aether.measurement.evaluator import RealEvaluator
from aether.measurement.manifest import (
    ExclusionReason,
    TaskCandidate,
    build_manifest,
    manifest_hash,
    screen_all,
    screen_candidate,
)
from aether.measurement.validity import WorktreeValidityInstrument

DIGEST = "sha256:" + "e" * 64

BROKEN_CALC = "def add(a, b):\n    return a - b\n"
FIXED_CALC = "def add(a, b):\n    return a + b\n"
RUN_TESTS = "import sys\nfrom calc import add\nsys.exit(0 if add(1, 2) == 3 else 1)\n"


def _git(*args: str, cwd: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout


@pytest.fixture
def upstream(tmp_path: Path):  # noqa: ANN201
    """A repo whose tests fail at HEAD, plus the gold patch that fixes them —
    the shape of every SWE-bench-style task."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git("init", "-q", cwd=str(repo))
    _git("config", "user.email", "test@example.com", cwd=str(repo))
    _git("config", "user.name", "Test", cwd=str(repo))
    (repo / "calc.py").write_text(BROKEN_CALC)
    (repo / "run_tests.py").write_text(RUN_TESTS)
    _git("add", ".", cwd=str(repo))
    _git("commit", "-q", "-m", "task base", cwd=str(repo))
    base_commit = _git("rev-parse", "HEAD", cwd=str(repo)).strip()

    (repo / "calc.py").write_text(FIXED_CALC)
    gold_patch = _git("diff", cwd=str(repo))
    _git("checkout", "--", "calc.py", cwd=str(repo))

    return str(repo), base_commit, gold_patch


@pytest.fixture
def instrument(upstream, tmp_path: Path):  # noqa: ANN001, ANN201
    repo_path, _base, _patch = upstream
    test_command = f"{sys.executable} run_tests.py"
    evaluator = RealEvaluator(
        str(tmp_path / "worktrees"), resolve_command=lambda spec: test_command
    )
    return (
        WorktreeValidityInstrument(repo_path, str(tmp_path / "worktrees"), evaluator),
        test_command,
    )


def _candidate(upstream, test_command: str, **overrides: object) -> TaskCandidate:  # noqa: ANN001
    _repo, base_commit, gold_patch = upstream
    base: dict[str, object] = {
        "instance_id": "local__calc-1",
        "repo": "local/calc",
        "base_commit": base_commit,
        "environment_image_digest": DIGEST,
        "test_command": test_command,
        "gold_patch": gold_patch,
        "split": "dev",
    }
    base.update(overrides)
    return TaskCandidate(**base)  # type: ignore[arg-type]


async def test_a_real_task_is_admitted_when_gold_passes_and_empty_fails(upstream, instrument) -> None:  # noqa: ANN001
    canary, test_command = instrument

    verdict = await screen_candidate(_candidate(upstream, test_command), canary)

    assert verdict.admitted is True, verdict.detail
    assert verdict.gold_status.value == "passed"
    assert verdict.empty_status.value == "failed"


async def test_a_task_whose_gold_patch_does_not_fix_it_is_excluded(upstream, instrument) -> None:  # noqa: ANN001
    """A no-op gold patch is the commonest shape of a broken upstream task."""
    canary, test_command = instrument
    candidate = _candidate(upstream, test_command, gold_patch="")

    verdict = await screen_candidate(candidate, canary)

    assert verdict.admitted is False
    assert verdict.reason is ExclusionReason.GOLD_PATCH_FAILS


async def test_an_unresolvable_base_commit_is_an_instrument_error_not_a_task_failure(  # noqa: ANN001
    upstream, instrument
) -> None:
    """B1's failure mode — `fatal: invalid reference` — is what produced the
    2026-08-01 non-run. It must never be recorded as "this task fails"."""
    canary, test_command = instrument
    candidate = _candidate(upstream, test_command, base_commit="0" * 40)

    verdict = await screen_candidate(candidate, canary)

    assert verdict.admitted is False
    assert verdict.reason is ExclusionReason.INSTRUMENT_ERROR


async def test_a_pinned_manifest_is_built_from_real_verdicts(upstream, instrument) -> None:  # noqa: ANN001
    canary, test_command = instrument
    candidates = [
        _candidate(upstream, test_command, instance_id="good-1"),
        _candidate(upstream, test_command, instance_id="broken-1", gold_patch=""),
    ]

    verdicts = await screen_all(candidates, canary)
    manifest = build_manifest(
        manifest_id="local-calc-01",
        suite="internal",
        candidates=candidates,
        verdicts=verdicts,
        instrument_contained=canary.is_contained,
    )

    assert [t["instance_id"] for t in manifest["tasks"]] == ["good-1"]
    assert manifest["validity_gate"]["exclusions"][0]["instance_id"] == "broken-1"
    assert manifest["validity_gate"]["instrument"]["contained"] is False
    assert manifest_hash(manifest).startswith("sha256:")
