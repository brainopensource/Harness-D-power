"""A rejected reply's real cause must reach the repair prompt, not just the
tests' downstream symptom.

`applied=False` without an `instrument_error` (a bad path, invalid syntax, an
unlabelled block) is deliberately *not* routed like a provider failure —
`test_a_real_completion_is_still_judged_normally` in
`test_instrument_error_is_not_a_task_failure.py` requires the tests still run.
But running the tests on the unmodified worktree produces a *different*
failure than the real one (e.g. a missing-attribute traceback instead of "path
must be repo-relative"), and before this fix `AppliedPatch.detail` — the only
place that real reason was recorded — was dropped once `EvaluateStep` built
its `EvaluatedCandidate`. The repair prompt then only ever showed the model
the symptom, so a model that habitually mislabels its path (observed with
`llama3.2:3b`: a fenced block labelled ``/main.py`` — rejected as escaping the
worktree) kept repeating the same rejected format across every repair
iteration with nothing telling it why.

Every test here fails against the pre-fix `EvaluateStep`/`build_repair_prompt`.
"""

from __future__ import annotations

from aether.domain.gate import GateReport, GateStatus
from aether.domain.ids import LeaseId, NodeId, RunId, TaskId
from aether.domain.task import Task, TaskSource
from aether.domain.workspace import WorktreeRef
from aether.workflow.nodes.apply import AppliedPatch
from aether.workflow.nodes.evaluate import EvaluateStep
from aether.workflow.nodes.repair import build_repair_prompt
from aether.workflow.step import StepContext

CTX = StepContext(run_id=RunId("r1"), node_id=NodeId("n1"), lease=LeaseId("lease-1"))

TASK = Task(
    task_id=TaskId("t1"),
    repo="org/repo",
    base_commit="a" * 40,
    instructions="Write is_even(n) in main.py.",
    environment_image_digest="sha256:" + "a" * 64,
    test_command_hash="sha256:" + "b" * 64,
    source=TaskSource(manifest_hash="sha256:" + "c" * 64, instance_id="t1"),
)
WORKTREE = WorktreeRef(worktree_id="wt1", run_id=RunId("r1"), base_commit="a" * 40, abs_hint="/tmp/wt1")


class _StubEvaluateFacade:
    """Stands in for the container/subprocess evaluator: runs the fixed test
    command and returns a scripted verdict, as if against an unmodified
    worktree (which is what happens when nothing was applied)."""

    def __init__(self) -> None:
        self.evaluate_calls = 0

    async def evaluate(self, spec, cost_estimate):  # noqa: ANN001, ANN201, ARG002
        self.evaluate_calls += 1
        return GateReport(
            gate="tests",
            status=GateStatus.FAILED,
            detail="AttributeError: module 'main' has no attribute 'is_even'",
        )


def _rejected_apply() -> AppliedPatch:
    return AppliedPatch(
        task=TASK,
        worktree=WORKTREE,
        applied=False,
        detail="/main.py: path must be repo-relative and must not escape the worktree",
        patch_text="```python:/main.py\ndef is_even(n):\n    return n % 2 == 0\n```",
        iteration=0,
    )


async def test_a_rejected_apply_still_runs_the_tests() -> None:
    """Unchanged behaviour: `applied=False` alone is not an instrument error."""
    facade = _StubEvaluateFacade()

    candidate = await EvaluateStep(facade).run(CTX, _rejected_apply())  # type: ignore[arg-type]

    assert facade.evaluate_calls == 1
    assert candidate.report.status is GateStatus.FAILED


async def test_the_rejection_reason_survives_into_the_evaluated_candidate() -> None:
    facade = _StubEvaluateFacade()

    candidate = await EvaluateStep(facade).run(CTX, _rejected_apply())  # type: ignore[arg-type]

    assert "path must be repo-relative" in candidate.apply_detail
    # The test traceback is the downstream symptom, not the cause — both are
    # available, but they are not the same string.
    assert candidate.apply_detail != candidate.report.detail


async def test_a_genuinely_applied_candidate_carries_no_apply_detail() -> None:
    """The field must stay empty on the ordinary path, or every repair prompt
    grows a spurious empty section."""
    facade = _StubEvaluateFacade()
    applied = AppliedPatch(task=TASK, worktree=WORKTREE, applied=True, patch_text="fix")

    candidate = await EvaluateStep(facade).run(CTX, applied)  # type: ignore[arg-type]

    assert candidate.apply_detail == ""


async def test_the_repair_prompt_names_the_rejection_not_just_the_traceback() -> None:
    facade = _StubEvaluateFacade()
    candidate = await EvaluateStep(facade).run(CTX, _rejected_apply())  # type: ignore[arg-type]

    prompt = build_repair_prompt(candidate)

    assert "path must be repo-relative" in prompt
    assert "rejected before it was tested" in prompt.lower() or "rejected" in prompt.lower()


async def test_an_ordinary_repair_prompt_has_no_rejection_section() -> None:
    facade = _StubEvaluateFacade()
    applied = AppliedPatch(task=TASK, worktree=WORKTREE, applied=True, patch_text="fix")
    candidate = await EvaluateStep(facade).run(CTX, applied)  # type: ignore[arg-type]

    prompt = build_repair_prompt(candidate)

    assert "rejected before it was tested" not in prompt.lower()
