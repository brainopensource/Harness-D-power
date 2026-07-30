"""D9: resumable run state — seq derived from TrajectoryStore, not engine memory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from sagiha.adapters.tools.registry import DefaultToolRegistry
from sagiha.adapters.trajectory.sqlite import SQLiteTrajectoryStore
from sagiha.agency.run_loop import RunLoop, make_task
from sagiha.domain.content import EffectClass, Message, ModelRequest, TextBlock, ToolResult, ToolUseBlock
from sagiha.domain.control import RunContext
from sagiha.domain.trajectory import StreamEvent
from sagiha.kernel.bus import EventBus
from sagiha.kernel.governor import DefaultResourceGovernor
from sagiha.kernel.policy.engine import DefaultPolicyEngine


def _ctx(run_id: str) -> RunContext:
    return RunContext(
        run_id=run_id, autonomy_level="interactive", workspace_root="/tmp", budget_remaining_usd=10.0
    )


class _ScriptedProvider:
    def __init__(self, responses: list[Message]) -> None:
        self._responses = responses
        self.i = 0
        self.seen_message_counts: list[int] = []

    async def complete(self, request: ModelRequest) -> Message:
        self.seen_message_counts.append(len(request.messages))
        msg = self._responses[min(self.i, len(self._responses) - 1)]
        self.i += 1
        return msg

    async def stream(self, request: ModelRequest) -> AsyncIterator[StreamEvent]:
        raise NotImplementedError
        yield  # pragma: no cover


def _make_registry() -> DefaultToolRegistry:
    registry = DefaultToolRegistry()

    async def handler(args: dict[str, object]) -> ToolResult:
        return ToolResult(call_id="c", content=[TextBlock(text="ok")])

    registry.register_handler("echo", {"type": "object"}, EffectClass.PURE, handler)
    return registry


@pytest.mark.asyncio
async def test_resume_continues_seq_without_collision(tmp_path: Path) -> None:
    store = SQLiteTrajectoryStore(db_path=str(tmp_path / "traj.db"))
    policy = DefaultPolicyEngine()
    policy.register_tool_schema("echo", {"type": "object"})
    governor = DefaultResourceGovernor()
    registry = _make_registry()
    ctx = _ctx("resume-1")
    task = make_task("do the thing", checks=[], task_id=ctx.run_id)

    # First run: two steps of tool_use, then interrupted mid-flight by capping max_steps at 2
    # (simulating a process restart before the model ended the turn).
    first_provider = _ScriptedProvider(
        [
            Message(
                role="assistant",
                content=[ToolUseBlock(call_id="a", tool_name="echo", arguments={"msg": "1"})],
            ),
            Message(
                role="assistant",
                content=[ToolUseBlock(call_id="b", tool_name="echo", arguments={"msg": "2"})],
            ),
        ]
    )
    first_loop = RunLoop(
        model_provider=first_provider,  # type: ignore[arg-type]
        policy_engine=policy,
        resource_governor=governor,
        tool_registry=registry,
        trajectory_store=store,
        bus=EventBus(),
        max_steps=2,
    )
    first_result = await first_loop.run(task, ctx)
    assert len(first_result.steps) == 2
    assert [s.step_id.seq for s in first_result.steps] == [1, 2]

    run_record = await store.get_run(ctx.run_id)
    assert run_record is not None
    # Exhausting the per-invocation max_steps budget without a stuck/budget signal is not
    # itself a failure — task success is what GateReport.admitted decides separately.
    assert run_record.status == "completed"

    # Resume: a fresh RunLoop/provider, simulating a new process. It must pick up at seq=3,
    # not restart from seq=1 (which would collide on the steps table's primary key).
    second_provider = _ScriptedProvider([Message(role="assistant", content=[TextBlock(text="done")])])
    second_loop = RunLoop(
        model_provider=second_provider,  # type: ignore[arg-type]
        policy_engine=policy,
        resource_governor=governor,
        tool_registry=registry,
        trajectory_store=store,
        bus=EventBus(),
        max_steps=5,
    )
    resumed_result = await second_loop.run(task, ctx, resume=True)

    # No collision: append_step would have raised sqlite3.IntegrityError on a duplicate
    # (run_id, branch_id, seq) primary key, which it did not.
    all_steps = await store.steps_for_run(ctx.run_id)
    assert [s.step_id.seq for s in all_steps] == [1, 2]  # step 3 ended the turn with no tool call

    # Prior steps are folded back into the result.
    assert len(resumed_result.steps) == 2
    assert resumed_result.steps[0].step_id.seq == 1

    # The model on resume saw the reconstructed history (goal + 2 prior tool round-trips), not
    # a blank slate.
    assert second_provider.seen_message_counts[0] == 5  # goal + 2*(assistant + tool_result)

    final_record = await store.get_run(ctx.run_id)
    assert final_record is not None
    assert final_record.status == "completed"
