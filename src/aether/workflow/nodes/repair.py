"""RepairStep (TASK-023) — the bounded repair edge, `evaluate →(fail, k)→
repair → apply → evaluate`.

`vision.md` §2 calls this "the single largest lever on score in the entire
system". It ships here; whether it *stays* is decided by its M2 ablation, not
by this sprint. So the bar for Sprint 3 is that it exists **correctly and
safely** — bounded, `NONE`-excluded, budget-honest — not that it wins.

Three constraints carry the weight, and each has a mechanism:

1. **Bounded.** The loop is statically unrolled to `max_iterations` by the
   executor, so the graph stays acyclic by construction. This node cannot
   iterate on its own — it has no loop in it.
2. **A `GateStatus.NONE` never routes here.** `workflow/executor.py` only
   follows the repair edge on `FAILED`; this node *also* refuses a `NONE`
   payload outright. Belt and braces on purpose: repairing against an
   instrument failure teaches the loop to fix our harness's bugs instead of
   the task's, and a wrong answer here is invisible in the aggregate.
3. **Tail-biased context.** The failing test output enters the prompt through
   `measurement.evaluator.tail_biased` — the same truncation the gate itself
   reported under, so the repair prompt and the gate never disagree about what
   the failure was.

There is no `agency/repair.py` in this sprint. `.importlinter`'s
`aether-layers` contract puts `aether.agency` and `aether.workflow` at the
same level as *independent* siblings, so a `WorkflowStep` in `workflow/nodes/`
importing prompt logic from `agency/` would break a contract that is currently
9-for-9. Splitting it needs a lattice change, which is an ADR-sized decision,
not a side effect of a sprint task — recorded in docs/agile/sprints/sprint-03.md.
"""

from __future__ import annotations

from datetime import UTC, datetime

from aether.composition import ReadArgs
from aether.domain.budget import BudgetDims
from aether.domain.gate import GateStatus
from aether.domain.ids import SpanId
from aether.domain.model_io import ModelMessage, ModelRequest, StopEvent, StopReason, TextDelta
from aether.domain.taint import Provenance, TaintSpan
from aether.domain.workspace import WorktreeRef
from aether.measurement.evaluator import tail_biased
from aether.workflow.dispatch_facade import DispatchFacade
from aether.workflow.edit_format import DEFAULT_EDIT_FORMAT, get_edit_format
from aether.workflow.nodes.evaluate import EvaluatedCandidate
from aether.workflow.nodes.generate import GeneratedPatch, build_system_text
from aether.workflow.step import StepContext, WorkflowStep

#: Test output entering the repair prompt. Smaller than the evaluator's own
#: 4000-char record on purpose: the gate keeps the fuller detail for the
#: trajectory, the prompt pays tokens for it.
REPAIR_OUTPUT_CHARS = 3000


class InstrumentErrorNotRepairable(Exception):
    """Raised when a `GateStatus.NONE` reaches the repair node.

    Not a defensive nicety — this is the second half of acceptance criterion 3.
    If the executor's routing were ever loosened, this turns a silent
    correctness bug (a loop happily "fixing" our own broken instrument) into a
    loud failure at the point it happens.
    """


def build_repair_prompt(payload: EvaluatedCandidate, current_files: str = "") -> str:
    """The repair instruction: the task, the attempt, and the failure — in
    that order, failure last, because that is where the model's attention and
    the truncation budget should land.

    Says nothing about *output format*: that lives in the system layer, which
    the node builds from its own `EditFormat`. A prompt naming one format while
    the parser expects another is a bug that looks like a bad model.
    """
    previous = payload.patch_text.strip() or "(no patch was produced on the previous attempt)"
    failure = tail_biased(payload.report.detail, REPAIR_OUTPUT_CHARS) or "(the gate reported no output)"
    
    isolated_assertion = ""
    for line in payload.report.detail.splitlines():
        line_stripped = line.strip()
        if (
            line_stripped.startswith("assert ")
            or line_stripped.startswith("AssertionError:")
            or line_stripped.startswith("FAIL: ")
        ):
            isolated_assertion = line_stripped
            break

    files_section = f"## Current source files\n{current_files}\n\n" if current_files else ""
    assertion_section = f"## Failing assertion line\n{isolated_assertion}\n\n" if isolated_assertion else ""
    
    return (
        f"A previous attempt at this task failed its tests.\n\n"
        f"## Task\n{payload.task.instructions}\n\n"
        f"{files_section}"
        f"## Previous attempt\n{previous}\n\n"
        f"{assertion_section}"
        f"## Failing test output (tail)\n{failure}\n\n"
        f"Correct the change so these tests pass."
    )


