"""Unit tests for Sprint 2 Day-Zero microkernel, bus, dispatch, and SQLite trajectory store."""

from __future__ import annotations

import tempfile
from pathlib import Path

import anyio
import pytest

from sagiha import Config, build_kernel
from sagiha.adapters.model.cassette import CassetteEntry, CassetteModelProvider
from sagiha.adapters.tools.registry import DefaultToolRegistry
from sagiha.adapters.trajectory.sqlite import SQLiteTrajectoryStore
from sagiha.domain.config import ModelConfig, TelemetryConfig, WorkspaceConfig
from sagiha.domain.content import EffectClass, Message, ModelRequest, TextBlock, ToolCall, ToolResult
from sagiha.domain.control import Decision, RunContext
from sagiha.domain.events import Event, ToolCallRequested
from sagiha.kernel.bus import EventBus
from sagiha.kernel.dispatch import dispatch
from sagiha.kernel.governor import DefaultResourceGovernor
from sagiha.kernel.policy.engine import DefaultPolicyEngine
from sagiha.kernel.react import ReActEngine


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
async def test_react_engine_execution() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        cassette_path = str(Path(tmp_dir) / "cassette.json")
        entry = CassetteEntry(
            request=ModelRequest(messages=[Message(role="user", content=[TextBlock(text="hello")])]),
            response=Message(role="assistant", content=[TextBlock(text="Hello back!")]),
        )
        await anyio.Path(cassette_path).write_text(f"[{entry.model_dump_json()}]")

        model = CassetteModelProvider(cassette_path=cassette_path, mode="replay")
        policy = DefaultPolicyEngine()
        governor = DefaultResourceGovernor()
        registry = DefaultToolRegistry()

        engine = ReActEngine(model, policy, governor, registry)
        ctx = RunContext(
            run_id="r-react",
            autonomy_level="interactive",
            workspace_root="/tmp",
            budget_remaining_usd=5.0,
        )

        step_result = await engine.step(ctx, "hello")
        assert step_result.step_id.seq == 1
        assert step_result.step_id.run_id == "r-react"


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
