"""D16/D17 (Sprint 3b): single ToolCallRequested instance, observer timeout + quarantine,
anyio-backed EventBus."""

from __future__ import annotations

import anyio
import pytest

from sagiha.adapters.tools.registry import DefaultToolRegistry
from sagiha.domain.content import EffectClass, TextBlock, ToolCall, ToolResult
from sagiha.domain.control import Decision, RunContext
from sagiha.domain.events import Event, ToolCallRequested
from sagiha.kernel.bus import EventBus
from sagiha.kernel.dispatch import dispatch
from sagiha.kernel.governor import DefaultResourceGovernor
from sagiha.kernel.policy.engine import DefaultPolicyEngine


@pytest.mark.asyncio
async def test_dispatch_emits_and_intercepts_the_same_requested_instance() -> None:
    """D16: the object handed to emit() and the object handed to intercept() must be the same
    instance, so an audit trail correlating by identity/timestamp cannot diverge."""
    seen: dict[str, ToolCallRequested] = {}

    async def observer(evt: Event) -> None:
        if isinstance(evt, ToolCallRequested):
            seen["emitted"] = evt

    async def interceptor(evt: Event) -> Decision:
        assert isinstance(evt, ToolCallRequested)
        seen["intercepted"] = evt
        return Decision(allowed=True, reason="ok")

    policy = DefaultPolicyEngine()
    governor = DefaultResourceGovernor()
    registry = DefaultToolRegistry()

    async def handler(args: dict[str, object]) -> ToolResult:
        return ToolResult(call_id="c1", content=[TextBlock(text="ok")])

    registry.register_handler("echo", {"type": "object"}, EffectClass.PURE, handler)
    policy.register_tool_schema("echo", {"type": "object"})

    bus = EventBus()
    bus.subscribe_observer(observer)
    bus.subscribe_interceptor("pre_tool", interceptor)

    ctx = RunContext(
        run_id="r1", autonomy_level="interactive", workspace_root="/tmp", budget_remaining_usd=10.0
    )
    call = ToolCall(call_id="c1", tool_name="echo", arguments={}, effect=EffectClass.PURE)
    await dispatch(call, ctx, policy, governor, registry, bus)

    assert seen["emitted"] is seen["intercepted"]


@pytest.mark.asyncio
async def test_observer_that_raises_is_quarantined_for_the_rest_of_the_run() -> None:
    calls = 0

    async def flaky_observer(evt: Event) -> None:
        nonlocal calls
        calls += 1
        raise RuntimeError("boom")

    bus = EventBus()
    bus.subscribe_observer(flaky_observer)

    call = ToolCall(call_id="c1", tool_name="t", arguments={}, effect=EffectClass.PURE)
    evt = ToolCallRequested(run_id="r1", call=call)

    await bus.emit(evt)
    await bus.emit(evt)
    await bus.emit(evt)

    assert calls == 1


@pytest.mark.asyncio
async def test_observer_that_hangs_past_timeout_is_quarantined() -> None:
    calls = 0

    async def hanging_observer(evt: Event) -> None:
        nonlocal calls
        calls += 1
        await anyio.sleep(10)

    bus = EventBus(observer_timeout_s=0.01)
    bus.subscribe_observer(hanging_observer)

    call = ToolCall(call_id="c1", tool_name="t", arguments={}, effect=EffectClass.PURE)
    evt = ToolCallRequested(run_id="r1", call=call)

    await bus.emit(evt)
    await bus.emit(evt)

    assert calls == 1


@pytest.mark.asyncio
async def test_one_broken_observer_does_not_block_a_healthy_one() -> None:
    healthy_received: list[Event] = []

    async def broken(evt: Event) -> None:
        raise RuntimeError("boom")

    async def healthy(evt: Event) -> None:
        healthy_received.append(evt)

    bus = EventBus()
    bus.subscribe_observer(broken)
    bus.subscribe_observer(healthy)

    call = ToolCall(call_id="c1", tool_name="t", arguments={}, effect=EffectClass.PURE)
    evt = ToolCallRequested(run_id="r1", call=call)
    await bus.emit(evt)

    assert len(healthy_received) == 1


@pytest.mark.asyncio
async def test_interceptor_timeout_fails_closed() -> None:
    async def hanging_interceptor(evt: Event) -> Decision:
        await anyio.sleep(10)
        return Decision(allowed=True, reason="never gets here")

    bus = EventBus(default_timeout_s=0.01)
    bus.subscribe_interceptor("pre_tool", hanging_interceptor)

    call = ToolCall(call_id="c1", tool_name="t", arguments={}, effect=EffectClass.PURE)
    evt = ToolCallRequested(run_id="r1", call=call)
    decision = await bus.intercept("pre_tool", evt)

    assert not decision.allowed
    assert "timed out" in decision.reason.lower()
