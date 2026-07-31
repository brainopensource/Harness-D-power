"""S2.5 proving test: freeze -> kill -> resume -> replay round-trip with a text-turn-bearing
cassette entry.

Before this sprint, `TrajectoryStep` stored only the `ToolCall`s derived from an assistant
response, not the response itself — a turn that mixed prose with a tool call lost the prose
on resume. `_reconstruct_history` rebuilt a `ToolUseBlock`-only message, which does not
digest-match the original request, so `replay --verify` against a recording made from the
live turn would raise `CassetteMismatchError` the moment any step carried accompanying text.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from sagiha.adapters.model.cassette import CassetteEntry, CassetteMismatchError, request_digest
from sagiha.adapters.trajectory.sqlite import SQLiteTrajectoryStore
from sagiha.agency.run_loop import RunLoop, make_task
from sagiha.composition import build_kernel
from sagiha.domain.config import SandboxConfig, Config, ModelConfig, TelemetryConfig, WorkspaceConfig
from sagiha.domain.content import Message, ModelRequest, TextBlock, ToolUseBlock
from sagiha.domain.control import RunContext
from sagiha.domain.trajectory import Completion, StreamEvent, TokenUsage


class _Scripted:
    def __init__(self, responses: list[Message]) -> None:
        self._responses = responses
        self.i = 0

    async def complete(self, request: ModelRequest) -> Completion:
        msg = self._responses[self.i]
        self.i += 1
        return Completion(message=msg, usage=TokenUsage(input_tokens=0, output_tokens=0), model="test")

    async def stream(self, request: ModelRequest) -> AsyncIterator[StreamEvent]:
        raise NotImplementedError
        yield  # pragma: no cover


@pytest.mark.asyncio
async def test_freeze_kill_resume_replay_preserves_text_alongside_tool_call(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    cassette_path = tmp_path / "cassette.json"
    cassette_path.write_text("[]", encoding="utf-8")
    trajectory_db = tmp_path / "traj.db"

    config = Config(
        model=ModelConfig(mode="replay"),
        workspace=WorkspaceConfig(root=str(workspace)),
        telemetry=TelemetryConfig(trajectory_db=str(trajectory_db)),
        sandbox=SandboxConfig(runtime="subprocess"),
    )

    # --- Phase 1: "freeze" — a text-turn-bearing step (prose + a tool call together),
    # then the process is "killed" (max_steps=1 caps the loop mid-flight).
    kernel1 = build_kernel(config, cassette_path=str(cassette_path))
    turn_with_text_and_tool_call = Message(
        role="assistant",
        content=[
            TextBlock(text="Checking the repo state before I act."),
            ToolUseBlock(call_id="c1", tool_name="run_command", arguments={"command": ["true"]}),
        ],
    )
    scripted1 = _Scripted([turn_with_text_and_tool_call])

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
    )
    run_id = "trajectory-completeness-1"
    task = make_task("run true", checks=[], task_id=run_id)
    ctx1 = RunContext(
        run_id=run_id, autonomy_level="interactive", workspace_root=str(workspace), budget_remaining_usd=10.0
    )
    phase1_result = await loop1.run(task, ctx1)
    assert len(phase1_result.steps) == 1

    # The full assistant turn is on the persisted step, not just the derived ToolCall.
    persisted_step = phase1_result.steps[0]
    assert persisted_step.message == turn_with_text_and_tool_call

    # --- "Kill": read back from SQLite as a fresh process would on restart, not from
    # in-process memory. The text block must survive the JSON round trip.
    store = SQLiteTrajectoryStore(db_path=str(trajectory_db))
    reloaded_steps = await store.steps_for_run(run_id)
    assert len(reloaded_steps) == 1
    assert reloaded_steps[0].message is not None
    assert any(isinstance(b, TextBlock) for b in reloaded_steps[0].message.content)
    assert reloaded_steps[0].message == turn_with_text_and_tool_call

    # --- Phase 2: what the resumed request looks like, reconstructed from the reloaded
    # (not in-memory) steps. If reconstruction dropped the TextBlock, this digest would
    # not match a recording made from the real prior turn.
    from sagiha.agency.context.assembler import ContextAssembler

    loop2 = RunLoop(
        model_provider=scripted1,  # unused for digest computation
        policy_engine=kernel1.policy_engine,
        resource_governor=kernel1.resource_governor,
        tool_registry=kernel1.tool_registry,
        trajectory_store=kernel1.trajectory_store,
        bus=kernel1.bus,
        tool_schemas=list(kernel1.tool_schemas),
        evaluator=kernel1.evaluator,
        context=kernel1.config.context,
    )
    assembler = ContextAssembler.from_trajectory(
        system_prompt=loop2._system_prompt,
        tool_schemas=tuple(kernel1.tool_schemas),
        task=task,
        steps=reloaded_steps,
        config=kernel1.config.context,
    )
    assembled = await assembler.assemble(role="execution")
    assistant_messages = [m for m in assembled.request.messages if m.role == "assistant"]
    assert len(assistant_messages) == 1
    assert assistant_messages[0] == turn_with_text_and_tool_call

    resumed_request = assembled.request
    end_turn = Message(role="assistant", content=[TextBlock(text="All done.")])
    entries = [
        CassetteEntry(
            request=resumed_request, response=end_turn, digest=request_digest(resumed_request)
        ).model_dump(mode="json")
    ]
    cassette_path.write_text(json.dumps(entries), encoding="utf-8")

    # --- "Resume": build a fresh kernel/loop against the recorded cassette (replay mode) —
    # equivalent to `sagiha replay --verify` after a restart. A digest mismatch here raises
    # CassetteMismatchError, which is exactly the failure mode this test guards against.
    kernel2 = build_kernel(config, cassette_path=str(cassette_path))
    loop3 = RunLoop(
        model_provider=kernel2.model_provider,
        policy_engine=kernel2.policy_engine,
        resource_governor=kernel2.resource_governor,
        tool_registry=kernel2.tool_registry,
        trajectory_store=kernel2.trajectory_store,
        bus=kernel2.bus,
        max_steps=5,
        tool_schemas=list(kernel2.tool_schemas),
        evaluator=kernel2.evaluator,
    )
    try:
        resumed_result = await loop3.run(task, ctx1, resume=True)
    except CassetteMismatchError as exc:
        pytest.fail(f"replay verify FAILED — resumed history lost the text-turn: {exc}")

    assert resumed_result.gate_report is not None
    # step 1 folded back in; step 2 is the RC-4-persisted text-only end_turn
    assert len(resumed_result.steps) == 2

    final_record = await store.get_run(run_id)
    assert final_record is not None
    assert final_record.status == "completed"
