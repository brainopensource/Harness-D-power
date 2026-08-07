"""A provider failure is `NONE`, never `FAILED` (audit F2).

B4 was built for the evaluator and not for the model provider, and the
asymmetry was invisible because both paths end in a `GateReport`. The path a
429, a socket reset or a read timeout used to take:

    provider raises -> StopEvent(provider_error) -> no TextDeltas
      -> GeneratedPatch(raw_output="") -> ApplyStep: "the model produced no edit"
      -> EvaluateStep runs the tests on an unmodified worktree -> exit 1
      -> GateStatus.FAILED

`measurement.md` §2 B4 exists to make exactly that unrepresentable: *an
instrument failure is never a data point.* Under a rate-limited paid provider —
which is what a 300-task publication run is — the old behaviour silently
depressed the resolve rate of whichever arm hit the limit harder, while the
per-arm instrument-error rate §4.1 requires read zero.

Every test here fails against the pre-fix nodes.
"""

from __future__ import annotations

import pytest

from aether.domain.gate import GateReport, GateStatus
from aether.domain.ids import LeaseId, NodeId, RunId, TaskId
from aether.domain.model_io import StopEvent, TextDelta
from aether.domain.task import Task, TaskSource
from aether.domain.workspace import WorktreeRef
from aether.workflow.nodes.apply import ApplyStep
from aether.workflow.nodes.evaluate import EvaluateStep
from aether.workflow.nodes.generate import GenerateStep
from aether.workflow.nodes.retrieve import RetrievedContext
from aether.workflow.step import StepContext

DIGEST = "sha256:" + "e" * 64
CTX = StepContext(run_id=RunId("r1"), node_id=NodeId("n1"), lease=LeaseId("lease-1"))


def _task() -> Task:
    return Task(
        task_id=TaskId("t1"),
        repo="org/repo",
        base_commit="a" * 40,
        instructions="add() returns the wrong value for negative operands",
        environment_image_digest=DIGEST,
        test_command_hash="sha256:" + "f" * 64,
        source=TaskSource(manifest_hash="sha256:" + "0" * 64, instance_id="t1"),
    )


def _worktree() -> WorktreeRef:
    return WorktreeRef(worktree_id="wt1", run_id=RunId("r1"), base_commit="a" * 40, abs_hint="/tmp/wt1")


class _FailingProviderFacade:
    """What `DispatchFacade.model` returns when the adapter's stream died: the
    adapter never raises past the generator, so the caller sees a terminal
    `provider_error` and nothing else."""

    def __init__(self, events: list[object] | None = None) -> None:
        self.evaluate_calls = 0
        self._events = events if events is not None else [StopEvent(reason="provider_error")]

    async def model(self, request, cost_estimate):  # noqa: ANN001, ANN201, ARG002
        return list(self._events)

    async def evaluate(self, spec, cost_estimate):  # noqa: ANN001, ANN201, ARG002
        self.evaluate_calls += 1
        return GateReport(gate="tests", status=GateStatus.FAILED, detail="1 failed")

    async def apply_patch(self, args, cost_estimate=None):  # noqa: ANN001, ANN201, ARG002
        raise AssertionError("a provider failure must not reach the worktree")

    async def write(self, args, cost_estimate=None):  # noqa: ANN001, ANN201, ARG002
        raise AssertionError("a provider failure must not reach the worktree")


async def test_a_provider_failure_is_carried_off_the_generate_node() -> None:
    facade = _FailingProviderFacade()
    step = GenerateStep(facade, model_name="m")  # type: ignore[arg-type]

    patch = await step.run(
        CTX, RetrievedContext(task=_task(), worktree=_worktree(), instructions="fix it")
    )

    assert patch.stop_reason == "provider_error"
    assert patch.raw_output == ""


async def test_apply_refuses_to_touch_the_worktree_and_flags_the_instrument() -> None:
    facade = _FailingProviderFacade()
    generated = await GenerateStep(facade, model_name="m").run(  # type: ignore[arg-type]
        CTX, RetrievedContext(task=_task(), worktree=_worktree(), instructions="fix it")
    )

    applied = await ApplyStep(facade).run(CTX, generated)  # type: ignore[arg-type]

    assert applied.applied is False
    assert applied.instrument_error is not None
    assert "provider" in applied.instrument_error


async def test_the_gate_reports_none_and_never_runs_the_tests() -> None:
    """The second assertion is the one that matters. Running the tests would
    score an unmodified worktree and return a confident FAILED for a candidate
    that was never produced."""
    facade = _FailingProviderFacade()
    generated = await GenerateStep(facade, model_name="m").run(  # type: ignore[arg-type]
        CTX, RetrievedContext(task=_task(), worktree=_worktree(), instructions="fix it")
    )
    applied = await ApplyStep(facade).run(CTX, generated)  # type: ignore[arg-type]

    candidate = await EvaluateStep(facade).run(CTX, applied)  # type: ignore[arg-type]

    assert candidate.report.status is GateStatus.NONE
    assert candidate.report.status is not GateStatus.FAILED
    assert candidate.report.instrument_error is not None
    assert facade.evaluate_calls == 0, "the judge must not be asked about a candidate that never existed"


async def test_a_none_from_a_provider_failure_never_enters_the_repair_edge() -> None:
    """The executor already refuses to route `NONE` into repair, and the repair
    node refuses one that reaches it anyway. This asserts the new `NONE` source
    inherits both, so a rate limit cannot spend the repair budget."""
    from aether.workflow.nodes.evaluate import EvaluatedCandidate
    from aether.workflow.nodes.repair import InstrumentErrorNotRepairable, RepairStep

    facade = _FailingProviderFacade()
    candidate = EvaluatedCandidate(
        task=_task(),
        worktree=_worktree(),
        report=GateReport(
            gate="tests",
            status=GateStatus.NONE,
            instrument_error="model provider failed",
        ),
    )

    with pytest.raises(InstrumentErrorNotRepairable):
        await RepairStep(facade, model_name="m").run(CTX, candidate)  # type: ignore[arg-type]


async def test_a_real_completion_is_still_judged_normally() -> None:
    """The guard must be narrow. A model that answers and is simply wrong is a
    task failure, and turning those into `NONE` would inflate the resolve rate
    by shrinking its denominator — the opposite error, and a worse one."""
    facade = _FailingProviderFacade(
        events=[TextDelta(text="diff --git a/mod.py b/mod.py\n"), StopEvent(reason="end")]
    )
    generated = await GenerateStep(facade, model_name="m").run(  # type: ignore[arg-type]
        CTX, RetrievedContext(task=_task(), worktree=_worktree(), instructions="fix it")
    )

    assert generated.stop_reason == "end"

    applied = await ApplyStep(facade).run(  # type: ignore[arg-type]
        CTX, generated.model_copy(update={"raw_output": ""})
    )
    assert applied.instrument_error is None, "an empty answer is the model's failure, not ours"

    candidate = await EvaluateStep(facade).run(CTX, applied)  # type: ignore[arg-type]
    assert candidate.report.status is GateStatus.FAILED
    assert facade.evaluate_calls == 1
