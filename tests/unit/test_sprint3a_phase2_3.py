"""Phase 2–3: grant verification, path scoping, ToolUseBlock parsing, typed events."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import timedelta
from pathlib import Path

import pytest

from sagiha.adapters.tools.registry import DefaultToolRegistry
from sagiha.adapters.trajectory.sqlite import SQLiteTrajectoryStore
from sagiha.agency.run_loop import RunLoop, make_task
from sagiha.domain.content import (
    EffectClass,
    Message,
    ModelRequest,
    TextBlock,
    ToolCall,
    ToolResult,
    ToolUseBlock,
)
from sagiha.domain.control import Grant, RunContext
from sagiha.domain.events import ToolCallCompleted, ToolCallRequested
from sagiha.domain.identity import utc_now
from sagiha.domain.trajectory import StreamEvent
from sagiha.kernel.bus import EventBus
from sagiha.kernel.dispatch import dispatch
from sagiha.kernel.governor import DefaultResourceGovernor
from sagiha.kernel.policy.engine import DefaultPolicyEngine


@pytest.mark.asyncio
async def test_dispatch_rejects_expired_grant(monkeypatch: pytest.MonkeyPatch) -> None:
    policy = DefaultPolicyEngine()
    governor = DefaultResourceGovernor()
    registry = DefaultToolRegistry()

    async def handler(args: dict[str, object]) -> ToolResult:
        return ToolResult(call_id="c1", content=[TextBlock(text="should-not-run")])

    registry.register_handler("echo", {"type": "object"}, EffectClass.PURE, handler)
    policy.register_tool_schema("echo", {"type": "object"})

    # Force authorize to mint an already-expired grant.
    original = policy.authorize

    async def authorize_expired(call: ToolCall, context: RunContext):
        decision = await original(call, context)
        assert decision.grant_id is not None
        grant = policy._active_grants[decision.grant_id]
        policy._active_grants[decision.grant_id] = Grant(
            grant_id=grant.grant_id,
            tool_name=grant.tool_name,
            scope_paths=grant.scope_paths,
            run_id=grant.run_id,
            issued_at=grant.issued_at,
            expires_at=utc_now() - timedelta(seconds=1),
        )
        return decision

    monkeypatch.setattr(policy, "authorize", authorize_expired)

    ctx = RunContext(
        run_id="r1",
        autonomy_level="interactive",
        workspace_root="/tmp",
        budget_remaining_usd=10.0,
    )
    call = ToolCall(call_id="c1", tool_name="echo", arguments={}, effect=EffectClass.PURE)
    result = await dispatch(call, ctx, policy, governor, registry)
    assert result.is_error is True
    assert "expired" in result.content[0].text.lower() or "missing" in result.content[0].text.lower()  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_policy_extracts_nested_edit_request_path() -> None:
    schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "x-sagiha-path": True},
            "request": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "x-sagiha-path": True},
                },
            },
        },
    }
    policy = DefaultPolicyEngine()
    policy.register_tool_schema("apply_edit", schema)

    ctx = RunContext(
        run_id="r1",
        autonomy_level="interactive",
        workspace_root="/tmp",
        budget_remaining_usd=10.0,
    )
    call = ToolCall(
        call_id="c1",
        tool_name="apply_edit",
        arguments={"request": {"path": "src/foo.py", "edits": []}},
        effect=EffectClass.IDEMPOTENT,
    )
    decision = await policy.authorize(call, ctx)
    assert decision.allowed
    assert decision.grant_id is not None
    grant = policy.get_grant(decision.grant_id)
    assert grant is not None
    assert "src/foo.py" in grant.scope_paths


@pytest.mark.asyncio
async def test_react_parses_tool_use_block(tmp_path: Path) -> None:
    """ToolUseBlock -> ToolCall resolution + dispatch now lives in RunLoop (R1
    superseded kernel/react.py's ReActEngine, which duplicated this path)."""

    class ScriptedProvider:
        def __init__(self) -> None:
            self.calls = 0

        async def complete(self, request: ModelRequest) -> Message:
            self.calls += 1
            if self.calls == 1:
                return Message(
                    role="assistant",
                    content=[ToolUseBlock(call_id="tu-1", tool_name="echo", arguments={"msg": "hi"})],
                )
            return Message(role="assistant", content=[TextBlock(text="done")])

        async def stream(self, request: ModelRequest) -> AsyncIterator[StreamEvent]:
            raise NotImplementedError
            yield  # pragma: no cover

    model = ScriptedProvider()
    policy = DefaultPolicyEngine()
    governor = DefaultResourceGovernor()
    registry = DefaultToolRegistry()

    async def handler(args: dict[str, object]) -> ToolResult:
        return ToolResult(call_id="tu-1", content=[TextBlock(text=f"got {args.get('msg')}")])

    registry.register_handler("echo", {"type": "object"}, EffectClass.PURE, handler)
    policy.register_tool_schema("echo", {"type": "object"})

    store = SQLiteTrajectoryStore(db_path=str(tmp_path / "traj.db"))
    loop = RunLoop(
        model_provider=model,  # type: ignore[arg-type]
        policy_engine=policy,
        resource_governor=governor,
        tool_registry=registry,
        trajectory_store=store,
        bus=EventBus(),
    )
    ctx = RunContext(
        run_id="r-react",
        autonomy_level="interactive",
        workspace_root="/tmp",
        budget_remaining_usd=5.0,
    )
    result = await loop.run(make_task("edit", checks=[]), ctx)
    assert len(result.steps) == 1
    step = result.steps[0]
    assert len(step.tool_calls) == 1
    assert step.tool_calls[0].tool_name == "echo"
    assert step.tool_calls[0].effect == EffectClass.PURE
    assert len(step.tool_results) == 1
    assert not step.tool_results[0].is_error


@pytest.mark.asyncio
async def test_sqlite_round_trips_subclass_payload(tmp_path: Path) -> None:
    store = SQLiteTrajectoryStore(db_path=str(tmp_path / "t.db"))
    call = ToolCall(call_id="c9", tool_name="echo", arguments={}, effect=EffectClass.PURE)
    evt = ToolCallRequested(run_id="run-x", call=call)
    await store.append_event(evt)
    events = await store.events_for_run("run-x")
    assert len(events) == 1
    assert isinstance(events[0], ToolCallRequested)
    assert events[0].call.call_id == "c9"

    completed = ToolCallCompleted(
        run_id="run-x",
        call_id="c9",
        result=ToolResult(call_id="c9", content=[TextBlock(text="ok")]),
        duration_ms=1.5,
    )
    await store.append_event(completed)
    events2 = await store.events_for_run("run-x")
    assert isinstance(events2[1], ToolCallCompleted)
    assert events2[1].call_id == "c9"
    assert events2[1].result.content[0].text == "ok"  # type: ignore[union-attr]
