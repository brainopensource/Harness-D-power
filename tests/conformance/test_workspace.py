"""Workspace/WorktreeManager conformance: the mock and the real git-CLI adapter
must behave identically against the same port contract (ADR-0005 rev. 2)."""

from __future__ import annotations

import subprocess

import pytest

from aether.adapters.workspace.git_cli import GitCliWorkspace, GitCliWorktreeManager
from aether.domain.ids import RunId
from aether.domain.workspace import WorktreeRef
from aether.ports.workspace import Workspace, WorktreeManager
from tests.aether.mocks import InMemoryWorkspace, InMemoryWorktreeManager


def _git(*args: str, cwd: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def git_repo(tmp_path):  # noqa: ANN001
    repo = tmp_path / "repo"
    repo.mkdir()
    _git("init", "-q", cwd=str(repo))
    _git("config", "user.email", "test@example.com", cwd=str(repo))
    _git("config", "user.name", "Test", cwd=str(repo))
    (repo / "hello.py").write_text("def greet():\n    return 'hi'\n")
    _git("add", ".", cwd=str(repo))
    _git("commit", "-q", "-m", "init", cwd=str(repo))
    base_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(repo), check=True, capture_output=True, text=True
    ).stdout.strip()
    return str(repo), base_commit


@pytest.mark.parametrize(
    "manager_factory",
    [InMemoryWorktreeManager, lambda: GitCliWorktreeManager("__set_by_test__", "__set_by_test__")],
)
async def test_manager_satisfies_protocol(manager_factory) -> None:  # noqa: ANN001
    assert isinstance(manager_factory(), WorktreeManager)


async def test_git_cli_worktree_lifecycle(git_repo, tmp_path) -> None:  # noqa: ANN001
    repo_path, base_commit = git_repo
    worktrees_root = str(tmp_path / "worktrees")
    manager = GitCliWorktreeManager(repo_path, worktrees_root)
    run_id = RunId("run-1")

    ref = await manager.create(run_id, base_commit)

    assert isinstance(ref, WorktreeRef)
    assert ref.run_id == run_id
    assert ref.base_commit == base_commit
    assert manager.last_create_duration_ms is not None
    active = await manager.list_active(run_id)
    assert active == (ref,)

    await manager.destroy(ref)
    assert await manager.list_active(run_id) == ()


@pytest.mark.parametrize(
    "workspace_factory",
    [InMemoryWorkspace, None],
)
async def test_workspace_satisfies_protocol(workspace_factory, tmp_path) -> None:  # noqa: ANN001
    workspace = workspace_factory() if workspace_factory else GitCliWorkspace(str(tmp_path))
    assert isinstance(workspace, Workspace)


async def test_git_cli_workspace_read_write_diff_apply_patch(git_repo, tmp_path) -> None:  # noqa: ANN001
    repo_path, base_commit = git_repo
    worktrees_root = str(tmp_path / "worktrees")
    manager = GitCliWorktreeManager(repo_path, worktrees_root)
    workspace = GitCliWorkspace(worktrees_root)
    run_id = RunId("run-1")
    ref = await manager.create(run_id, base_commit)

    slice_ = await workspace.read(ref, "hello.py")
    assert "def greet" in slice_.text

    await workspace.write(ref, "hello.py", "def greet():\n    return 'hello'\n")
    diff_text = await workspace.diff(ref)
    assert "greet" in diff_text and "hello" in diff_text

    await workspace.write(ref, "new_file.py", "x = 1\n")
    new_slice = await workspace.read(ref, "new_file.py")
    assert new_slice.text == "x = 1"


async def test_git_cli_workspace_read_line_slicing(git_repo, tmp_path) -> None:  # noqa: ANN001
    repo_path, base_commit = git_repo
    worktrees_root = str(tmp_path / "worktrees")
    manager = GitCliWorktreeManager(repo_path, worktrees_root)
    workspace = GitCliWorkspace(worktrees_root)
    ref = await manager.create(RunId("run-2"), base_commit)

    await workspace.write(ref, "multi.py", "line1\nline2\nline3\nline4\n")
    slice_ = await workspace.read(ref, "multi.py", start_line=2, end_line=3)

    assert slice_.text == "line2\nline3"
    assert slice_.start_line == 2
    assert slice_.end_line == 3


@pytest.mark.parametrize("repo_rel_path", ["/etc/passwd", "../escaped.py", "sub/../../escaped.py"])
async def test_a_path_escaping_the_worktree_is_refused(tmp_path, repo_rel_path: str) -> None:  # noqa: ANN001
    """The adapter is the boundary, so the check lives here and not in whoever
    called it. Paths crossing this boundary originate from a model, which makes
    them untrusted input by definition (ADR-0015).

    Refused, never clamped: silently rewriting the path would let a candidate
    believe it wrote where it asked.
    """
    from aether.adapters.workspace.git_cli import GitCliWorkspace, PathEscapesWorktree

    worktrees_root = tmp_path / "worktrees"
    (worktrees_root / "run-1" / "wt-1").mkdir(parents=True)
    workspace = GitCliWorkspace(str(worktrees_root))
    worktree = WorktreeRef(
        worktree_id="wt-1", run_id=RunId("run-1"), base_commit="a" * 40, abs_hint="x"
    )

    with pytest.raises(PathEscapesWorktree):
        await workspace.write(worktree, repo_rel_path, "pwned")
    with pytest.raises(PathEscapesWorktree):
        await workspace.read(worktree, repo_rel_path)


async def test_an_ordinary_nested_path_still_works(tmp_path) -> None:  # noqa: ANN001
    """The containment check must not break legitimate subdirectories."""
    from aether.adapters.workspace.git_cli import GitCliWorkspace

    worktrees_root = tmp_path / "worktrees"
    (worktrees_root / "run-1" / "wt-1").mkdir(parents=True)
    workspace = GitCliWorkspace(str(worktrees_root))
    worktree = WorktreeRef(
        worktree_id="wt-1", run_id=RunId("run-1"), base_commit="a" * 40, abs_hint="x"
    )

    await workspace.write(worktree, "src/pkg/mod.py", "X = 1\n")
    slice_ = await workspace.read(worktree, "src/pkg/mod.py")

    assert slice_.text == "X = 1"
