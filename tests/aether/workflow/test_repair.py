"""The bounded repair edge (TASK-023) — routing, bounds, budget, truncation.

The four things that must hold, and what would happen if they did not:

* bounded — an unrolled loop runs at most `max_iterations` times, or a
  benchmark run never terminates;
* `NONE` never routes into repair, or the loop spends its budget "fixing" our
  own instrument errors and the spend looks like ordinary work;
* each iteration reserves its own budget from the governor, or a bounded loop
  is bounded in count but not in cost;
* the failure block, not the pass list, enters the repaired context.
"""

from __future__ import annotations

from typing import Any

import pytest

from aether.domain.budget import BudgetDims
from aether.domain.gate import GateReport, GateStatus
from aether.domain.ids import LeaseId, RunId, TaskId
from aether.domain.task import Task, TaskSource
from aether.domain.workspace import WorktreeRef
from aether.kernel.bus import EventBus
from aether.kernel.governor import ResourceGovernor
from aether.workflow.executor import WorkflowExecutor, gate_status_of
from aether.workflow.nodes.apply import AppliedPatch
from aether.workflow.nodes.evaluate import EvaluatedCandidate
from aether.workflow.nodes.generate import GeneratedPatch
from aether.workflow.nodes.repair import (
    REPAIR_OUTPUT_CHARS,
    InstrumentErrorNotRepairable,
    RepairStep,
    build_repair_prompt,
)
from aether.workflow.step import StepContext, WorkflowStep

TASK = Task(
    task_id=TaskId("t1"),
    repo="org/repo",
    base_commit="a" * 40,
    instructions="Fix the adder.",
    environment_image_digest="sha256:" + "a" * 64,
    test_command_hash="sha256:" + "b" * 64,
    source=TaskSource(manifest_hash="sha256:" + "c" * 64, instance_id="i1"),
)
WORKTREE = WorktreeRef(worktree_id="wt-1", run_id=RunId("run-1"), base_commit="a" * 40, abs_hint="/tmp")


def _candidate(status: GateStatus, iteration: int = 0, detail: str = "") -> EvaluatedCandidate:
    return EvaluatedCandidate(
        task=TASK,
        worktree=WORKTREE,
        report=GateReport(
            gate="tests",
            status=status,
            detail=detail,
            instrument_error="exit 127" if status is GateStatus.NONE else None,
        ),
        patch_text="diff --git a/x b/x\n",
        iteration=iteration,
    )


# ------------------------------------------------------------- the executor


class _ScriptedEvaluate(WorkflowStep[Any, EvaluatedCandidate]):
    """Returns a scripted verdict per call, so a repair loop can be driven
    through fail → fail → pass without a model or a container."""

    node_kind = "evaluate"

    def __init__(self, verdicts: list[GateStatus]) -> None:
        self._verdicts = verdicts
        self.calls = 0

    async def run(self, ctx: StepContext, payload: Any) -> EvaluatedCandidate:
        status = self._verdicts[min(self.calls, len(self._verdicts) - 1)]
        self.calls += 1
        return _candidate(status, iteration=getattr(payload, "iteration", 0))


class _CountingStep(WorkflowStep[Any, Any]):
    def __init__(self, node_kind: str, output: Any) -> None:
        self.node_kind = node_kind
        self._output = output
        self.calls = 0
        self.leases: list[LeaseId] = []

    async def run(self, ctx: StepContext, payload: Any) -> Any:
        self.calls += 1
        self.leases.append(ctx.lease)
        return self._output


def _topology(max_iterations: int = 3) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "topology_id": "test_repair",
        "description": "test",
        "nodes": [
            {"id": "apply", "kind": "apply", "budget": {"wall_clock_ms": 1000}},
            {"id": "evaluate", "kind": "evaluate", "budget": {"wall_clock_ms": 1000}},
            {"id": "repair", "kind": "repair", "budget": {"prompt_tokens": 10}},
        ],
        "edges": [{"from": "apply", "to": "evaluate"}],
        "repair": {
            "from_node": "evaluate",
            "via_nodes": ["repair", "apply"],
            "back_to": "evaluate",
            "max_iterations": max_iterations,
            "budget_per_iteration": {"usd_micros": 1000, "prompt_tokens": 100, "wall_clock_ms": 10000},
        },
    }


