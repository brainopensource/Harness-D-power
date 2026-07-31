"""Unit tests for Sprint 2 Day-Zero microkernel, bus, dispatch, and SQLite trajectory store."""

from __future__ import annotations

import tempfile
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from sagiha import Config, build_kernel
from sagiha.adapters.tools.registry import DefaultToolRegistry
from sagiha.adapters.trajectory.sqlite import SQLiteTrajectoryStore
from sagiha.agency.run_loop import RunLoop, make_task
from sagiha.domain.config import ModelConfig, TelemetryConfig, WorkspaceConfig
from sagiha.domain.content import EffectClass, Message, ModelRequest, TextBlock, ToolCall, ToolResult
from sagiha.domain.control import Decision, RunContext
from sagiha.domain.events import Event, ToolCallRequested
from sagiha.domain.trajectory import Completion, StreamEvent, TokenUsage
from sagiha.kernel.bus import EventBus
from sagiha.kernel.dispatch import dispatch
from sagiha.kernel.governor import DefaultResourceGovernor
from sagiha.kernel.policy.engine import DefaultPolicyEngine


@pytest.mark.asyncio
async def test_event_bus_observer_and_interceptor() -> None:
    bus = EventBus()
    received_events: list[Event] = []

    async def my_observer(evt: Event) -> None:
        received_events.append(evt)

    bus.subscribe_observer(my_observer)

    call = ToolCall(
        call_id="c-1",
        tool_name="test_tool",
        arguments={},
        effect=EffectClass.PURE,
    )
    evt = ToolCallRequested(run_id="run-1", call=call)
    await bus.emit(evt)

    assert len(received_events) == 1
    assert received_events[0].run_id == "run-1"

    async def my_interceptor(e: Event) -> Decision:
        return Decision(allowed=False, reason="Denied by test interceptor")

    bus.subscribe_interceptor("pre_tool", my_interceptor)
    decision = await bus.intercept("pre_tool", evt)
    assert not decision.allowed
    assert "Denied by test" in decision.reason


@pytest.mark.asyncio
async def test_sqlite_trajectory_store() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = str(Path(tmp_dir) / "trajectories.db")
        store = SQLiteTrajectoryStore(db_path=db_path)

        evt = Event(event="test.event", run_id="run-100")
        await store.append_event(evt)

        events = await store.events_for_run("run-100")
        assert len(events) == 1
        assert events[0].event == "test.event"


@pytest.mark.asyncio
async def test_dispatch_capability_choke_point() -> None:
    policy = DefaultPolicyEngine()
    governor = DefaultResourceGovernor()
    registry = DefaultToolRegistry()

    async def dummy_handler(args: dict[str, object]) -> ToolResult:
        return ToolResult(call_id="c1", content=[TextBlock(text="Success")], truncated=False)

    registry.register_handler(
        "echo",
        {"type": "object"},
        EffectClass.PURE,
        dummy_handler,
    )
    policy.register_tool_schema("echo", {"type": "object"})

    ctx = RunContext(
        run_id="r-1",
        autonomy_level="interactive",
        workspace_root="/tmp",
        budget_remaining_usd=10.0,
    )

    call = ToolCall(
        call_id="c1",
        tool_name="echo",
        arguments={"msg": "hello"},
        effect=EffectClass.PURE,
    )
    result = await dispatch(call, ctx, policy, governor, registry)

    assert not result.truncated
    assert isinstance(result.content[0], TextBlock)
    assert result.content[0].text == "Success"


@pytest.mark.asyncio
async def test_run_loop_single_step_ends_turn_with_no_tool_calls() -> None:
    """RunLoop supersedes kernel/react.py (R1): a step that ends the turn with no
    tool calls records exactly one step and stops without dispatching anything."""

    class EndTurnProvider:
        async def complete(self, request: ModelRequest) -> Completion:
            return Completion(
                message=Message(role="assistant", content=[TextBlock(text="Hello back!")]),
                usage=TokenUsage(input_tokens=0, output_tokens=0),
                model="test",
            )

        async def stream(self, request: ModelRequest) -> AsyncIterator[StreamEvent]:
            raise NotImplementedError
            yield  # pragma: no cover

    with tempfile.TemporaryDirectory() as tmp_dir:
        store = SQLiteTrajectoryStore(db_path=str(Path(tmp_dir) / "traj.db"))
        loop = RunLoop(
            model_provider=EndTurnProvider(),
            policy_engine=DefaultPolicyEngine(),
            resource_governor=DefaultResourceGovernor(),
            tool_registry=DefaultToolRegistry(),
            trajectory_store=store,
            bus=EventBus(),
        )
        ctx = RunContext(
            run_id="r-react",
            autonomy_level="interactive",
            workspace_root="/tmp",
            budget_remaining_usd=5.0,
        )

        result = await loop.run(make_task("hello", checks=[]), ctx)
        # RC-4: a text-only end_turn is persisted — it is part of what happened.
        assert len(result.steps) == 1
        assert result.steps[0].message is not None
        assert result.run_id == "r-react"


@pytest.mark.asyncio
async def test_build_kernel_wires_day_zero_adapters() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        cassette = Path(tmp_dir) / "c.json"
        cassette.write_text("[]")
        config = Config(
            model=ModelConfig(mode="replay"),
            telemetry=TelemetryConfig(trajectory_db=str(Path(tmp_dir) / "test_traj.db")),
            workspace=WorkspaceConfig(root=tmp_dir),
        )

        kernel = build_kernel(config, cassette_path=str(cassette))
        assert kernel.trajectory_store is not None
        assert kernel.policy_engine is not None
        assert kernel.resource_governor is not None
        assert kernel.tool_registry is not None
        assert kernel.memory is not None
        assert kernel.evaluator is not None


def test_kernel_mandatory_ports_are_not_optional() -> None:
    """D14: model_provider, policy_engine, resource_governor, tool_registry, and
    trajectory_store are non-optional constructor arguments — a partially wired Kernel is not
    representable. Profile-optional ports (evaluator, indexer, code_graph, lsp_adapter,
    worktree_manager) may still default to None."""
    import dataclasses

    from sagiha.composition import Kernel

    mandatory_no_default = {
        "config",
        "model_provider",
        "policy_engine",
        "resource_governor",
        "tool_registry",
        "trajectory_store",
        "memory",
        "workspace",
    }
    profile_optional = {"indexer", "code_graph", "lsp_adapter", "worktree_manager", "evaluator"}

    for f in dataclasses.fields(Kernel):
        if f.name in mandatory_no_default:
            assert f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING, (
                f"{f.name} must have no default — a partially wired Kernel must fail at composition"
            )
        elif f.name in profile_optional:
            assert f.default is None, f"{f.name} is expected to default to None"

    with pytest.raises(TypeError):
        Kernel(config=None)  # type: ignore[call-arg,arg-type]
