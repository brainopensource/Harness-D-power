"""Tool input schema validation (D13) and the unknown-tool deny path (C.16)."""

from __future__ import annotations

from sagiha.adapters.tools.registry import DefaultToolRegistry, validate_arguments
from sagiha.domain.content import EffectClass, TextBlock, ToolCall, ToolResult
from sagiha.domain.control import RunContext
from sagiha.domain.events import ToolCallFailed
from sagiha.kernel.bus import EventBus
from sagiha.kernel.dispatch import dispatch
from sagiha.kernel.governor import DefaultResourceGovernor
from sagiha.kernel.policy.engine import DefaultPolicyEngine

# --- validate_arguments -------------------------------------------------

READ_LIKE_SCHEMA = {
    "type": "object",
    "properties": {
        "path": {"type": "string"},
        "offset": {"type": "integer"},
    },
    "required": ["path"],
}

COMMAND_SCHEMA = {
    "type": "object",
    "properties": {
        "command": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["command"],
}


def test_validate_arguments_accepts_conforming_input() -> None:
    assert validate_arguments(READ_LIKE_SCHEMA, {"path": "a.py"}) == []


def test_validate_arguments_flags_missing_required_field() -> None:
    errors = validate_arguments(READ_LIKE_SCHEMA, {"offset": 3})
    assert any("missing required field 'path'" in e for e in errors)


def test_validate_arguments_flags_wrong_type() -> None:
    errors = validate_arguments(READ_LIKE_SCHEMA, {"path": 123})
    assert any("must be string" in e for e in errors)


def test_validate_arguments_rejects_bool_as_integer() -> None:
    """`isinstance(True, int)` is True in Python — a bool must not pass as an integer."""
    errors = validate_arguments(READ_LIKE_SCHEMA, {"path": "a.py", "offset": True})
    assert any("must be integer, got bool" in e for e in errors)


def test_validate_arguments_checks_array_item_types() -> None:
    errors = validate_arguments(COMMAND_SCHEMA, {"command": ["ls", 7]})
    assert any("command[1]" in e and "must be string" in e for e in errors)


def test_validate_arguments_ignores_unknown_properties() -> None:
    """Extra keys the schema doesn't declare are not this validator's job to police."""
    assert validate_arguments(READ_LIKE_SCHEMA, {"path": "a.py", "extra": "x"}) == []


# --- registry.dispatch: validation runs before the handler --------------


async def test_dispatch_rejects_invalid_arguments_without_invoking_handler() -> None:
    registry = DefaultToolRegistry()
    invoked = False

    async def handler(args: dict[str, object]) -> ToolResult:
        nonlocal invoked
        invoked = True
        return ToolResult(call_id="", content=[TextBlock(text="ran")], truncated=False)

    registry.register_handler("read_file", READ_LIKE_SCHEMA, EffectClass.PURE, handler)

    result = await registry.dispatch(
        ToolCall(call_id="c1", tool_name="read_file", arguments={}, effect=EffectClass.PURE)
    )

    assert result.is_error is True
    assert "missing required field 'path'" in result.content[0].text  # type: ignore[union-attr]
    assert invoked is False


async def test_dispatch_invokes_handler_when_arguments_are_valid() -> None:
    registry = DefaultToolRegistry()

    async def handler(args: dict[str, object]) -> ToolResult:
        return ToolResult(call_id="", content=[TextBlock(text="ran")], truncated=False)

    registry.register_handler("read_file", READ_LIKE_SCHEMA, EffectClass.PURE, handler)

    result = await registry.dispatch(
        ToolCall(
            call_id="c1",
            tool_name="read_file",
            arguments={"path": "a.py"},
            effect=EffectClass.PURE,
        )
    )

    assert result.is_error is False


# --- unknown-tool deny path (C.16) --------------------------------------


async def test_dispatch_unknown_tool_returns_error_result() -> None:
    registry = DefaultToolRegistry()

    result = await registry.dispatch(
        ToolCall(call_id="c1", tool_name="does_not_exist", arguments={}, effect=EffectClass.PURE)
    )

    assert result.is_error is True
    assert "Unknown tool" in result.content[0].text  # type: ignore[union-attr]


async def test_dispatch_unknown_tool_reaches_registry_and_emits_failed() -> None:
    """C.16, full path through `kernel.dispatch`: policy authorizes the call (a schema is
    registered, so R3's fail-closed rule does not fire), but no handler exists in the
    `ToolRegistry` — the registry's own "Unknown tool" branch runs, `dispatch` sees
    `is_error=True`, and emits `ToolCallFailed`, not `ToolCallCompleted`.

    (A tool with no *schema* is a different, already-covered case — that is denied at
    authorization with `ToolCallDenied`, per R3, before it ever reaches the registry.)
    """
    policy = DefaultPolicyEngine()
    policy.register_tool_schema("ghost_tool", {"type": "object"})
    governor = DefaultResourceGovernor()
    registry = DefaultToolRegistry()  # no handler registered for "ghost_tool"
    bus = EventBus()
    failed_events: list[ToolCallFailed] = []
    bus.subscribe_observer(
        lambda event: failed_events.append(event) if isinstance(event, ToolCallFailed) else None
    )

    ctx = RunContext(
        run_id="r1",
        autonomy_level="interactive",
        workspace_root="/tmp",
        budget_remaining_usd=10.0,
    )
    call = ToolCall(call_id="c1", tool_name="ghost_tool", arguments={}, effect=EffectClass.PURE)
    result = await dispatch(call, ctx, policy, governor, registry, bus)

    assert result.is_error is True
    assert "Unknown tool" in result.content[0].text  # type: ignore[union-attr]
    assert len(failed_events) == 1
    assert failed_events[0].call_id == "c1"
