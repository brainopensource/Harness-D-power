"""Sprint 3b deny-path security tests (U1/D8), beyond 3a's grant-expiry coverage:

1. A tool in `always_gate` is refused with `requires_human=True` and emits `ToolCallDenied`.
2. Interceptor denial and interceptor timeout both block execution (fail-closed).
"""

from __future__ import annotations

import anyio
import pytest

from sagiha.adapters.tools.registry import DefaultToolRegistry
from sagiha.domain.content import EffectClass, TextBlock, ToolCall, ToolResult
from sagiha.domain.control import Decision, RunContext
from sagiha.domain.events import Event, ToolCallDenied
from sagiha.kernel.bus import EventBus
from sagiha.kernel.dispatch import dispatch
from sagiha.kernel.governor import DefaultResourceGovernor
from sagiha.kernel.policy.engine import DefaultPolicyEngine


def _ctx() -> RunContext:
    return RunContext(
        run_id="r1", autonomy_level="interactive", workspace_root="/tmp", budget_remaining_usd=10.0
    )


def _registry_with_echo() -> tuple[DefaultToolRegistry, list[str]]:
    invoked: list[str] = []
    registry = DefaultToolRegistry()

    async def handler(args: dict[str, object]) -> ToolResult:
        invoked.append("called")
        return ToolResult(call_id="c1", content=[TextBlock(text="ok")])

    registry.register_handler("echo", {"type": "object"}, EffectClass.PURE, handler)
    return registry, invoked


@pytest.mark.asyncio
async def test_always_gate_tool_is_denied_with_requires_human() -> None:
    policy = DefaultPolicyEngine(always_gate=["echo"])
    policy.register_tool_schema("echo", {"type": "object"})
    governor = DefaultResourceGovernor()
    registry, invoked = _registry_with_echo()
    bus = EventBus()
    denied_events: list[ToolCallDenied] = []

    async def observer(evt: Event) -> None:
        if isinstance(evt, ToolCallDenied):
            denied_events.append(evt)

    bus.subscribe_observer(observer)

    call = ToolCall(call_id="c1", tool_name="echo", arguments={}, effect=EffectClass.PURE)
    result = await dispatch(call, _ctx(), policy, governor, registry, bus)

    assert result.is_error is True
    assert invoked == []  # handler never runs — denial happens before the choke point's effect
    assert len(denied_events) == 1
    assert denied_events[0].requires_human is True


@pytest.mark.asyncio
async def test_interceptor_denial_blocks_execution() -> None:
    policy = DefaultPolicyEngine()
    policy.register_tool_schema("echo", {"type": "object"})
    governor = DefaultResourceGovernor()
    registry, invoked = _registry_with_echo()
    bus = EventBus()
    denied_events: list[ToolCallDenied] = []

    async def observer(evt: Event) -> None:
        if isinstance(evt, ToolCallDenied):
            denied_events.append(evt)

    async def deny_interceptor(evt: Event) -> Decision:
        return Decision(allowed=False, reason="org policy forbids this tool")

    bus.subscribe_observer(observer)
    bus.subscribe_interceptor("pre_tool", deny_interceptor)

    call = ToolCall(call_id="c1", tool_name="echo", arguments={}, effect=EffectClass.PURE)
    result = await dispatch(call, _ctx(), policy, governor, registry, bus)

    assert result.is_error is True
    assert invoked == []
    assert len(denied_events) == 1
    assert "org policy forbids" in denied_events[0].reason


@pytest.mark.asyncio
async def test_interceptor_timeout_blocks_execution_fail_closed() -> None:
    policy = DefaultPolicyEngine()
    policy.register_tool_schema("echo", {"type": "object"})
    governor = DefaultResourceGovernor()
    registry, invoked = _registry_with_echo()
    bus = EventBus(default_timeout_s=0.01)
    denied_events: list[ToolCallDenied] = []

    async def observer(evt: Event) -> None:
        if isinstance(evt, ToolCallDenied):
            denied_events.append(evt)

    async def hanging_interceptor(evt: Event) -> Decision:
        await anyio.sleep(10)
        return Decision(allowed=True, reason="never reached")

    bus.subscribe_observer(observer)
    bus.subscribe_interceptor("pre_tool", hanging_interceptor)

    call = ToolCall(call_id="c1", tool_name="echo", arguments={}, effect=EffectClass.PURE)
    result = await dispatch(call, _ctx(), policy, governor, registry, bus)

    assert result.is_error is True
    assert invoked == []
    assert len(denied_events) == 1
    assert "timed out" in denied_events[0].reason.lower()