def _registry(apply_step: Any, evaluate: Any, repair: Any) -> dict[str, Any]:
    """kind -> factory. The executor builds one instance per node from these,
    so a topology with two nodes of one kind gets two instances (B1)."""
    return {
        "apply": lambda params: apply_step,
        "evaluate": lambda params: evaluate,
        "repair": lambda params: repair,
    }


def _executor(verdicts: list[GateStatus], max_iterations: int = 3):  # noqa: ANN202
    evaluate = _ScriptedEvaluate(verdicts)
    repair = _CountingStep(
        "repair", GeneratedPatch(task=TASK, worktree=WORKTREE, raw_output="fix", iteration=1)
    )
    apply_step = _CountingStep(
        "apply", AppliedPatch(task=TASK, worktree=WORKTREE, applied=True, patch_text="fix")
    )
    governor = ResourceGovernor()
    executor = WorkflowExecutor(
        _topology(max_iterations),
        _registry(apply_step, evaluate, repair),
        EventBus(),
        governor,
    )
    return executor, evaluate, repair, apply_step, governor


async def test_a_failing_gate_routes_into_repair_and_stops_when_it_passes() -> None:
    executor, evaluate, repair, _apply, _gov = _executor([GateStatus.FAILED, GateStatus.PASSED])

    result = await executor.execute(
        RunId("run-1"), AppliedPatch(task=TASK, worktree=WORKTREE, applied=True)
    )

    assert repair.calls == 1
    assert evaluate.calls == 2  # initial + one repaired re-evaluation
    assert result.report.status is GateStatus.PASSED


async def test_the_loop_is_bounded_by_max_iterations() -> None:
    """A candidate that never passes stops at the bound, not at exhaustion."""
    executor, evaluate, repair, _apply, _gov = _executor([GateStatus.FAILED], max_iterations=3)

    result = await executor.execute(
        RunId("run-1"), AppliedPatch(task=TASK, worktree=WORKTREE, applied=True)
    )

    assert repair.calls == 3
    assert evaluate.calls == 4  # the initial verdict plus one per iteration
    assert result.report.status is GateStatus.FAILED


@pytest.mark.parametrize("bound", [1, 2, 5])
async def test_the_bound_is_honoured_exactly(bound: int) -> None:
    executor, _evaluate, repair, _apply, _gov = _executor([GateStatus.FAILED], max_iterations=bound)

    await executor.execute(RunId("run-1"), AppliedPatch(task=TASK, worktree=WORKTREE, applied=True))

    assert repair.calls == bound


async def test_an_instrument_error_never_routes_into_repair() -> None:
    """**Acceptance criterion 3.** NONE is unmeasured, not failed. Repairing
    against it teaches the loop to fix our bugs instead of the task's."""
    executor, evaluate, repair, _apply, _gov = _executor([GateStatus.NONE])

    result = await executor.execute(
        RunId("run-1"), AppliedPatch(task=TASK, worktree=WORKTREE, applied=True)
    )

    assert repair.calls == 0
    assert evaluate.calls == 1
    assert result.report.status is GateStatus.NONE


async def test_a_passing_gate_never_routes_into_repair() -> None:
    executor, _evaluate, repair, _apply, _gov = _executor([GateStatus.PASSED])

    await executor.execute(RunId("run-1"), AppliedPatch(task=TASK, worktree=WORKTREE, applied=True))

    assert repair.calls == 0


async def test_each_iteration_reserves_its_own_budget_as_a_parent_lease() -> None:
    """Acceptance criterion 4: N iterations are N reservations, and every node
    inside an iteration carves a *child* lease from that iteration's lease."""
    executor, _evaluate, repair, apply_step, _gov = _executor([GateStatus.FAILED], max_iterations=2)

    await executor.execute(RunId("run-1"), AppliedPatch(task=TASK, worktree=WORKTREE, applied=True))

    # Two iterations => two distinct repair-node leases, and the apply node ran
    # once outside the loop plus once per iteration.
    assert len(set(repair.leases)) == 2
    assert apply_step.calls == 3


async def test_exhausting_the_budget_ends_the_loop_not_the_run() -> None:
    """Criterion 4's second half. A denied reservation must not raise: the
    candidate keeps the verdict it already earned."""
    executor, _evaluate, repair, _apply, governor = _executor([GateStatus.FAILED], max_iterations=3)
    # A run ceiling that funds the linear chain but not a repair iteration.
    governor.seed_run_budget(RunId("run-1"), BudgetDims(wall_clock_ms=5000, usd_micros=0))

    result = await executor.execute(
        RunId("run-1"), AppliedPatch(task=TASK, worktree=WORKTREE, applied=True)
    )

    assert repair.calls == 0
    assert result.report.status is GateStatus.FAILED


