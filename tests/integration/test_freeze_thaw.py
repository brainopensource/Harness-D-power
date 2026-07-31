"""S3.4 proving tests — freeze → kill → thaw → identical GateReport ×3."""

from __future__ import annotations

import subprocess
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from sagiha.agency.freeze import load_freeze, persist_freeze
from sagiha.agency.run_loop import RunLoop, make_task
from sagiha.composition import build_kernel
from sagiha.domain.config import Config, ModelConfig, TelemetryConfig, WorkspaceConfig
from sagiha.domain.content import Message, ModelRequest, TextBlock, ToolUseBlock
from sagiha.domain.control import RunContext
from sagiha.domain.trajectory import Completion, StreamEvent, TokenUsage
from sagiha.domain.work import GateReport


class _Scripted:
    def __init__(self, responses: list[Message]) -> None:
        self._responses = list(responses)
        self.i = 0
        self.stable_digests: list[str] = []

    async def complete(self, request: ModelRequest) -> Completion:
        if self.i >= len(self._responses):
            return Completion(
                message=Message(role="assistant", content=[TextBlock(text="done")]),
                usage=TokenUsage(input_tokens=1, output_tokens=1),
                model="test",
            )
        msg = self._responses[self.i]
        self.i += 1
        return Completion(
            message=msg,
            usage=TokenUsage(input_tokens=5, output_tokens=3),
            model="test",
        )

    async def stream(self, request: ModelRequest) -> AsyncIterator[StreamEvent]:
        raise NotImplementedError
        yield  # pragma: no cover


