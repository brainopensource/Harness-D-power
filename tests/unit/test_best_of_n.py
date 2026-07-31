"""Unit tests for `adapters/search/best_of_n.py` — `BestOfNSearch` (v2-S4 Epic S4.2)."""

from __future__ import annotations

import pytest

from sagiha.adapters.search.best_of_n import BestOfNSearch, should_escalate
from sagiha.adapters.search.protocols import CandidateOutcome
from sagiha.adapters.search.scoring import NullScorer
from sagiha.domain.config import SearchConfig
from sagiha.domain.control import RunContext
from sagiha.domain.work import CriterionResult, GateReport, ReviewReport, TaskSpec


def _task() -> TaskSpec:
    return TaskSpec(task_id="t1", goal="fix it", acceptance=())


def _context() -> RunContext:
    return RunContext(
        run_id="run1", autonomy_level="interactive", workspace_root="/tmp", budget_remaining_usd=5.0
    )


def _gate_report(admitted: bool) -> GateReport:
    return GateReport(
        criteria=(CriterionResult(description="a", check="a", passed=admitted, required=True),),
        no_new_suppressions=admitted,
        tests_unmodified=admitted,
        diff_within_bounds=admitted,
    )


class FakeWorktreeManager:
    def __init__(self) -> None:
        self.released: list[str] = []

    async def allocate(self, base_commit: str, branch_id: str) -> object:
        return object()

    async def materialize(self, branch_id: str) -> None:
        pass

    async def release(self, branch_id: str) -> None:
        self.released.append(branch_id)


class ScriptedExecutor:
    """Returns outcomes from a script keyed by call order, so tests can control admission per
    candidate/round without a real Kernel/RunLoop."""

    def __init__(self, script: list[CandidateOutcome]) -> None:
        self._script = list(script)
        self.calls = 0

    async def execute(self, task, context, *, branch_id, base_commit, temperature=None, repair_round=0):
        outcome = self._script[min(self.calls, len(self._script) - 1)]
        self.calls += 1
        return outcome.model_copy(update={"branch_id": branch_id, "temperature": temperature or 0.0})


def _outcome(admitted: bool, *, diff_digest: str = "x") -> CandidateOutcome:
    return CandidateOutcome(
        branch_id="b",
        run_id="r",
        worktree_ref="b",
        gate_report=_gate_report(admitted),
        diff_digest=diff_digest,
    )


def test_should_escalate_fixed_policy_never_escalates() -> None:
    config = SearchConfig(n_policy="fixed", escalate_after_failures=1)
    assert should_escalate(failures=99, files_changed=99, diff_lines=99, config=config) is False


def test_should_escalate_triggers_on_failures_threshold() -> None:
    config = SearchConfig(n_policy="escalating", escalate_after_failures=2)
    assert should_escalate(failures=2, files_changed=0, diff_lines=0, config=config) is True
    assert should_escalate(failures=1, files_changed=0, diff_lines=0, config=config) is False


@pytest.mark.asyncio
async def test_propose_sequential_runs_n_candidates_and_releases_each() -> None:
    worktree_manager = FakeWorktreeManager()
    executor = ScriptedExecutor([_outcome(True), _outcome(True), _outcome(True)])
    search = BestOfNSearch(
        worktree_manager=worktree_manager,
        executor=executor,
        scorer=NullScorer(),
        config=SearchConfig(launch_mode="sequential"),
    )
    branch_ids = await search.propose(_task(), _context(), n=3)
    assert len(branch_ids) == 3
    assert worktree_manager.released == branch_ids


@pytest.mark.asyncio
async def test_select_prefers_admitted_over_non_admitted() -> None:
    worktree_manager = FakeWorktreeManager()
    executor = ScriptedExecutor([_outcome(False), _outcome(True)])
    search = BestOfNSearch(
        worktree_manager=worktree_manager,
        executor=executor,
        scorer=NullScorer(),
        config=SearchConfig(launch_mode="sequential", prune_on_first_gate_fail=True),
    )
    branch_ids = await search.propose(_task(), _context(), n=2)
    winner = await search.select(branch_ids)
    # winner must be the admitted candidate (index 1), never the non-admitted one.
    report = await search.evaluate(winner)
    assert report is not None and report.admitted is True


@pytest.mark.asyncio
async def test_select_falls_back_to_best_effort_when_nothing_admitted() -> None:
    worktree_manager = FakeWorktreeManager()
    executor = ScriptedExecutor([_outcome(False), _outcome(False)])
    search = BestOfNSearch(
        worktree_manager=worktree_manager,
        executor=executor,
        scorer=NullScorer(),
        config=SearchConfig(launch_mode="sequential", prune_on_first_gate_fail=True),
    )
    branch_ids = await search.propose(_task(), _context(), n=2)
    winner = await search.select(branch_ids)
    assert winner in branch_ids  # best-effort pick, not a raised error


