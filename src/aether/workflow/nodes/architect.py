"""ArchitectStep & ReflectorStep (ADR-0007) — decoupled planning and memory reflection nodes.

ArchitectStep takes RetrievedContext and emits a RetrievedContext carrying an initial
structured planning scratchpad. ReflectorStep takes EvaluatedCandidate on failure and updates
the plan with failure lessons.
"""

from __future__ import annotations

from datetime import UTC, datetime

from aether.domain.budget import BudgetDims
from aether.domain.ids import SpanId
from aether.domain.model_io import ModelMessage, ModelRequest, TextDelta
from aether.domain.taint import Provenance, TaintSpan
from aether.workflow.dispatch_facade import DispatchFacade
from aether.workflow.nodes.evaluate import EvaluatedCandidate
from aether.workflow.nodes.retrieve import RetrievedContext
from aether.workflow.step import StepContext, WorkflowStep

ARCHITECT_SYSTEM_ROLE = (
    "You are a precise software architect analyzing a bug. "
    "Output a short 3-line analysis plan listing:\n"
    "1. Target function/class\n"
    "2. Expected behavior vs current bug\n"
    "3. Proposed code fix logic"
)

REFLECTOR_SYSTEM_ROLE = (
    "You are a software engineer reflecting on a failed test execution. "
    "Analyze the test failure traceback and output a 2-line correction instruction "
    "stating what was wrong in the previous attempt and how to fix it."
)


class ArchitectStep(WorkflowStep[RetrievedContext, RetrievedContext]):
    node_kind = "architect"
    input_type = RetrievedContext
    output_type = RetrievedContext

    def __init__(
        self,
        dispatch: DispatchFacade,
        model_name: str,
        max_tokens: int = 1024,
    ) -> None:
        self._dispatch = dispatch
        self._model_name = model_name
        self._max_tokens = max_tokens

    async def run(self, ctx: StepContext, payload: RetrievedContext) -> RetrievedContext:
        spans = [
            TaintSpan(
                span_id=SpanId(f"{ctx.node_id}-instructions"),
                label=Provenance.OPERATOR,
                text=payload.instructions,
                source="task.instructions",
                created_at=datetime.now(UTC),
            )
        ]
        for idx, file_slice in enumerate(payload.files):
            spans.append(
                TaintSpan(
                    span_id=SpanId(f"{ctx.node_id}-file-{idx}"),
                    label=Provenance.AGENT,
                    text=f"=== {file_slice.repo_rel_path} ===\n{file_slice.text}",
                    source=f"file:{file_slice.repo_rel_path}",
                    created_at=datetime.now(UTC),
                )
            )

        sys_span = TaintSpan(
            span_id=SpanId(f"{ctx.node_id}-system"),
            label=Provenance.TRUSTED_SYSTEM,
            text=ARCHITECT_SYSTEM_ROLE,
            source="harness.architect_layer",
            created_at=datetime.now(UTC),
        )

        request = ModelRequest(
            model=self._model_name,
            messages=(
                ModelMessage(role="system", spans=(sys_span,)),
                ModelMessage(role="user", spans=tuple(spans)),
            ),
            max_tokens=self._max_tokens,
        )
        events = await self._dispatch.model(request, BudgetDims(prompt_tokens=self._max_tokens))
        plan_text = "".join(e.text for e in events if isinstance(e, TextDelta))

        # Append plan to task instructions so downstream generate node receives it in L4
        augmented_instructions = (
            f"{payload.instructions}\n\n"
            f"## Architect Plan\n{plan_text.strip()}"
        )
        return payload.model_copy(update={"instructions": augmented_instructions})


class ReflectorStep(WorkflowStep[EvaluatedCandidate, EvaluatedCandidate]):
    node_kind = "reflector"
    input_type = EvaluatedCandidate
    output_type = EvaluatedCandidate

    def __init__(
        self,
        dispatch: DispatchFacade,
        model_name: str,
        max_tokens: int = 1024,
    ) -> None:
        self._dispatch = dispatch
        self._model_name = model_name
        self._max_tokens = max_tokens

    async def run(self, ctx: StepContext, payload: EvaluatedCandidate) -> EvaluatedCandidate:
        detail = payload.report.detail or "(no gate output reported)"
        user_span = TaintSpan(
            span_id=SpanId(f"{ctx.node_id}-reflection-{payload.iteration}"),
            label=Provenance.AGENT,
            text=(
                f"Failing Test Output:\n{detail[:2000]}\n\n"
                f"Previous Patch Attempt:\n{payload.patch_text[:1000]}\n\n"
                "State what was wrong and provide the corrected logic."
            ),
            source=f"reflector:iteration-{payload.iteration}",
            created_at=datetime.now(UTC),
        )
        sys_span = TaintSpan(
            span_id=SpanId(f"{ctx.node_id}-system"),
            label=Provenance.TRUSTED_SYSTEM,
            text=REFLECTOR_SYSTEM_ROLE,
            source="harness.reflector_layer",
            created_at=datetime.now(UTC),
        )
        request = ModelRequest(
            model=self._model_name,
            messages=(
                ModelMessage(role="system", spans=(sys_span,)),
                ModelMessage(role="user", spans=(user_span,)),
            ),
            max_tokens=self._max_tokens,
        )
        events = await self._dispatch.model(request, BudgetDims(prompt_tokens=self._max_tokens))
        reflection = "".join(e.text for e in events if isinstance(e, TextDelta))

        augmented_task = payload.task.model_copy(
            update={
                "instructions": (
                    f"{payload.task.instructions}\n\n"
                    f"## Reflection (Iteration {payload.iteration})\n{reflection.strip()}"
                )
            }
        )
        return payload.model_copy(update={"task": augmented_task})


__all__ = ["ArchitectStep", "ReflectorStep"]