class RepairStep(WorkflowStep[EvaluatedCandidate, GeneratedPatch]):
    node_kind = "repair"
    input_type = EvaluatedCandidate
    output_type = GeneratedPatch

    def __init__(
        self,
        dispatch: DispatchFacade,
        model_name: str,
        max_tokens: int = 4096,
        edit_format: str = DEFAULT_EDIT_FORMAT,
        entry_files: tuple[str, ...] = (),
    ) -> None:
        self._dispatch = dispatch
        self._model_name = model_name
        self._max_tokens = max_tokens
        self._edit_format = get_edit_format(edit_format)
        self._entry_files = entry_files

    async def _read_current_files(self, worktree: WorktreeRef) -> str:
        if not self._entry_files:
            return ""
        parts: list[str] = []
        for path in self._entry_files:
            try:
                result = await self._dispatch.read(ReadArgs(worktree=worktree, repo_rel_path=path))
                parts.append(f"=== {path} ===\n{result.text}\n")
            except Exception as exc:
                parts.append(f"=== {path} ===\n(error: {type(exc).__name__})\n")
        return "\n".join(parts)

    async def run(self, ctx: StepContext, payload: EvaluatedCandidate) -> GeneratedPatch:
        if payload.report.status is GateStatus.NONE:
            raise InstrumentErrorNotRepairable(
                f"node {ctx.node_id}: gate reported NONE "
                f"({payload.report.instrument_error!r}) — an instrument failure is not a repair "
                "candidate (measurement.md §2 B4)"
            )
        if payload.report.status is GateStatus.PASSED:
            # Nothing to repair. The executor does not route a pass here; if it
            # ever did, returning the passing patch unchanged is the only
            # answer that cannot make things worse.
            return GeneratedPatch(
                task=payload.task,
                worktree=payload.worktree,
                raw_output=payload.patch_text,
                edit_format=self._edit_format.name,
                iteration=payload.iteration,
            )

        current_files = await self._read_current_files(payload.worktree)

        span = TaintSpan(
            span_id=SpanId(f"{ctx.node_id}-repair-{payload.iteration}"),
            # The prompt embeds test output produced by executing the
            # candidate's own code. That is not operator-authored text, and
            # labelling it as such would launder its provenance (ADR-0015).
            label=Provenance.AGENT,
            text=build_repair_prompt(payload, current_files=current_files),
            source=f"repair:iteration-{payload.iteration}",
            created_at=datetime.now(UTC),
        )
        system = TaintSpan(
            span_id=SpanId(f"{ctx.node_id}-system"),
            label=Provenance.TRUSTED_SYSTEM,
            text=build_system_text(self._edit_format.instructions()),
            source="harness.system_layer",
            created_at=datetime.now(UTC),
        )
        request = ModelRequest(
            model=self._model_name,
            messages=(
                ModelMessage(role="system", spans=(system,)),
                ModelMessage(role="user", spans=(span,)),
            ),
            max_tokens=self._max_tokens,
        )
        events = await self._dispatch.model(request, BudgetDims(prompt_tokens=self._max_tokens))

        patch_parts = [event.text for event in events if isinstance(event, TextDelta)]
        # Same reason as `GenerateStep`: a provider failure inside a repair
        # iteration must not be scored as the iteration failing to fix the bug.
        stop_reason: StopReason = "end"
        for event in events:
            if isinstance(event, StopEvent):
                stop_reason = event.reason
        return GeneratedPatch(
            task=payload.task,
            worktree=payload.worktree,
            raw_output="".join(patch_parts),
            edit_format=self._edit_format.name,
            iteration=payload.iteration + 1,
            stop_reason=stop_reason,
        )


__all__ = ["REPAIR_OUTPUT_CHARS", "InstrumentErrorNotRepairable", "RepairStep", "build_repair_prompt"]
