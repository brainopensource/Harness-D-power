"""Composition root wiring (Step 7): the real adapters must be reachable
through Dispatcher.dispatch(), not just unit-testable in isolation."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime

import pytest

from aether.adapters.model_provider.openai_compatible import OpenAICompatibleProvider
from aether.adapters.tools.builtin import BuiltinToolRegistry
from aether.adapters.workspace.git_cli import GitCliWorkspace, GitCliWorktreeManager
from aether.composition import ReadArgs, build_dispatcher
from aether.domain.budget import BudgetDims
from aether.domain.ids import RunId, SpanId
from aether.domain.taint import Provenance, TaintSpan
from aether.domain.workspace import FileSlice
from aether.kernel.governor import ResourceGovernor
from aether.measurement.evaluator import RealEvaluator
from aether.ports.policy_engine import EffectRequest


def _git(*args: str, cwd: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def wired(tmp_path):  # noqa: ANN001
    repo = tmp_path / "repo"
    repo.mkdir()
    _git("init", "-q", cwd=str(repo))
    _git("config", "user.email", "test@example.com", cwd=str(repo))
    _git("config", "user.name", "Test", cwd=str(repo))
    (repo / "hello.py").write_text("print('hi')\n")
    _git("add", ".", cwd=str(repo))
    _git("commit", "-q", "-m", "init", cwd=str(repo))
    base_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(repo), check=True, capture_output=True, text=True
    ).stdout.strip()

    worktrees_root = str(tmp_path / "worktrees")
    workspace = GitCliWorkspace(worktrees_root)
    worktree_manager = GitCliWorktreeManager(str(repo), worktrees_root)
    tool_registry = BuiltinToolRegistry(workspace, worktrees_root)
    model_provider = OpenAICompatibleProvider("http://localhost:11434/v1", "test-model")
    evaluator = RealEvaluator(worktrees_root, resolve_command=lambda spec: "true")
    governor = ResourceGovernor()
    dispatcher = build_dispatcher(workspace, tool_registry, model_provider, evaluator, governor)

    return dispatcher, worktree_manager, base_commit, governor


async def test_dispatched_read_effect_reaches_the_real_workspace_adapter(wired) -> None:  # noqa: ANN001
    dispatcher, worktree_manager, base_commit, governor = wired
    run_id = RunId("run-1")
    worktree = await worktree_manager.create(run_id, base_commit)

    span = TaintSpan(
        span_id=SpanId("s1"), label=Provenance.AGENT, text="x", source="test", created_at=datetime.now(UTC)
    )
    args = ReadArgs(worktree=worktree, repo_rel_path="hello.py")
    request = EffectRequest(
        run_id=run_id,
        effect_class="read",
        descriptor=args.model_dump_json(),
        justifying_spans=(span,),
        widens_capability=False,
    )

    outcome = await dispatcher.dispatch(request, cost_estimate=BudgetDims())

    assert outcome.status == "ok"
    assert outcome.result_json is not None
    file_slice = FileSlice.model_validate_json(outcome.result_json)
    assert "print" in file_slice.text
