"""RunLoop — multi-step agent loop with stop conditions and stuck detection (C6)."""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field

from sagiha.agency.context.assembler import ContextAssembler, result_message
from sagiha.agency.context.compactor import ExchangeCompactor
from sagiha.agency.freeze import clear_freeze, load_freeze, persist_freeze
from sagiha.domain.config import ContextConfig, PricingConfig, RepairConfig
from sagiha.domain.content import (
    Message,
    TextBlock,
    ToolCall,
    ToolResult,
    ToolSchema,
    ToolUseBlock,
)
from sagiha.domain.control import FreezeReason, FrozenRunState, RunContext
from sagiha.domain.events import (
    BudgetExhausted,
    CompactionApplied,
    GateEvaluated,
    ModelCallCompleted,
    ModelCallStarted,
    ProviderFailover,
    RepairAbandoned,
    RepairAttemptStarted,
    RunCompleted,
    RunFailed,
    RunStarted,
    StepCompleted,
    StepStarted,
)
from sagiha.domain.graph import RetrievalHit
from sagiha.domain.identity import StepId, utc_now
from sagiha.domain.trajectory import RunRecord, TrajectoryStep
from sagiha.domain.work import (
    AcceptanceCriterion,
    CostSummary,
    GateReport,
    RepairContext,
    TaskSpec,
)
from sagiha.kernel.bus import EventBus
from sagiha.kernel.dispatch import dispatch
from sagiha.kernel.policy.effects import classify_command
from sagiha.ports.evaluator import Evaluator
from sagiha.ports.governor import ResourceGovernor
from sagiha.ports.model import ModelProvider
from sagiha.ports.policy import PolicyEngine
from sagiha.ports.tool_registry import ToolRegistry
from sagiha.ports.trajectory import TrajectoryStore
from sagiha.ports.workspace import Workspace

logger = logging.getLogger(__name__)

_STUCK_REPEAT_THRESHOLD = 3

#: The default system prompt every `RunLoop` uses unless a caller overrides it — no caller in
#: this tree does. Named so the v2-S4 trace exporter (`outer_loop/export/sft.py`) can reconstruct
#: a step's assembled request with the same prompt the live run actually saw, rather than a
#: duplicated copy that could silently drift from this one.
DEFAULT_SYSTEM_PROMPT = (
    "You are an autonomous software developer agent. "
    "To solve the task, you MUST use the provided tools (apply_edit, run_command). "
    "When creating or editing a file, call apply_edit directly instead of conversational text."
)


@dataclass
class _StepPhaseOutcome:
    """What one pass of the step loop produced — either a repair attempt or the initial
    attempt. Bundles the locals `_step_phase`'s extraction pulled out of `run()` so the outer
    repair loop (v2-S7f) can accumulate cost/state across multiple phases without `run()`
    reaching into a still-running phase's internals."""

    parked: bool = False
    failed: bool = False
    stuck: bool = False
    frozen_snap: FrozenRunState | None = None
    run_usd: float = 0.0
    run_input_tokens: int = 0
    run_output_tokens: int = 0
    run_model_calls: int = 0
    #: `seq` to pass as `start_seq` to the next phase, so step ids never collide across
    #: repair attempts.
    next_seq: int = 0


def render_repair_prompt(repair: RepairContext) -> str:
    """Plain by design — the model needs the traceback, not coaching."""
    lines = [
        f"Your previous attempt did not pass. This is repair attempt {repair.attempt}.",
        "",
    ]
    for criterion in repair.failed_criteria:
        lines += [f"FAILED CHECK: {criterion.check}", "```", criterion.output.strip()[-4000:], "```", ""]
    if repair.failed_gates:
        lines += [f"FAILED GATES: {', '.join(repair.failed_gates)}", ""]
    lines += [
        "Diagnose the failure from the output above and fix it. "
        "Do not modify test files. Do not add suppressions (# type: ignore, # noqa, "
        "pytest.mark.skip) — those fail the gate.",
    ]
    return "\n".join(lines)


