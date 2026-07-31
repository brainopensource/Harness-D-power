"""Unit tests for `adapters/search/best_of_n.py` — `BestOfNSearch` (v2-S4 Epic S4.2)."""

from __future__ import annotations

import pytest

from sagiha.adapters.search.best_of_n import BestOfNSearch, should_escalate
from sagiha.adapters.search.protocols import CandidateOutcome
from sagiha.adapters.search.scoring import NullScorer
from sagiha.domain.config import SearchConfig
from sagiha.domain.control import RunContext
from sagiha.domain.work import CostSummary, CriterionResult, GateReport, ReviewReport, TaskSpec


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
    """Test-local double — tracks allocate/release pairs for leak assertions."""

    def __init__(self) -> None:
        self.allocated: list[str] = []
        self.released: list[str] = []

    async def allocate(self, base_commit: str, branch_id: str, **_kwargs: object) -> object:
        self.allocated.append(branch_id)
        return object()

    async def materialize(self, branch_id: str) -> None:
        pass

    async def release(self, branch_id: str, **_kwargs: object) -> None:
        self.released.append(branch_id)


class ScriptedExecutor:
    """Returns outcomes from a script keyed by call order, so tests can control admission per
    candidate/round without a real Kernel/RunLoop. Allocates on `repair_round==0` so parallel
    leak tests exercise the same allocate→release pairing as `KernelCandidateExecutor`."""

    def __init__(
        self,
        script: list[CandidateOutcome],
        *,
        worktree_manager: FakeWorktreeManager | None = None,
    ) -> None:
        self._script = list(script)
        self.calls = 0
        self._worktree_manager = worktree_manager

    async def execute(self, task, context, *, branch_id, base_commit, temperature=None, repair_round=0):
        if repair_round == 0 and self._worktree_manager is not None:
            await self._worktree_manager.allocate(base_commit, branch_id)
        outcome = self._script[min(self.calls, len(self._script) - 1)]
        self.calls += 1
        return outcome.model_copy(update={"branch_id": branch_id, "temperature": temperature or 0.0})


