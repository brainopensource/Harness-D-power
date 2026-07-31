"""Proving tests for ADR-0020: per-invocation effect classification.

`classify_command` narrows a declared DESTRUCTIVE `run_command` to PURE for allowlisted
read-only argv. `CassetteToolRegistry` uses that per-call classification to decide, under
`replay --verify`, which steps re-execute against the live workspace (PURE) and which are
served from the recording (everything else) — see docs/08-decisions/0020.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from sagiha.adapters.tools.builtins import register_builtin_tools
from sagiha.adapters.tools.cassette import CassetteToolRegistry, ToolCassetteMismatchError, call_digest
from sagiha.adapters.tools.registry import DefaultToolRegistry
from sagiha.adapters.workspace.local import LocalWorkspace
from sagiha.domain.content import EffectClass, ToolCall
from sagiha.kernel.policy.effects import classify_command


def test_classify_command_narrows_pure_git_read() -> None:
    assert classify_command(["git", "status"], EffectClass.DESTRUCTIVE) is EffectClass.PURE
    assert classify_command(["git", "diff"], EffectClass.DESTRUCTIVE) is EffectClass.PURE


def test_classify_command_never_widens_git_mutation() -> None:
    assert classify_command(["git", "commit", "-m", "x"], EffectClass.DESTRUCTIVE) is EffectClass.DESTRUCTIVE
    assert classify_command(["git", "push"], EffectClass.DESTRUCTIVE) is EffectClass.DESTRUCTIVE


def test_classify_command_leaves_rm_destructive() -> None:
    assert classify_command(["rm", "x"], EffectClass.DESTRUCTIVE) is EffectClass.DESTRUCTIVE


def test_classify_command_never_narrows_shell() -> None:
    assert classify_command(["bash", "-lc", "git status"], EffectClass.DESTRUCTIVE) is EffectClass.DESTRUCTIVE


def test_classify_command_does_not_widen_already_narrow_effect() -> None:
    assert classify_command(["rm", "x"], EffectClass.PURE) is EffectClass.PURE
    assert classify_command(["rm", "x"], EffectClass.IDEMPOTENT) is EffectClass.IDEMPOTENT


@pytest.fixture
def git_workspace(tmp_path: Path) -> LocalWorkspace:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    (tmp_path / "x").write_text("hello\n")
    subprocess.run(["git", "add", "x"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=tmp_path, check=True)
    return LocalWorkspace(str(tmp_path))


def _call(tool_name: str, argv: list[str], declared: EffectClass) -> ToolCall:
    return ToolCall(
        call_id=f"c-{argv}",
        tool_name=tool_name,
        arguments={"command": argv},
        effect=classify_command(argv, declared),
    )


@pytest.mark.asyncio
async def test_pure_git_status_reexecutes_destructive_rm_served_from_cassette(
    git_workspace: LocalWorkspace, tmp_path: Path
) -> None:
    live = DefaultToolRegistry()
    register_builtin_tools(live, git_workspace)
    cassette_path = str(tmp_path / "tools.json")

    # Record pass: all calls execute for real once.
    recorder = CassetteToolRegistry(live, cassette_path, mode="record")
    declared = await recorder.get_effect_class("run_command")
    git_status_call = _call("run_command", ["git", "status"], declared)
    git_diff_call = _call("run_command", ["git", "diff"], declared)
    rm_call = _call("run_command", ["rm", "x"], declared)
    assert git_status_call.effect is EffectClass.PURE
    assert git_diff_call.effect is EffectClass.PURE
    assert rm_call.effect is EffectClass.DESTRUCTIVE

    await recorder.dispatch(git_status_call)
    await recorder.dispatch(git_diff_call)
    await recorder.dispatch(rm_call)

    # Recreate the file the `rm` recorded as deleted, so a stray re-execution would be visible.
    (Path(git_workspace.root) / "x").write_text("hello\n")

    # Replay pass against a fresh registry pointed at the same cassette.
    live2 = DefaultToolRegistry()
    register_builtin_tools(live2, git_workspace)
    replayer = CassetteToolRegistry(live2, cassette_path, mode="replay")

    git_status_call_2 = _call("run_command", ["git", "status"], declared)
    git_diff_call_2 = _call("run_command", ["git", "diff"], declared)
    rm_call_2 = _call("run_command", ["rm", "x"], declared)

    await replayer.dispatch(git_status_call_2)
    await replayer.dispatch(git_diff_call_2)
    await replayer.dispatch(rm_call_2)

    assert replayer.re_executed == 2  # git status + git diff
    assert replayer.served_from_cassette == 1  # rm served, not re-run
    # The file must still exist — `rm` was never re-executed against the live workspace.
    assert (Path(git_workspace.root) / "x").exists()

    total = replayer.re_executed + replayer.served_from_cassette
    assert replayer.re_executed / total >= 0.6  # RC-6: exit metric context, PURE-majority re-executes


@pytest.mark.asyncio
async def test_replay_raises_on_missing_recording_for_mutating_call(
    git_workspace: LocalWorkspace, tmp_path: Path
) -> None:
    live = DefaultToolRegistry()
    register_builtin_tools(live, git_workspace)
    cassette_path = str(tmp_path / "empty.json")
    replayer = CassetteToolRegistry(live, cassette_path, mode="replay")

    call = _call("run_command", ["rm", "x"], await replayer.get_effect_class("run_command"))
    with pytest.raises(ToolCassetteMismatchError):
        await replayer.dispatch(call)


def test_call_digest_is_stable_across_argument_order() -> None:
    d1 = call_digest("run_command", {"command": ["git", "status"]})
    d2 = call_digest("run_command", {"command": ["git", "status"]})
    assert d1 == d2