@dataclass
class RunLoopResult:
    task: TaskSpec
    gate_report: GateReport
    steps: list[TrajectoryStep]
    run_id: str
    #: What the run actually cost. Was not exposed at all before PR-1b, because there
    #: was no true figure to expose.
    cost: CostSummary = field(
        default_factory=lambda: CostSummary(
            usd=0.0, input_tokens=0, output_tokens=0, wall_clock_s=0.0, model_calls=0
        )
    )
    #: True when the run stopped on budget-park (status `input-required`), not failure.
    parked: bool = False
    #: The freeze snapshot written when the run parked or checkpointed on failover.
    frozen: FrozenRunState | None = None


class RunLoop:
    """Closed coding loop: assemble history → model → tools → gate."""

    def __init__(
        self,
        model_provider: ModelProvider,
        policy_engine: PolicyEngine,
        resource_governor: ResourceGovernor,
        tool_registry: ToolRegistry,
        trajectory_store: TrajectoryStore,
        bus: EventBus,
        *,
        evaluator: Evaluator,
        max_steps: int = 20,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        tool_schemas: list[ToolSchema] | None = None,
        workspace: Workspace | None = None,
        pricing: PricingConfig | None = None,
        context: ContextConfig | None = None,
        compactor: ExchangeCompactor | None = None,
        branch_id: str = "main",
        temperature: float | None = None,
        retrieval_seed: tuple[RetrievalHit, ...] = (),
        repair: RepairConfig | None = None,
    ) -> None:
        self._model = model_provider
        self._policy = policy_engine
        self._governor = resource_governor
        self._registry = tool_registry
        self._trajectory = trajectory_store
        self._bus = bus
        self._max_steps = max_steps
        self._system_prompt = system_prompt
        self._tool_schemas = tool_schemas or []
        self._workspace = workspace
        #: Candidate identity within a Best-of-N `run_id` (StepId's DAG shape already supports
        #: sibling branches — see `domain/identity.py::StepId`). Single-shot callers never set
        #: this and get the same `"main"` every prior run used.
        self._branch_id = branch_id
        #: Sampling temperature applied to every model call this loop makes. `None` (the
        #: default) leaves `ModelRequest.temperature` at whatever the assembler set (unset,
        #: today) — single-shot callers never set this. Best-of-N sets a distinct value per
        #: candidate (`SearchConfig.candidate_temperatures`) so siblings are not near-identical
        #: samples of one deterministic model call, which would make Best-of-N cost N× for the
        #: diversity of single-shot (`diversity_ratio`, v2-S4 Epic S4.2d).
        self._temperature = temperature
        self._pricing = pricing or PricingConfig()
        self._context_config = context or ContextConfig()
        self._compactor = compactor
        self._retrieval_seed = retrieval_seed
        #: `RepairConfig()` (enabled=False) preserves legacy single-attempt behavior for every
        #: caller that does not pass one — see `test_repair_disabled_matches_legacy`.
        self._repair = repair or RepairConfig()
        #: RC-8: required, never default-constructed here. `agency` building its own
        #: `GateEvaluator` meant the layer being judged also chose its judge — a TCB object
        #: constructed outside the composition root, where the `tcb-isolation` contract cannot
        #: see it. Composition already builds exactly one; every caller passes that one.
        self._evaluator: Evaluator = evaluator
        #: The last assembler built by `run`. Held so `freeze()` can lift anchored state
        #: (plan, open-file set) out of it without the caller having to thread it through.
        self._assembler: ContextAssembler | None = None
        self._next_seq: int = 1
        #: Plan/open-files to apply after the next `run()` builds its assembler (thaw path).
        self._pending_thaw_plan: tuple[str, ...] | None = None
        self._pending_thaw_open_files: tuple[str, ...] | None = None

    def _tool_signature(self, name: str, arguments: dict[str, object]) -> str:
        payload = json.dumps({"tool": name, "args": arguments}, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

    def _build_repair_context(self, attempt: int, gate_report: GateReport) -> RepairContext:
        failed_criteria = tuple(c for c in gate_report.criteria if c.required and not c.passed)
        failed_gates = tuple(
            name for name in sorted(gate_report.required_gates) if getattr(gate_report, name, None) is False
        )
        output_lines: list[str] = []
        for criterion in failed_criteria:
            output_lines.extend(criterion.output.splitlines())
        tail = "\n".join(output_lines[-self._repair.output_tail_lines :])
        return RepairContext(
            attempt=attempt,
            failed_criteria=failed_criteria,
            failed_gates=failed_gates,
            truncated_output=tail,
        )

    def _repair_signature(self, repair: RepairContext) -> str:
        """Identifies "the same failure" across attempts for `stop_on_no_progress` — same
        failed gates, same output tail. Deliberately excludes `attempt` itself."""
        payload = json.dumps(
            {"failed_gates": repair.failed_gates, "output": repair.truncated_output}, sort_keys=True
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    def _build_assembler(self, task: TaskSpec, existing_steps: list[TrajectoryStep]) -> ContextAssembler:
        """Prompt assembly moved wholesale into `agency/context/` (PR-3.1).

        It used to be four inline lines here plus a `_reconstruct_history` helper, which is
        exactly why there was nowhere to put a compaction check and no way to enforce the
        seed-only Layer 6 rule. `retrieval_seed` is passed from `RunLoop.__init__` when
        retrieval is enabled — construction-time-only by shape.
        """
        return ContextAssembler.from_trajectory(
            system_prompt=self._system_prompt,
            tool_schemas=tuple(self._tool_schemas),
            task=task,
            steps=existing_steps,
            config=self._context_config,
            compactor=self._compactor,
            retrieval_seed=self._retrieval_seed,
        )

    def freeze(
        self,
        ctx: RunContext,
        *,
        reason: FreezeReason = "checkpoint",
        worktree_ref: str | None = None,
    ) -> FrozenRunState:
        """Serializable snapshot of this run — **with no capability grant in it**.

        See `FrozenRunState`. The transcript is not copied here; it is already durable in
        `TrajectoryStore`, and a second copy is a second thing that can go stale.
        """
        anchored = self._assembler.anchored() if self._assembler is not None else None
        tainted = False
        is_tainted = getattr(self._policy, "is_tainted", None)
        if callable(is_tainted):
            tainted = bool(is_tainted(ctx.run_id))
        # Prefer an explicit worktree ref; otherwise carry base_commit so thaw can
        # rematerialize a primary-checkout run at the gate baseline when asked.
        ref = worktree_ref
        return FrozenRunState(
            run_id=ctx.run_id,
            task_id=anchored.task.task_id if anchored else ctx.run_id,
            autonomy_level=ctx.autonomy_level,
            workspace_root=ctx.workspace_root,
            budget_remaining_usd=ctx.budget_remaining_usd,
            worktree_ref=ref,
            base_commit=ctx.base_commit,
            next_seq=self._next_seq,
            plan=anchored.plan if anchored else (),
            open_files=anchored.open_files if anchored else (),
            tainted=tainted,
            frozen_at=utc_now(),
            reason=reason,
        )

    async def thaw(
        self,
        task: TaskSpec,
        frozen: FrozenRunState | None = None,
        *,
        run_id: str | None = None,
    ) -> RunLoopResult:
        """Resume a previously frozen run: rematerialize, re-seed taint, re-authorize on demand.

        Grants are never restored — thaw rebuilds a `RunContext` and mints fresh grants as
        the loop proceeds. If `frozen` is omitted, load from the freeze file for `run_id`.
        """
        if frozen is None:
            if run_id is None:
                raise ValueError("thaw requires frozen state or run_id")
            root = (
                str(self._workspace.root)  # type: ignore[attr-defined]
                if self._workspace is not None and hasattr(self._workspace, "root")
                else "."
            )
            frozen = load_freeze(root, run_id)

        if frozen.tainted:
            mark = getattr(self._policy, "mark_tainted", None)
            if callable(mark):
                mark(frozen.run_id)

        if frozen.worktree_ref and self._workspace is not None:
            await self._workspace.restore(frozen.worktree_ref)

        self._pending_thaw_plan = frozen.plan
        self._pending_thaw_open_files = frozen.open_files
        ctx = frozen.to_run_context()
        ctx = ctx.model_copy(update={"budget_remaining_usd": frozen.budget_remaining_usd})

        result = await self.run(task, ctx, resume=True)
        clear_freeze(frozen.workspace_root, frozen.run_id)
        return result

    async def run(self, task: TaskSpec, ctx: RunContext, *, resume: bool = False) -> RunLoopResult:
        """Run `task` to completion (or a stop condition).

        `resume=True` continues an interrupted `ctx.run_id`: `seq` picks up from
        `TrajectoryStore.steps_for_run`'s high-water mark (D9) — never from engine memory, which
        does not survive a restart — and prior steps are folded back into `history` and the
        returned `steps` list.
        """
        existing_steps = await self._trajectory.steps_for_run(ctx.run_id) if resume else []
        start_seq = existing_steps[-1].step_id.seq + 1 if existing_steps else 1

        # Capture the base ref before step 1 — every coding gate diffs against it.
        # A resumed run keeps the sha it started from; re-checkpointing here would
        # measure the diff against the agent's own prior work and gate nothing.
        if ctx.base_commit is None and self._workspace is not None:
            try:
                ctx = ctx.model_copy(update={"base_commit": await self._workspace.checkpoint("run-start")})
            except RuntimeError:
                # Not a git workspace. Leave base_commit unset; the gates report None
                # and the run fails closed rather than claiming a pass it cannot check.
                pass

        await self._trajectory.upsert_run(RunRecord(run_id=ctx.run_id, task=task, status="working"))
        bind_run = getattr(self._model, "bind_run", None)
        if callable(bind_run):
            bind_run(ctx.run_id)
        await self._bus.emit(
            RunStarted(
                run_id=ctx.run_id,
                task=task,
                run_context=ctx,
                profile=task.profile,
            )
        )

        assembler = self._build_assembler(task, existing_steps)
        if self._pending_thaw_plan is not None:
            assembler.set_plan(self._pending_thaw_plan)
            self._pending_thaw_plan = None
        if self._pending_thaw_open_files is not None:
            assembler.seed_open_files(self._pending_thaw_open_files)
            self._pending_thaw_open_files = None
        self._assembler = assembler
        steps: list[TrajectoryStep] = list(existing_steps)
        signature_counts: dict[str, int] = {}
        run_started = time.monotonic()

        parked = False
        failed = False
        frozen_snap: FrozenRunState | None = None
        total_usd = 0.0
        total_input_tokens = 0
        total_output_tokens = 0
        total_model_calls = 0
        gate_report: GateReport | None = None
        repair_signatures: set[str] = set()
        seq = start_seq
        attempt = 0

        while True:
            attempt += 1
            outcome = await self._step_phase(task, ctx, assembler, steps, signature_counts, start_seq=seq)
            total_usd += outcome.run_usd
            total_input_tokens += outcome.run_input_tokens
            total_output_tokens += outcome.run_output_tokens
            total_model_calls += outcome.run_model_calls
            seq = outcome.next_seq
            if outcome.frozen_snap is not None:
                frozen_snap = outcome.frozen_snap

            if outcome.parked:
                parked = True
                break
            if outcome.failed:
                failed = True
                break

            gate_report = await self._evaluator.evaluate(task, ctx)
            await self._bus.emit(GateEvaluated(run_id=ctx.run_id, gate_report=gate_report, attempt=attempt))

            if gate_report.admitted or not self._repair.enabled or attempt > self._repair.max_attempts:
                break

            repair = self._build_repair_context(attempt, gate_report)
            signature = self._repair_signature(repair)
            if self._repair.stop_on_no_progress and signature in repair_signatures:
                await self._bus.emit(
                    RepairAbandoned(run_id=ctx.run_id, reason="no_progress", attempt=attempt)
                )
                break
            repair_signatures.add(signature)

            assembler.append_repair_turn(render_repair_prompt(repair))
            await self._bus.emit(
                RepairAttemptStarted(run_id=ctx.run_id, attempt=attempt + 1, failed_gates=repair.failed_gates)
            )
            # Fresh attempt: repeated tool calls from a prior attempt must not immediately
            # trip stuck-loop detection in the next one.
            signature_counts.clear()

        if gate_report is None:
            gate_report = await self._evaluator.evaluate(task, ctx)
            await self._bus.emit(GateEvaluated(run_id=ctx.run_id, gate_report=gate_report, attempt=attempt))

        if parked:
            status = "input-required"
        elif failed:
            status = "failed"
        else:
            status = "completed"
        await self._trajectory.upsert_run(RunRecord(run_id=ctx.run_id, task=task, status=status))
        run_cost = CostSummary(
            usd=total_usd,
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            wall_clock_s=time.monotonic() - run_started,
            model_calls=total_model_calls,
        )
        await self._bus.emit(RunCompleted(run_id=ctx.run_id, gate_report=gate_report, cost=run_cost))
        return RunLoopResult(
            task=task,
            gate_report=gate_report,
            steps=steps,
            run_id=ctx.run_id,
            cost=run_cost,
            parked=parked,
            frozen=frozen_snap,
        )

    async def _step_phase(
        self,
        task: TaskSpec,
        ctx: RunContext,
        assembler: ContextAssembler,
        steps: list[TrajectoryStep],
        signature_counts: dict[str, int],
        *,
        start_seq: int,
    ) -> _StepPhaseOutcome:
        """One pass of the step loop — the initial attempt, or one v2-S7f repair attempt.

        Extracted from `run()` unchanged in behavior (see `test_repair_disabled_matches_legacy`,
        which pins byte-identical output with `RepairConfig(enabled=False)`); the only new thing
        is that `run()` may call this more than once per `run()` call.
        """
        stuck = False
        failed = False
        parked = False
        frozen_snap: FrozenRunState | None = None
        run_usd = 0.0
        run_input_tokens = 0
        run_output_tokens = 0
        run_model_calls = 0
        seq = start_seq - 1

        for seq in range(start_seq, start_seq + self._max_steps):
            self._next_seq = seq
            # RC-2: `GovernorConfig.max_wall_clock_s` was accepted and read by nothing.
            # Checked here as well as in `acquire` because the loop can burn wall clock in
            # model calls without ever touching a pooled resource, and a limit that only
            # trips on tool use does not bound a run that is stuck talking to itself.
            remaining_wall = getattr(self._governor, "remaining_wall_clock_s", None)
            if callable(remaining_wall):
                remaining_s = remaining_wall(ctx.run_id)
                if isinstance(remaining_s, (int, float)) and float(remaining_s) <= 0.0:
                    failed = True
                    await self._bus.emit(
                        RunFailed(
                            run_id=ctx.run_id,
                            error_kind="wall_clock_exhausted",
                            disposition="ABORT",
                            message="Wall-clock limit exceeded",
                        )
                    )
                    break

            remaining = await self._governor.remaining_budget(ctx.run_id)
            if remaining <= 0:
                # Budget-park: freeze (grants absent), wait for funding — not a failure.
                frozen_snap = self.freeze(ctx, reason="budget")
                frozen_snap = frozen_snap.model_copy(update={"budget_remaining_usd": 0.0})
                persist_freeze(frozen_snap)
                parked = True
                await self._bus.emit(
                    BudgetExhausted(
                        run_id=ctx.run_id,
                        spent_usd=run_usd,
                        limit_usd=ctx.budget_remaining_usd,
                        limit_kind="run",
                    )
                )
                break

            step_id = StepId(
                run_id=ctx.run_id,
                branch_id=self._branch_id,
                seq=seq,
                parent=str(seq - 1) if seq > 1 else None,
            )
            await self._bus.emit(StepStarted(run_id=ctx.run_id, step_id=step_id))

            # Compaction is checked here — once per step, pre-assembly, never mid-turn.
            # It resets the cache exactly once in exchange for reclaiming the window; run
            # continuously it pays that cost every turn and saves nothing.
            tail_before = assembler.tail_tokens()
            exchanges_before = len(assembler.exchanges)
            assembled = await assembler.assemble(role="execution")
            if assembled.compacted:
                await self._bus.emit(
                    CompactionApplied(
                        run_id=ctx.run_id,
                        step_id=step_id,
                        exchanges_before=exchanges_before,
                        exchanges_after=len(assembler.exchanges),
                        tail_tokens_before=tail_before,
                        tail_tokens_after=assembled.tail_tokens,
                        tainted_span=assembler.is_tainted(),
                    )
                )
            request = assembled.request
            if self._temperature is not None:
                request = request.model_copy(update={"temperature": self._temperature})
            digest = hashlib.sha256(request.model_dump_json().encode()).hexdigest()
            await self._bus.emit(
                ModelCallStarted(
                    run_id=ctx.run_id,
                    step_id=step_id,
                    model=request.role,
                    request_digest=digest,
                )
            )

            call_started = time.monotonic()
            completion = await self._model.complete(request)
            call_seconds = time.monotonic() - call_started

            # Failover-as-checkpoint: if the model adapter hopped providers, emit the
            # event (adapters cannot import kernel.bus) and persist a freeze snapshot.
            last_failover = getattr(self._model, "last_failover", None)
            if isinstance(last_failover, ProviderFailover):
                event = last_failover
                if not event.run_id:
                    event = event.model_copy(update={"run_id": ctx.run_id})
                await self._bus.emit(event)
                frozen_snap = self.freeze(ctx, reason="failover")
                persist_freeze(frozen_snap)

            response = completion.message
            usage = completion.usage
            cost_usd = self._pricing.cost_usd(usage)

            # The call that makes `remaining_budget()` mean anything. `record_spend`
            # was implemented, correct, and invoked from nowhere in `src/` — which is
            # what made the budget break below unreachable (H2).
            await self._governor.record_spend(ctx.run_id, cost_usd)

            step_cost = CostSummary(
                usd=cost_usd,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                wall_clock_s=call_seconds,
                model_calls=1,
            )
            run_usd += cost_usd
            run_input_tokens += usage.input_tokens
            run_output_tokens += usage.output_tokens
            run_model_calls += 1

            has_tools = any(isinstance(b, ToolUseBlock) for b in response.content)
            await self._bus.emit(
                ModelCallCompleted(
                    run_id=ctx.run_id,
                    step_id=step_id,
                    usage=usage,
                    stop_reason="tool_use" if has_tools else "end_turn",
                    cost=step_cost,
                )
            )

            tool_use_blocks = [b for b in response.content if isinstance(b, ToolUseBlock)]
            if not tool_use_blocks:
                # Model ended turn. Persist the text-only assistant turn before leaving:
                # it is part of what happened, and a resumed or replayed run that cannot
                # see it assembles a different prompt than the one that was recorded
                # (the other half of RC-4 — `from_trajectory` now reads these back).
                assembler.append_exchange(response, ())
                final_step = TrajectoryStep(
                    step_id=step_id,
                    message=response,
                    usage=usage,
                    cost=step_cost,
                    prefix_digest=assembled.stable_prefix_digest,
                )
                await self._trajectory.append_step(final_step)
                await self._bus.emit(StepCompleted(run_id=ctx.run_id, step_id=step_id, step=final_step))
                steps.append(final_step)
                break

            tool_calls: list[ToolCall] = []
            tool_results: list[ToolResult] = []
            result_messages: list[Message] = []
            tainted_exchange = False
            skipped: list[ToolUseBlock] = []
            for i, block in enumerate(tool_use_blocks):
                sig = self._tool_signature(block.tool_name, block.arguments)
                signature_counts[sig] = signature_counts.get(sig, 0) + 1
                if signature_counts[sig] >= _STUCK_REPEAT_THRESHOLD:
                    stuck = True
                    logger.warning("Stuck signature detected for %s", block.tool_name)
                    skipped = tool_use_blocks[i:]
                    break

                effect = await self._registry.get_effect_class(block.tool_name)
                if block.tool_name == "run_command":
                    effect = classify_command(block.arguments.get("command", []), effect)
                call = ToolCall(
                    call_id=block.call_id,
                    tool_name=block.tool_name,
                    arguments=block.arguments,
                    effect=effect,
                )
                result = await dispatch(
                    call=call,
                    ctx=ctx,
                    policy=self._policy,
                    governor=self._governor,
                    registry=self._registry,
                    bus=self._bus,
                )
                tool_calls.append(call)
                tool_results.append(result)
                if not result.trusted:
                    tainted_exchange = True
                # T7: envelope applied here — the single ToolResult → prompt path.
                result_messages.append(result_message(block.call_id, result, block.tool_name))

            # RC-1: the assistant message with its `tool_use` blocks is already in history.
            # Breaking out of the loop above without answering the remaining blocks leaves
            # dangling `tool_use` ids, and every provider rejects a request containing one —
            # so a run that got stuck could not be resumed, which is precisely when you
            # most want to resume it. Answer the skipped calls with explicit errors.
            for block in skipped:
                synthetic = ToolResult(
                    call_id=block.call_id,
                    content=[TextBlock(text="Skipped: run halted on repeated identical tool calls.")],
                    is_error=True,
                    trusted=True,  # harness-authored; it introduces no external content
                )
                tool_calls.append(
                    ToolCall(
                        call_id=block.call_id,
                        tool_name=block.tool_name,
                        arguments=block.arguments,
                        effect=await self._registry.get_effect_class(block.tool_name),
                    )
                )
                tool_results.append(synthetic)
                result_messages.append(result_message(block.call_id, synthetic, block.tool_name))

            assembler.append_exchange(response, tuple(result_messages), tainted=tainted_exchange)

            step = TrajectoryStep(
                step_id=step_id,
                tool_calls=tuple(tool_calls),
                tool_results=tuple(tool_results),
                message=response,
                usage=usage,
                cost=step_cost,
                prefix_digest=assembled.stable_prefix_digest,
            )
            await self._trajectory.append_step(step)
            await self._bus.emit(StepCompleted(run_id=ctx.run_id, step_id=step_id, step=step))
            steps.append(step)

            if stuck:
                failed = True
                await self._bus.emit(
                    RunFailed(
                        run_id=ctx.run_id,
                        error_kind="stuck_loop",
                        disposition="ABORT",
                        message="Repeated identical tool calls",
                    )
                )
                break

        return _StepPhaseOutcome(
            parked=parked,
            failed=failed,
            stuck=stuck,
            frozen_snap=frozen_snap,
            run_usd=run_usd,
            run_input_tokens=run_input_tokens,
            run_output_tokens=run_output_tokens,
            run_model_calls=run_model_calls,
            next_seq=seq + 1,
        )


def make_task(goal: str, checks: list[str], task_id: str | None = None) -> TaskSpec:
    return TaskSpec(
        task_id=task_id or str(uuid.uuid4()),
        goal=goal,
        acceptance=tuple(AcceptanceCriterion(description=c, check=c, required=True) for c in checks),
        profile="coding",
    )
