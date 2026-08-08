"""Composition root (I6) — the concrete `AdapterTable` and `Dispatcher` wiring
Steps 1-6's real adapters into the M1a walking skeleton.

No new port or business logic: `EffectRequest.descriptor` carries each
effect's payload as JSON — Frozen models are JSON round-trippable by
construction (I2/I3), so the small `*Args` models below are exactly that
payload shape, not a new port. `EffectOutcome.result_json` (kernel/dispatch.py)
carries the adapter's real result back the same way. Entry points are frozen
here; there is no DI container and no runtime registration.
"""

from __future__ import annotations

import json
import time
from typing import Any

from aether.adapters.model_provider.openai_compatible import OpenAICompatibleProvider
from aether.adapters.tools.builtin import BuiltinToolRegistry
from aether.adapters.workspace.git_cli import GitCliWorkspace
from aether.domain.budget import Actuals, BudgetDims, Lease
from aether.domain.effects import ApplyPatchArgs, ReadArgs, ShellArgs, WriteArgs
from aether.domain.model_io import ModelRequest, StopEvent, UsageEvent
from aether.kernel.bus import EventBus
from aether.kernel.dispatch import AdapterTable, Dispatcher, EffectOutcome
from aether.kernel.governor import ResourceGovernor
from aether.kernel.policy import DefaultPolicyEngine
from aether.measurement.evaluator import RealEvaluator
from aether.measurement.pricing import priced
from aether.ports.evaluator import EvalSpec
from aether.ports.policy_engine import EffectRequest


def build_adapter_table(
    workspace: GitCliWorkspace,
    tool_registry: BuiltinToolRegistry,
    model_provider: OpenAICompatibleProvider,
    evaluator: RealEvaluator,
    model_base_url: str | None = None,
) -> AdapterTable:
    """Effect_class -> adapter closure. Each closure performs the real I/O,
    JSON-encodes its result into `EffectOutcome.result_json`, and reports
    `actuals` back to the ledger — the piece that makes `Dispatcher.commit()`
    honest rather than a no-op."""

    async def _read(request: EffectRequest, lease: Lease) -> EffectOutcome:
        args = ReadArgs.model_validate_json(request.descriptor)
        file_slice = await workspace.read(args.worktree, args.repo_rel_path, args.start_line, args.end_line)
        return EffectOutcome(status="ok", result_json=file_slice.model_dump_json())

    async def _write(request: EffectRequest, lease: Lease) -> EffectOutcome:
        raw = json.loads(request.descriptor)
        if raw.get("kind") == "apply_patch":
            patch_args = ApplyPatchArgs.model_validate_json(request.descriptor)
            result = await workspace.apply_patch(patch_args.worktree, patch_args.unified_diff)
            return EffectOutcome(status="ok", result_json=result.model_dump_json())

        args = WriteArgs.model_validate_json(request.descriptor)
        await workspace.write(args.worktree, args.repo_rel_path, args.text)
        return EffectOutcome(status="ok")

    async def _shell(request: EffectRequest, lease: Lease) -> EffectOutcome:
        args = ShellArgs.model_validate_json(request.descriptor)
        # TASK-062: the lease this dispatch acquired is the real deadline, not
        # the cost estimate a node reserved against. `wall_clock_ms=0` means
        # "no wall-clock dimension was reserved" (BudgetDims default), in
        # which case the adapter falls back to its own default rather than
        # spawning with a zero timeout.
        deadline_ms = lease.reserved.wall_clock_ms or None
        result = await tool_registry.execute(args.worktree, args.call, deadline_ms)
        return EffectOutcome(status="ok", result_json=result.model_dump_json())

    async def _model(request: EffectRequest, lease: Lease) -> EffectOutcome:
        model_request = ModelRequest.model_validate_json(request.descriptor)
        events: list[dict[str, Any]] = []
        usage = BudgetDims()
        reported_usage = False
        async for event in model_provider.stream(model_request):
            events.append(event.model_dump(mode="json"))
            if isinstance(event, UsageEvent):
                reported_usage = True
                usage = BudgetDims(
                    prompt_tokens=event.prompt_tokens, completion_tokens=event.completion_tokens
                )
            if isinstance(event, StopEvent):
                break

        if not reported_usage:
            # Ollama's streamed OpenAI-compatible endpoint reports no usage
            # block. Zero tokens would price at zero and make a dollar cap
            # unenforceable against exactly the endpoints we test on, so fall
            # back to the port's own estimator and mark it as an estimate.
            estimated = await model_provider.count_tokens(model_request)
            usage = BudgetDims(prompt_tokens=estimated, completion_tokens=0)

        # `usd_micros` is filled here, at the one place that knows both the
        # model and the token counts. Before Sprint 3.5 nothing wrote it, so a
        # `seed_run_budget(usd_micros=...)` cap compared spend against a field
        # that was always zero and could never fire.
        dims = priced(model_request.model, usage, base_url=model_base_url)
        return EffectOutcome(status="ok", actuals=Actuals(dims=dims), result_json=json.dumps(events))

    async def _evaluate(request: EffectRequest, lease: Lease) -> EffectOutcome:
        spec = EvalSpec.model_validate_json(request.descriptor)
        # Wall-clock comes from the lease, not from the caller's wish: an
        # evaluation may not outlive the reservation the governor granted it.
        # (Memory/CPU/pids have no `BudgetDims` dimension to come from and are
        # composition-frozen `ContainerLimits` instead — sprint-03.md records
        # that gap rather than papering over it.)
        ceiling = lease.reserved.wall_clock_ms
        if 0 < ceiling < spec.timeout_ms:
            spec = spec.model_copy(update={"timeout_ms": ceiling})
        started = time.monotonic()
        report = await evaluator.evaluate(spec)
        elapsed_ms = int((time.monotonic() - started) * 1000)
        return EffectOutcome(
            status="ok",
            actuals=Actuals(dims=BudgetDims(wall_clock_ms=elapsed_ms)),
            result_json=report.model_dump_json(),
        )

    return {
        "read": _read,
        "write": _write,
        "shell": _shell,
        "model": _model,
        "evaluate": _evaluate,
    }


def build_dispatcher(
    workspace: GitCliWorkspace,
    tool_registry: BuiltinToolRegistry,
    model_provider: OpenAICompatibleProvider,
    evaluator: RealEvaluator,
    governor: ResourceGovernor,
    model_base_url: str | None = None,
    bus: EventBus | None = None,
) -> Dispatcher:
    """`model_base_url` is passed for **pricing**, not for calling: a localhost
    endpoint bills nothing, and a run against one should not be charged against
    a dollar cap meant for a paid provider."""
    adapters = build_adapter_table(workspace, tool_registry, model_provider, evaluator, model_base_url)
    return Dispatcher(policy=DefaultPolicyEngine(), governor=governor, adapters=adapters, bus=bus)
