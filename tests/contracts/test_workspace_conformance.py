"""Workspace port conformance — parametrized over LocalWorkspace and ContainerSandbox.

The hexagon's payoff test (v2-S5 / ADR-0006): both adapters honour the same Workspace
contract. Container cases require rootless Podman and the `sagiha/runtime:latest` image.
"""

from __future__ import annotations

import subprocess
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from sagiha.adapters.sandbox.container import ContainerSandbox
from sagiha.adapters.workspace.local import LocalWorkspace
from sagiha.domain.config import SandboxConfig
from sagiha.domain.work import Edit, EditRequest
from sagiha.ports.workspace import Workspace
from tests.podman_support import RUNTIME_IMAGE, require_podman

pytestmark = pytest.mark.asyncio

_RUNTIME_IMAGE = RUNTIME_IMAGE


def _init_git_repo(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "conformance@test"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "conformance"], cwd=root, check=True)
    (root / "README.md").write_text("hello\n", encoding="utf-8")
    (root / "mod.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=root, check=True)


@pytest.fixture
def git_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _init_git_repo(root)
    return root


@pytest.fixture(params=["local", pytest.param("container", marks=pytest.mark.podman)])
async def workspace(request: pytest.FixtureRequest, git_root: Path) -> AsyncIterator[Workspace]:
    kind = request.param
    if kind == "local":
        yield LocalWorkspace(str(git_root))
        return

    require_podman()

    sandbox = ContainerSandbox(
        str(git_root),
        SandboxConfig(
            runtime="container",
            image=_RUNTIME_IMAGE,
            network="none",
            memory_limit_mb=512,
            cpu_limit=1.0,
        ),
        state_dir=str(git_root / ".sagiha" / "sandbox"),
    )
    await sandbox.start()
    try:
        yield sandbox
    finally:
        await sandbox.aclose()


async def test_read_write_round_trip(workspace: Workspace) -> None:
    await workspace.write("note.txt", "alpha\n")
    assert await workspace.read("note.txt") == "alpha\n"
    assert "alpha" in await workspace.read("note.txt", offset=0, limit=1)


async def test_apply_edit_success(workspace: Workspace) -> None:
    result = await workspace.apply_edit(
        EditRequest(path="mod.py", edits=(Edit(old_string="x = 1", new_string="x = 2"),))
    )
    assert result.syntax_valid is True
    assert all(h.applied for h in result.hunks)
    assert "x = 2" in await workspace.read("mod.py")


async def test_apply_edit_syntax_refusal_leaves_disk_unchanged(workspace: Workspace) -> None:
    before = await workspace.read("mod.py")
    result = await workspace.apply_edit(
        EditRequest(
            path="mod.py",
            edits=(Edit(old_string="x = 1", new_string="def broken(:\n"),),
        )
    )
    assert result.syntax_valid is False
    assert await workspace.read("mod.py") == before


async def test_run_echo(workspace: Workspace) -> None:
    result = await workspace.run(["echo", "perimeter-ok"])
    assert result.exit_code == 0
    assert "perimeter-ok" in result.stdout


async def test_run_argv_list(workspace: Workspace) -> None:
    result = await workspace.run(["python", "-c", "print(2 + 2)"])
    assert result.exit_code == 0
    assert "4" in result.stdout


async def test_checkpoint_and_restore(workspace: Workspace) -> None:
    sha = await workspace.checkpoint("pre")
    assert len(sha) >= 7
    await workspace.write("tracked.txt", "scratch\n")
    # Stage+commit so restore has something to rewind — or just check HEAD stable.
    head = await workspace.run(["git", "rev-parse", "HEAD"])
    assert head.stdout.strip() == sha
    await workspace.restore(sha)
    after = await workspace.run(["git", "rev-parse", "HEAD"])
    assert after.stdout.strip() == sha


async def test_path_escape_refused(workspace: Workspace) -> None:
    with pytest.raises(PermissionError, match="escapes"):
        await workspace.read("../outside.txt")
