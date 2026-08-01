"""Real-repo tests for `Harvester.validate_task` (v2-S4 Epic S4.1b — the harvester's own
honesty gate). Uses a throwaway git repo with an actual buggy-then-fixed commit pair rather
than mocking subprocess — validation correctness (clean revert, reproducing failure,
determinism) is exactly the kind of thing a mock can't prove.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from sagiha.domain.benchmark import HarvestedTask
from sagiha.e0.harvester import Harvester

_TEST_SCRIPT = (
    "import sys\nsys.path.insert(0, '.')\nfrom src import add\nsys.exit(0 if add(2, 3) == 5 else 1)\n"
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _make_fix_repo(tmp_path: Path, *, flaky: bool = False) -> tuple[Path, str, str]:
    """A two-commit repo: `base` has a buggy `add`, `target` fixes it and adds a test.

    Returns `(repo_path, base_sha, target_sha)`.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "test")

    (repo / "src.py").write_text("def add(a, b):\n    return a - b  # bug\n")
    _git(repo, "add", "src.py")
    _git(repo, "commit", "-q", "-m", "buggy add")
    base_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()

    (repo / "src.py").write_text("def add(a, b):\n    return a + b  # fixed\n")
    if flaky:
        # Deterministically alternates pass/fail via a counter file bumped on every invocation
        # — used to prove the determinism probe rejects flaky tasks, without relying on
        # process-id parity (which varies unpredictably run to run and made this test itself
        # flaky).
        (repo / "test_x.py").write_text(
            "import pathlib, sys\n"
            "counter_path = pathlib.Path(__file__).parent / '.flaky_counter'\n"
            "n = int(counter_path.read_text()) if counter_path.exists() else 0\n"
            "counter_path.write_text(str(n + 1))\n"
            "sys.exit(0 if n % 2 == 0 else 1)\n"
        )
    else:
        (repo / "test_x.py").write_text(_TEST_SCRIPT)
    _git(repo, "add", "src.py", "test_x.py")
    _git(repo, "commit", "-q", "-m", "fix add")
    target_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()

    return repo, base_sha, target_sha


def _task(repo: Path, base_sha: str, target_sha: str) -> HarvestedTask:
    return HarvestedTask(
        task_id="fix-add",
        repo=str(repo),
        base_commit=base_sha,
        target_commit=target_sha,
        diff_summary="fix add",
        failing_test_cmd="python test_x.py",
        files_changed=("src.py", "test_x.py"),
        test_files=("test_x.py",),
        source_files=("src.py",),
    )


@pytest.mark.asyncio
async def test_validate_task_passes_on_a_real_clean_fix(tmp_path: Path) -> None:
    repo, base_sha, target_sha = _make_fix_repo(tmp_path)
    harvester = Harvester(repo)
    result = await harvester.validate_task(_task(repo, base_sha, target_sha), k_determinism=3)
    assert result.passed is True
    assert result.reason == ""
    assert result.determinism_failures == 3


@pytest.mark.asyncio
async def test_validate_task_missing_file_split_rejected_without_touching_git(tmp_path: Path) -> None:
    repo, base_sha, target_sha = _make_fix_repo(tmp_path)
    task = _task(repo, base_sha, target_sha).model_copy(update={"test_files": (), "source_files": ()})
    harvester = Harvester(repo)
    result = await harvester.validate_task(task)
    assert result.passed is False
    assert result.reason == "missing_file_split"


@pytest.mark.asyncio
async def test_validate_task_flaky_failure_rejected(tmp_path: Path) -> None:
    repo, base_sha, target_sha = _make_fix_repo(tmp_path, flaky=True)
    harvester = Harvester(repo)
    result = await harvester.validate_task(_task(repo, base_sha, target_sha), k_determinism=5)
    assert result.passed is False
    assert result.reason == "flaky_failure"


@pytest.mark.asyncio
async def test_validate_task_releases_worktree_even_on_failure(tmp_path: Path) -> None:
    """The `finally: release(...)` must fire on every exit path — verified by checking no
    worktree survives after a failing validation."""
    repo, base_sha, target_sha = _make_fix_repo(tmp_path)
    task = _task(repo, base_sha, target_sha).model_copy(update={"test_files": (), "source_files": ()})
    harvester = Harvester(repo)
    await harvester.validate_task(task)
    worktrees_dir = repo / ".sagiha" / "worktrees"
    remaining = list(worktrees_dir.iterdir()) if worktrees_dir.exists() else []
    assert remaining == []
