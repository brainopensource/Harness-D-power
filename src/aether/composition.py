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
from typing import Any, Literal

from aether.adapters.model_provider.openai_compatible import OpenAICompatibleProvider
from aether.adapters.tools.builtin import BuiltinToolRegistry
from aether.adapters.workspace.git_cli import GitCliWorkspace
from aether.domain.budget import Actuals, BudgetDims, Lease
from aether.domain.ids import Frozen
from aether.domain.model_io import ModelRequest, StopEvent, UsageEvent
from aether.domain.tools import ToolCall
from aether.domain.workspace import WorktreeRef
from aether.kernel.dispatch import AdapterTable, Dispatcher, EffectOutcome
from aether.kernel.governor import ResourceGovernor
from aether.kernel.policy import DefaultPolicyEngine
from aether.measurement.evaluator import RealEvaluator
from aether.ports.evaluator import EvalSpec
from aether.ports.policy_engine import EffectRequest


class ReadArgs(Frozen):
    worktree: WorktreeRef
    repo_rel_path: str
    start_line: int = 1
    end_line: int = -1


class WriteArgs(Frozen):
    # "write" effect_class covers both a plain file write and a unified-diff
    # apply — `kind` discriminates which payload the `_write` closure below
    # deserializes, since EffectRequest.effect_class has no third bucket.
    kind: Literal["write_file"] = "write_file"
    worktree: WorktreeRef
    repo_rel_path: str
    text: str


class ApplyPatchArgs(Frozen):
    kind: Literal["apply_patch"] = "apply_patch"
    worktree: WorktreeRef
    unified_diff: str


class ShellArgs(Frozen):
    worktree: WorktreeRef
    call: ToolCall


def build_adapter_table(
    workspace: GitCliWorkspace,
    tool_registry: BuiltinToolRegistry,
    model_provider: OpenAICompatibleProvider,
    evaluator: RealEvaluator,
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
        result = await tool_registry.execute(args.worktree, args.call)
        return EffectOutcome(status="ok", result_json=result.model_dump_json())

    async def _model(request: EffectRequest, lease: Lease) -> EffectOutcome:
        model_request = ModelRequest.model_validate_json(request.descriptor)
        events: list[dict[str, Any]] = []
        usage = BudgetDims()
        async for event in model_provider.stream(model_request):
            events.append(event.model_dump(mode="json"))
            if isinstance(event, UsageEvent):
                usage = BudgetDims(
                    prompt_tokens=event.prompt_tokens, completion_tokens=event.completion_tokens
                )
            if isinstance(event, StopEvent):
                break
        return EffectOutcome(status="ok", actuals=Actuals(dims=usage), result_json=json.dumps(events))

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
) -> Dispatcher:
    adapters = build_adapter_table(workspace, tool_registry, model_provider, evaluator)
    return Dispatcher(policy=DefaultPolicyEngine(), governor=governor, adapters=adapters)
