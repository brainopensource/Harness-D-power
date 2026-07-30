"""Capability security dispatch choke point — see docs/02-architecture/car-model.md."""

from __future__ import annotations

import logging
import time

from sagiha.domain.content import TextBlock, ToolCall, ToolResult
from sagiha.domain.control import RunContext
from sagiha.domain.events import (
    ToolCallAuthorized,
    ToolCallCompleted,
    ToolCallDenied,
    ToolCallFailed,
    ToolCallRequested,
)
from sagiha.kernel.bus import EventBus
from sagiha.ports.governor import ResourceGovernor
from sagiha.ports.policy import PolicyEngine
from sagiha.ports.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


async def dispatch(
    call: ToolCall,
    ctx: RunContext,
    policy: PolicyEngine,
    governor: ResourceGovernor,
    registry: ToolRegistry,
    bus: EventBus | None = None,
) -> ToolResult:
    """Sole choke point routing tool execution from Agency intent to Runtime effect.

    Authorization, capability grant minting, lease acquisition, and outcome recording
    are enforced here. Agency code has zero direct access to runtime adapters.
    """
    start_time = time.monotonic()

    requested = ToolCallRequested(run_id=ctx.run_id, call=call)
    if bus is not None:
        await bus.emit(requested)

        intercept_decision = await bus.intercept("pre_tool", requested)
        if not intercept_decision.allowed:
            await bus.emit(
                ToolCallDenied(
                    run_id=ctx.run_id,
                    decision=intercept_decision,
                    reason=intercept_decision.reason,
                    requires_human=intercept_decision.requires_human,
                )
            )
            return ToolResult(
                call_id=call.call_id,
                content=[
                    TextBlock(
                        text=f"Pre-tool interceptor denial: {intercept_decision.reason}"
                    )
                ],
                truncated=False,
                is_error=True,
            )

    decision = await policy.authorize(call, ctx)
    if not decision.allowed or decision.grant_id is None:
        if bus is not None:
            await bus.emit(
                ToolCallDenied(
                    run_id=ctx.run_id,
                    decision=decision,
                    reason=decision.reason,
                    requires_human=decision.requires_human,
                )
            )
        return ToolResult(
            call_id=call.call_id,
            content=[TextBlock(text=f"Policy denial: {decision.reason}")],
            truncated=False,
            is_error=True,
        )

    # Point-of-effect grant verification (C1 / D8) — expiry and forged ids fail closed.
    get_grant = getattr(policy, "get_grant", None)
    if callable(get_grant):
        grant = get_grant(decision.grant_id)
        if grant is None:
            if bus is not None:
                await bus.emit(
                    ToolCallDenied(
                        run_id=ctx.run_id,
                        decision=decision,
                        reason=f"Grant '{decision.grant_id}' missing or expired",
                        requires_human=False,
                    )
                )
            return ToolResult(
                call_id=call.call_id,
                content=[TextBlock(text=f"Grant '{decision.grant_id}' missing or expired")],
                truncated=False,
                is_error=True,
            )

    if bus is not None:
        await bus.emit(ToolCallAuthorized(run_id=ctx.run_id, decision=decision))

    lease_id = await governor.acquire(call.tool_name, ctx.run_id)

    try:
        try:
            result = await registry.dispatch(call)
        except Exception as exc:
            logger.error("Error executing tool '%s': %s", call.tool_name, exc, exc_info=True)
            result = ToolResult(
                call_id=call.call_id,
                content=[TextBlock(text=f"Execution failure: {exc}")],
                truncated=False,
                is_error=True,
            )
    finally:
        await governor.release(lease_id)

    # Ensure call_id is always set on results from handlers that omit it.
    if not result.call_id:
        result = result.model_copy(update={"call_id": call.call_id})

    await policy.record_outcome(decision.grant_id, result)

    duration_ms = (time.monotonic() - start_time) * 1000.0

    if bus is not None:
        if result.is_error:
            await bus.emit(
                ToolCallFailed(
                    run_id=ctx.run_id,
                    call_id=call.call_id,
                    error_kind="execution_error",
                    disposition="SURFACE",
                )
            )
        else:
            await bus.emit(
                ToolCallCompleted(
                    run_id=ctx.run_id,
                    call_id=call.call_id,
                    result=result,
                    duration_ms=duration_ms,
                )
            )

    return result