async def test_a_repair_iteration_event_is_emitted_per_iteration() -> None:
    """The repair edge's cost has to be visible per iteration, or its M2
    ablation cannot price it."""
    evaluate = _ScriptedEvaluate([GateStatus.FAILED])
    repair = _CountingStep(
        "repair", GeneratedPatch(task=TASK, worktree=WORKTREE, raw_output="fix", iteration=1)
    )
    apply_step = _CountingStep("apply", AppliedPatch(task=TASK, worktree=WORKTREE, applied=True))
    bus = EventBus()
    bus.subscribe("test", drop_policy="never")
    executor = WorkflowExecutor(
        _topology(2), _registry(apply_step, evaluate, repair), bus, ResourceGovernor()
    )

    await executor.execute(RunId("run-1"), AppliedPatch(task=TASK, worktree=WORKTREE, applied=True))

    kinds = [event.kind for event in bus.drain("test")]
    assert kinds.count("repair_iteration_started") == 2


def test_gate_status_of_distinguishes_no_verdict_from_a_none_verdict() -> None:
    """`None` (this payload carries no gate) and `GateStatus.NONE` (the gate
    reported an instrument error) are different facts."""
    assert gate_status_of(AppliedPatch(task=TASK, worktree=WORKTREE, applied=True)) is None
    assert gate_status_of(_candidate(GateStatus.NONE)) is GateStatus.NONE
    assert gate_status_of(_candidate(GateStatus.FAILED)) is GateStatus.FAILED


# ------------------------------------------------------------ the repair node


class _FakeFacade:
    """Captures the `ModelRequest` the repair node builds."""

    def __init__(self) -> None:
        self.request: Any = None

    async def model(self, request: Any, cost_estimate: BudgetDims) -> list[Any]:
        from aether.domain.model_io import TextDelta

        self.request = request
        return [TextDelta(text="diff --git a/fixed b/fixed\n")]


async def test_the_repair_node_refuses_an_instrument_error_outright() -> None:
    """Second line of defence behind the executor's routing: if the routing
    were ever loosened, this fails loudly instead of quietly repairing our
    own instrument."""
    step = RepairStep(_FakeFacade(), model_name="m")  # type: ignore[arg-type]
    ctx = StepContext(run_id=RunId("run-1"), node_id="repair", lease=LeaseId("l1"))  # type: ignore[arg-type]

    with pytest.raises(InstrumentErrorNotRepairable):
        await step.run(ctx, _candidate(GateStatus.NONE))


async def test_the_repair_node_increments_the_iteration_counter() -> None:
    facade = _FakeFacade()
    step = RepairStep(facade, model_name="m")  # type: ignore[arg-type]
    ctx = StepContext(run_id=RunId("run-1"), node_id="repair", lease=LeaseId("l1"))  # type: ignore[arg-type]

    result = await step.run(ctx, _candidate(GateStatus.FAILED, iteration=1))

    assert result.iteration == 2
    assert result.patch_text == "diff --git a/fixed b/fixed\n"


def test_test_output_enters_the_prompt_tail_biased() -> None:
    """Criterion 5: the repair edge needs the traceback, not the pass list."""
    passes = "\n".join(f"tests/test_{i}.py::test_ok PASSED" for i in range(2000))
    traceback = "E   AssertionError: add(1, 2) == -1"
    payload = _candidate(GateStatus.FAILED, detail=f"{passes}\n{traceback}")

    prompt = build_repair_prompt(payload)

    assert traceback in prompt
    assert "tests/test_0.py" not in prompt  # the head was dropped, not the tail
    assert len(prompt) < len(payload.report.detail)
    assert REPAIR_OUTPUT_CHARS <= 4000  # never wider than what the gate recorded


def test_the_prompt_carries_the_attempt_being_repaired() -> None:
    prompt = build_repair_prompt(_candidate(GateStatus.FAILED, detail="boom"))

    assert "Fix the adder." in prompt
    assert "diff --git a/x b/x" in prompt
    assert prompt.index("Fix the adder.") < prompt.index("boom")  # failure last