def _git_init(workspace: Path) -> None:
    subprocess.run(["git", "init"], cwd=workspace, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@test"], cwd=workspace, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=workspace, check=True, capture_output=True)
    (workspace / "README.md").write_text("hello\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=workspace, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=workspace, check=True, capture_output=True)


def _responses() -> list[Message]:
    return [
        Message(
            role="assistant",
            content=[
                ToolUseBlock(
                    call_id="c1",
                    tool_name="write_file",
                    arguments={"path": "out.txt", "content": "ok"},
                )
            ],
        ),
        Message(role="assistant", content=[TextBlock(text="finished")]),
    ]


async def _run_freeze_thaw_cycle(tmp_path: Path, cycle: int) -> GateReport:
    workspace = tmp_path / f"ws{cycle}"
    workspace.mkdir()
    _git_init(workspace)
    cassette = tmp_path / f"c{cycle}.json"
    cassette.write_text("[]", encoding="utf-8")
    traj = tmp_path / f"t{cycle}.db"

    config = Config(
        model=ModelConfig(mode="replay"),
        workspace=WorkspaceConfig(root=str(workspace)),
        telemetry=TelemetryConfig(trajectory_db=str(traj)),
    )

    # --- Phase 1: start run, take one step, freeze, "kill" the process ---
    kernel1 = build_kernel(config, cassette_path=str(cassette))
    scripted1 = _Scripted(_responses())
    loop1 = RunLoop(
        model_provider=scripted1,  # type: ignore[arg-type]
        policy_engine=kernel1.policy_engine,
        resource_governor=kernel1.resource_governor,
        tool_registry=kernel1.tool_registry,
        trajectory_store=kernel1.trajectory_store,
        bus=kernel1.bus,
        max_steps=1,
        tool_schemas=list(kernel1.tool_schemas),
        evaluator=kernel1.evaluator,
        workspace=kernel1.workspace,
        pricing=kernel1.config.pricing,
        context=kernel1.config.context,
    )
    run_id = f"freeze-thaw-{cycle}"
    task = make_task("write out.txt", checks=[], task_id=run_id)
    ctx = RunContext(
        run_id=run_id,
        autonomy_level="interactive",
        workspace_root=str(workspace.resolve()),
        budget_remaining_usd=10.0,
    )
    phase1 = await loop1.run(task, ctx)
    assert len(phase1.steps) == 1

    # base_commit lives on the RunLoop's in-run ctx copy; recover HEAD for gate continuity.
    sha = await kernel1.workspace.checkpoint("freeze") if kernel1.workspace is not None else ""
    frozen = loop1.freeze(ctx.model_copy(update={"base_commit": sha}), reason="checkpoint")
    remaining = await kernel1.resource_governor.remaining_budget(run_id)
    frozen = frozen.model_copy(update={"budget_remaining_usd": remaining})
    persist_freeze(frozen)
    # "kill -9": drop loop1/kernel1; only disk state survives.
    del loop1
    del kernel1

    # --- Phase 2: new process thaws and finishes ---
    kernel2 = build_kernel(config, cassette_path=str(cassette))
    # Remaining responses: the text-only end turn (write already done in phase 1).
    scripted2 = _Scripted([Message(role="assistant", content=[TextBlock(text="finished")])])
    loop2 = RunLoop(
        model_provider=scripted2,  # type: ignore[arg-type]
        policy_engine=kernel2.policy_engine,
        resource_governor=kernel2.resource_governor,
        tool_registry=kernel2.tool_registry,
        trajectory_store=kernel2.trajectory_store,
        bus=kernel2.bus,
        max_steps=5,
        tool_schemas=list(kernel2.tool_schemas),
        evaluator=kernel2.evaluator,
        workspace=kernel2.workspace,
        pricing=kernel2.config.pricing,
        context=kernel2.config.context,
    )
    reloaded = load_freeze(str(workspace.resolve()), run_id)
    assert reloaded.reason == "checkpoint"
    phase2 = await loop2.thaw(task, reloaded)
    assert not phase2.parked
    assert (workspace / "out.txt").read_text(encoding="utf-8") == "ok"
    return phase2.gate_report


@pytest.mark.asyncio
async def test_freeze_kill_thaw_identical_gate_report_x3(tmp_path: Path) -> None:
    reports: list[GateReport] = []
    for i in range(3):
        reports.append(await _run_freeze_thaw_cycle(tmp_path, i))

    # Identical final GateReport three times (kill-9 simulation).
    assert reports[0] == reports[1] == reports[2]


@pytest.mark.asyncio
async def test_budget_park_persists_freeze(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _git_init(workspace)
    cassette = tmp_path / "c.json"
    cassette.write_text("[]", encoding="utf-8")
    traj = tmp_path / "t.db"

    from sagiha.domain.config import GovernorConfig

    config = Config(
        model=ModelConfig(mode="replay"),
        workspace=WorkspaceConfig(root=str(workspace)),
        telemetry=TelemetryConfig(trajectory_db=str(traj)),
        governor=GovernorConfig(max_spend_usd_per_run=0.0),
    )
    kernel = build_kernel(config, cassette_path=str(cassette))
    scripted = _Scripted(_responses())
    loop = RunLoop(
        model_provider=scripted,  # type: ignore[arg-type]
        policy_engine=kernel.policy_engine,
        resource_governor=kernel.resource_governor,
        tool_registry=kernel.tool_registry,
        trajectory_store=kernel.trajectory_store,
        bus=kernel.bus,
        max_steps=5,
        tool_schemas=list(kernel.tool_schemas),
        evaluator=kernel.evaluator,
        workspace=kernel.workspace,
        pricing=kernel.config.pricing,
        context=kernel.config.context,
    )
    run_id = "budget-park-1"
    task = make_task("write", checks=[], task_id=run_id)
    ctx = RunContext(
        run_id=run_id,
        autonomy_level="interactive",
        workspace_root=str(workspace.resolve()),
        budget_remaining_usd=0.0,
    )
    result = await loop.run(task, ctx)
    assert result.parked is True
    assert result.frozen is not None
    assert result.frozen.reason == "budget"
    loaded = load_freeze(str(workspace.resolve()), run_id)
    assert loaded.reason == "budget"
    record = await kernel.trajectory_store.get_run(run_id)
    assert record is not None
    assert record.status == "input-required"