def _outcome(
    admitted: bool,
    *,
    diff_digest: str = "x",
    cost: CostSummary | None = None,
) -> CandidateOutcome:
    return CandidateOutcome(
        branch_id="b",
        run_id="r",
        worktree_ref="b",
        gate_report=_gate_report(admitted),
        diff_digest=diff_digest,
        cost=cost,
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
async def test_default_config_allows_repair_after_first_gate_fail() -> None:
    """Shipped defaults: prune=False and escalate_after_failures=3 so max_repair_rounds=2
    is reachable (audit defects #5/#6)."""
    worktree_manager = FakeWorktreeManager()
    executor = ScriptedExecutor([_outcome(False), _outcome(True)])
    search = BestOfNSearch(
        worktree_manager=worktree_manager,
        executor=executor,
        scorer=NullScorer(),
        config=SearchConfig(launch_mode="sequential"),
    )
    assert search._config.prune_on_first_gate_fail is False
    assert search._config.escalate_after_failures == 3
    await search.propose(_task(), _context(), n=1)
    assert executor.calls == 2, "expected one repair round under shipped defaults"


@pytest.mark.asyncio
async def test_prune_on_first_gate_fail_skips_repair() -> None:
    """`prune_on_first_gate_fail=True` is the cheap / no-repair profile — distinct from
    worktree release, which always runs in `_run_and_release_one`'s finally."""
    worktree_manager = FakeWorktreeManager()
    executor = ScriptedExecutor([_outcome(False), _outcome(True)])
    search = BestOfNSearch(
        worktree_manager=worktree_manager,
        executor=executor,
        scorer=NullScorer(),
        config=SearchConfig(launch_mode="sequential", prune_on_first_gate_fail=True, max_repair_rounds=2),
    )
    await search.propose(_task(), _context(), n=1)
    assert executor.calls == 1, "expected no repair round under prune_on_first_gate_fail=True"
    assert worktree_manager.released  # release still happens


@pytest.mark.asyncio
async def test_max_repair_rounds_zero_skips_repair() -> None:
    worktree_manager = FakeWorktreeManager()
    executor = ScriptedExecutor([_outcome(False), _outcome(True)])
    search = BestOfNSearch(
        worktree_manager=worktree_manager,
        executor=executor,
        scorer=NullScorer(),
        config=SearchConfig(launch_mode="sequential", prune_on_first_gate_fail=False, max_repair_rounds=0),
    )
    await search.propose(_task(), _context(), n=1)
    assert executor.calls == 1


@pytest.mark.asyncio
async def test_escalate_stop_allows_two_repair_rounds_under_default() -> None:
    """With escalate_after_failures=3 and max_repair_rounds=2, two repairs run before stop."""
    worktree_manager = FakeWorktreeManager()
    executor = ScriptedExecutor([_outcome(False), _outcome(False), _outcome(False)])
    search = BestOfNSearch(
        worktree_manager=worktree_manager,
        executor=executor,
        scorer=NullScorer(),
        config=SearchConfig(launch_mode="sequential", n_policy="escalating"),
    )
    await search.propose(_task(), _context(), n=1)
    assert executor.calls == 3  # initial + 2 repairs


def test_search_config_shipped_defaults() -> None:
    cfg = SearchConfig()
    assert cfg.enabled is False
    assert cfg.prune_on_first_gate_fail is False
    assert cfg.escalate_after_failures == 3
    assert cfg.max_repair_rounds == 2


def _cost(usd: float) -> CostSummary:
    return CostSummary(usd=usd, input_tokens=10, output_tokens=5, wall_clock_s=1.0, model_calls=1)


def test_batch_cost_sums_all_candidates_not_winner_only() -> None:
    search = BestOfNSearch(
        worktree_manager=FakeWorktreeManager(),
        executor=ScriptedExecutor([]),
        scorer=NullScorer(),
        config=SearchConfig(),
    )
    search._outcomes = {  # type: ignore[attr-defined]
        "b1": _outcome(True, cost=_cost(1.0)),
        "b2": _outcome(False, cost=_cost(2.0)),
        "b3": _outcome(True, cost=_cost(3.0)),
    }
    total = search.batch_cost(["b1", "b2", "b3"])
    assert total.usd == pytest.approx(6.0)
    assert total.model_calls == 3


def test_batch_cost_skips_none_cost_outcomes() -> None:
    search = BestOfNSearch(
        worktree_manager=FakeWorktreeManager(),
        executor=ScriptedExecutor([]),
        scorer=NullScorer(),
        config=SearchConfig(),
    )
    search._outcomes = {  # type: ignore[attr-defined]
        "b1": _outcome(True, cost=_cost(1.0)),
        "b2": _outcome(False, cost=None),
        "b3": _outcome(True, cost=_cost(2.0)),
    }
    total = search.batch_cost(["b1", "b2", "b3"])
    assert total.usd == pytest.approx(3.0)
    assert total.model_calls == 2


@pytest.mark.asyncio
async def test_parallel_cancel_on_clean_admit_releases_every_allocate() -> None:
    """Parallel contention probe: every allocate has a matching release, including peers
    cancelled after a clean admit (shielded finally in `_run_and_release_one`)."""
    worktree_manager = FakeWorktreeManager()
    # First candidate admits; remaining may still start / get cancelled mid-flight.
    executor = ScriptedExecutor(
        [_outcome(True, cost=_cost(1.0)), _outcome(False, cost=_cost(1.0)), _outcome(False, cost=_cost(1.0))],
        worktree_manager=worktree_manager,
    )
    search = BestOfNSearch(
        worktree_manager=worktree_manager,
        executor=executor,
        scorer=NullScorer(),
        config=SearchConfig(
            launch_mode="parallel",
            cancel_on_clean_admit=True,
            stagger_s=0.0,
            prune_on_first_gate_fail=True,
        ),
        max_concurrent=3,
    )
    branch_ids = await search.propose(_task(), _context(), n=3)
    # Every allocate must have a matching release (zero leaked worktrees). Branches cancelled
    # before they enter `_run_and_release_one` never allocate — that is not a leak.
    assert set(worktree_manager.allocated) <= set(worktree_manager.released)
    assert worktree_manager.allocated, "expected at least the admitting candidate to allocate"
    # Peers that finished still land in `_outcomes` and contribute to batch_cost.
    finished = list(search._outcomes.keys())  # type: ignore[attr-defined]
    total = search.batch_cost(finished)
    assert total.usd == pytest.approx(float(len(finished)))
    assert set(finished) <= set(branch_ids)