@pytest.mark.asyncio
async def test_select_raises_on_empty_candidate_list() -> None:
    search = BestOfNSearch(
        worktree_manager=FakeWorktreeManager(),
        executor=ScriptedExecutor([]),
        scorer=NullScorer(),
        config=SearchConfig(),
    )
    with pytest.raises(ValueError):
        await search.select([])


def test_diversity_ratio_all_identical_diffs_is_low() -> None:
    search = BestOfNSearch(
        worktree_manager=FakeWorktreeManager(),
        executor=ScriptedExecutor([]),
        scorer=NullScorer(),
        config=SearchConfig(),
    )
    search._outcomes = {  # type: ignore[attr-defined]
        "b1": _outcome(True, diff_digest="same"),
        "b2": _outcome(True, diff_digest="same"),
        "b3": _outcome(True, diff_digest="same"),
    }
    assert search.diversity_ratio(["b1", "b2", "b3"]) == pytest.approx(1 / 3)


def test_diversity_ratio_all_distinct_diffs_is_one() -> None:
    search = BestOfNSearch(
        worktree_manager=FakeWorktreeManager(),
        executor=ScriptedExecutor([]),
        scorer=NullScorer(),
        config=SearchConfig(),
    )
    search._outcomes = {  # type: ignore[attr-defined]
        "b1": _outcome(True, diff_digest="d1"),
        "b2": _outcome(True, diff_digest="d2"),
        "b3": _outcome(True, diff_digest="d3"),
    }
    assert search.diversity_ratio(["b1", "b2", "b3"]) == 1.0


def test_diversity_ratio_empty_branch_list_is_zero() -> None:
    search = BestOfNSearch(
        worktree_manager=FakeWorktreeManager(),
        executor=ScriptedExecutor([]),
        scorer=NullScorer(),
        config=SearchConfig(),
    )
    assert search.diversity_ratio([]) == 0.0


class FakeBus:
    def __init__(self) -> None:
        self.events: list[object] = []

    async def emit(self, event: object) -> None:
        self.events.append(event)


@pytest.mark.asyncio
async def test_select_emits_diversity_ratio_on_candidate_selected() -> None:
    """RC/defect #4: `diversity_ratio` was computed but never reported anywhere. `select()`
    now stamps it on `CandidateSelected` — the one event a caller already has to consume to
    learn the winner, so the validity precondition travels with the result rather than
    requiring a second, unwired call."""
    from sagiha.domain.events import CandidateSelected

    worktree_manager = FakeWorktreeManager()
    executor = ScriptedExecutor([_outcome(True, diff_digest="d1"), _outcome(True, diff_digest="d2")])
    bus = FakeBus()
    search = BestOfNSearch(
        worktree_manager=worktree_manager,
        executor=executor,
        scorer=NullScorer(),
        config=SearchConfig(launch_mode="sequential"),
        bus=bus,
    )
    branch_ids = await search.propose(_task(), _context(), n=2)
    await search.select(branch_ids)

    selected = [e for e in bus.events if isinstance(e, CandidateSelected)]
    assert len(selected) == 1
    assert selected[0].diversity_ratio == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_score_standalone_synthesizes_outcome_from_diff() -> None:
    search = BestOfNSearch(
        worktree_manager=FakeWorktreeManager(),
        executor=ScriptedExecutor([]),
        scorer=NullScorer(),
        config=SearchConfig(),
    )
    review = await search.score(_task(), "diff contents", "unknown-branch")
    assert isinstance(review, ReviewReport)


@pytest.mark.asyncio
async def test_prune_on_first_gate_fail_default_disables_repair() -> None:
    """Documents current behavior: with the shipped default (`prune_on_first_gate_fail=True`),
    a failing candidate is never revised — `max_repair_rounds` is unreachable. Flagged in review
    as defect #5 (the flag's docstring claims 'releases at first failure', not 'disables repair
    entirely'); this test pins today's actual behavior so a future fix changes it deliberately."""
    worktree_manager = FakeWorktreeManager()
    executor = ScriptedExecutor([_outcome(False), _outcome(True)])  # 2nd call would succeed
    search = BestOfNSearch(
        worktree_manager=worktree_manager,
        executor=executor,
        scorer=NullScorer(),
        config=SearchConfig(launch_mode="sequential", prune_on_first_gate_fail=True, max_repair_rounds=2),
    )
    await search.propose(_task(), _context(), n=1)
    assert executor.calls == 1, "expected no repair round under prune_on_first_gate_fail=True"
