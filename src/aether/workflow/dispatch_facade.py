"""DispatchFacade — the object `workflow/step.py` calls "a dispatch facade
injected by the executor." Steps receive no adapter handles; every effect
goes through `Dispatcher.dispatch()` via this thin wrapper, which builds the
`EffectRequest` (descriptor = JSON payload, I2/I3) and deserializes
`EffectOutcome.result_json` back into the typed result the caller expects.
"""

from __future__ import annotations

import json

from pydantic import TypeAdapter

from aether.domain.budget import BudgetDims
from aether.domain.effects import ApplyPatchArgs, ReadArgs, ShellArgs, WriteArgs
from aether.domain.gate import GateReport
from aether.domain.model_io import ModelRequest, ModelStreamEvent
from aether.domain.taint import TaintSpan
from aether.domain.tools import ToolResult
from aether.domain.workspace import FileSlice, PatchResult
from aether.kernel.dispatch import Dispatcher, EffectOutcome
from aether.ports.evaluator import EvalSpec
from aether.ports.policy_engine import EffectRequest

_MODEL_EVENT_ADAPTER: TypeAdapter[ModelStreamEvent] = TypeAdapter(ModelStreamEvent)
_ZERO_BUDGET = BudgetDims()  # Frozen/immutable — safe as a shared default (ruff B008)


class EffectDeniedError(Exception):
    def __init__(self, outcome: EffectOutcome) -> None:
        self.outcome = outcome
        super().__init__(f"effect denied: status={outcome.status}")


class DispatchFacade:
    def __init__(self, dispatcher: Dispatcher, run_id: str) -> None:
        self._dispatcher = dispatcher
        self._run_id = run_id

    async def _dispatch(
        self,
        effect_class: str,
        descriptor_json: str,
        cost_estimate: BudgetDims,
        *,
        widens_capability: bool = False,
        justifying_spans: tuple[TaintSpan, ...] = (),
    ) -> EffectOutcome:
        request = EffectRequest(
            run_id=self._run_id,  # type: ignore[arg-type]
            effect_class=effect_class,  # type: ignore[arg-type]
            descriptor=descriptor_json,
            justifying_spans=justifying_spans,
            widens_capability=widens_capability,
        )
        outcome = await self._dispatcher.dispatch(request, cost_estimate)
        if outcome.status != "ok":
            raise EffectDeniedError(outcome)
        return outcome

    async def read(self, args: ReadArgs, cost_estimate: BudgetDims = _ZERO_BUDGET) -> FileSlice:
        outcome = await self._dispatch("read", args.model_dump_json(), cost_estimate)
        assert outcome.result_json is not None
        return FileSlice.model_validate_json(outcome.result_json)

    async def write(self, args: WriteArgs, cost_estimate: BudgetDims = _ZERO_BUDGET) -> None:
        await self._dispatch("write", args.model_dump_json(), cost_estimate)

    async def apply_patch(
        self, args: ApplyPatchArgs, cost_estimate: BudgetDims = _ZERO_BUDGET
    ) -> PatchResult:
        outcome = await self._dispatch("write", args.model_dump_json(), cost_estimate)
        assert outcome.result_json is not None
        return PatchResult.model_validate_json(outcome.result_json)

    async def shell(
        self,
        args: ShellArgs,
        cost_estimate: BudgetDims = _ZERO_BUDGET,
        *,
        justifying_spans: tuple[TaintSpan, ...] = (),
    ) -> ToolResult:
        outcome = await self._dispatch(
            "shell",
            args.model_dump_json(),
            cost_estimate,
            widens_capability=True,
            justifying_spans=justifying_spans,
        )
        assert outcome.result_json is not None
        return ToolResult.model_validate_json(outcome.result_json)

    async def model(self, request: ModelRequest, cost_estimate: BudgetDims) -> list[ModelStreamEvent]:
        outcome = await self._dispatch("model", request.model_dump_json(), cost_estimate)
        raw_events = json.loads(outcome.result_json or "[]")
        return [_MODEL_EVENT_ADAPTER.validate_python(e) for e in raw_events]

    async def evaluate(self, spec: EvalSpec, cost_estimate: BudgetDims) -> GateReport:
        outcome = await self._dispatch("evaluate", spec.model_dump_json(), cost_estimate)
        assert outcome.result_json is not None
        return GateReport.model_validate_json(outcome.result_json)
