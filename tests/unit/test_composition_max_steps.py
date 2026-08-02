"""`KernelCandidateExecutor.execute` must source `RunLoop.max_steps` from
`config.governor.max_steps_per_run`, not `RunLoop`'s own independently-defaulted 20 — the
step-budget reconciliation `planning_final_sprint_rev2.md` correction 2 describes: before this
fix, every Best-of-N candidate silently ran with a 20-step ceiling regardless of what
`GovernorConfig.max_steps_per_run` (default 200) said.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

from sagiha.adapters.workspace.worktree import GitWorktreeManager
from sagiha.agency import run_loop as run_loop_module
from sagiha.composition import KernelCandidateExecutor
from sagiha.domain.config import Config, GovernorConfig, ModelConfig, SandboxConfig, WorkspaceConfig
from sagiha.domain.work import TaskSpec


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=repo, check=True)
    (repo / "a.txt").write_text("x")
    subprocess.run(["git", "add", "a.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True)
    return repo


@pytest.mark.asyncio
async def test_candidate_executor_wires_governor_max_steps_into_run_loop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _init_repo(tmp_path)
    cassette = tmp_path / "cassette.json"
    cassette.write_text("[]")

    config = Config(
        model=ModelConfig(mode="replay"),
        workspace=WorkspaceConfig(root=str(repo)),
        sandbox=SandboxConfig(runtime="subprocess"),
        governor=GovernorConfig(max_steps_per_run=137),  # distinctive, not the RunLoop default of 20
    )
    manager = GitWorktreeManager(str(repo))
    executor = KernelCandidateExecutor(
        parent_config=config, cassette_path=str(cassette), worktree_manager=manager
    )

    captured: dict[str, Any] = {}
    real_init = run_loop_module.RunLoop.__init__

    def _spy_init(self: object, *args: object, **kwargs: object) -> None:
        captured["max_steps"] = kwargs.get("max_steps")
        real_init(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(run_loop_module.RunLoop, "__init__", _spy_init)

    task = TaskSpec(task_id="t1", goal="noop", acceptance=(), profile="coding")
    ctx_run_id = "candidate-max-steps-test"
    from sagiha.domain.control import RunContext

    context = RunContext(
        run_id=ctx_run_id,
        autonomy_level="interactive",
        workspace_root=str(repo),
        budget_remaining_usd=5.0,
    )

    # Only the constructor call matters here — it fires before any model call, so a cassette
    # mismatch downstream (this test supplies no recorded entries) does not affect the assertion.
    with pytest.raises(Exception):  # noqa: B017 - CassetteMismatchError, deliberately untyped here
        await executor.execute(task, context, branch_id="b1", base_commit="HEAD")

    assert captured["max_steps"] == 137
