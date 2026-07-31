"""Best-of-N candidate search with sequential repair (ADR-0005) — `CandidateSearch` v2.

Pure orchestration: this module knows nothing about `Kernel`, `RunLoop`, or `build_kernel` (the
`layers` import contract forbids `sagiha.adapters` from reaching `sagiha.agency`/`sagiha.kernel`,
and importing `sagiha.composition` here would be a literal circular import anyway — composition
constructs this class). Everything mechanism-shaped is delegated to an injected
`CandidateExecutor`; everything policy-shaped (how many candidates, pruning, repair, ranking,
selection) lives here, which is what lets the sequential and parallel launch strategies
(`docs/implementation/development_plan_v2.md` v2-S4 Epic S4.2) share one policy path and differ
only in how launches are scheduled.
"""

from __future__ import annotations

import hashlib
import logging
import uuid

import anyio

from sagiha.adapters.search.protocols import (
    CandidateExecutor,
    CandidateOutcome,
    CandidateScorer,
    EventEmitter,
)
from sagiha.domain.config import SearchConfig
from sagiha.domain.control import RunContext
from sagiha.domain.events import (
    CandidateProposed,
    CandidateSelected,
    GateEvaluated,
    ReviewCompleted,
    WorktreeReleased,
)
from sagiha.domain.work import CostSummary, GateReport, ReviewReport, TaskSpec
from sagiha.ports.workspace import WorktreeManager

logger = logging.getLogger(__name__)


def should_escalate(*, failures: int, files_changed: int, diff_lines: int, config: SearchConfig) -> bool:
    """Deterministic **stop** condition over the three `escalate_*` thresholds.

    This stops further repair on a candidate — it does **not** widen search (no N bump, no
    strategy change). No learned router until label volume exists (ADR-0005 cold-start
    doctrine). `config.n_policy == "fixed"` disables the ladder entirely: repair always runs
    the full `max_repair_rounds`, win or lose.
    """
    if config.n_policy == "fixed":
        return False
    return (
        failures >= config.escalate_after_failures
        or files_changed >= config.escalate_on_files
        or diff_lines >= config.escalate_on_diff_lines
    )


def _revise_with_feedback(task: TaskSpec, outcome: CandidateOutcome) -> TaskSpec:
    """Sequential repair: re-enter the *same* worktree with the failing gate's own output
    appended, as a new revision — never a mutation of the original `TaskSpec`."""
    failing = [c for c in (outcome.gate_report.criteria if outcome.gate_report else ()) if not c.passed]
    if failing:
        feedback = "; ".join(f"{c.description}: {c.output[:500]}" for c in failing)
    else:
        feedback = "a required coding gate did not report an explicit pass"
    return task.model_copy(
        update={
            "revision": task.revision + 1,
            "goal": f"{task.goal}\n\nPrevious attempt failed ({feedback}). Fix this and retry.",
        }
    )


class BestOfNSearch:
    """`CandidateSearch` v2 — Best-of-N with sequential repair, early pruning, and rank-never-admit
    selection. `launch_mode` selects `sequential` (default, CPU-inference safe) or `parallel`
    (bounded by inference capacity, not just sandbox capacity — see `max_concurrent`)."""

    def __init__(
        self,
        *,
        worktree_manager: WorktreeManager,
        executor: CandidateExecutor,
        scorer: CandidateScorer,
        config: SearchConfig,
        bus: EventEmitter | None = None,
        max_concurrent: int = 1,
    ) -> None:
        self._worktree_manager = worktree_manager
        self._executor = executor
        self._scorer = scorer
        self._config = config
        self._bus = bus
        #: Upper bound on simultaneous candidates under `launch_mode="parallel"` — the
        #: composition root computes this as `min(governor.max_concurrent_sandboxes,
        #: tier.max_concurrent_requests)`, so a single-threaded local Ollama tier never gets more
        #: concurrent launches than it can actually serve. Unused under `"sequential"`.
        self._max_concurrent = max(1, max_concurrent)
        #: State propose() accumulates for the same run — evaluate()/select()/score() take only
        #: a `branch_id`, per the `CandidateSearch` v2 Protocol shape, so this is where the
        #: context that shape omits (task, gate reports, reviews) actually lives.
        self._outcomes: dict[str, CandidateOutcome] = {}
        self._tasks: dict[str, TaskSpec] = {}

    async def _run_one_candidate(
        self, task: TaskSpec, context: RunContext, branch_id: str, *, temperature: float | None
    ) -> CandidateOutcome:
        base_commit = context.base_commit or ""
        current_task = task
        round_ = 0
        outcome = await self._executor.execute(
            current_task,
            context,
            branch_id=branch_id,
            base_commit=base_commit,
            temperature=temperature,
            repair_round=round_,
        )

        # `prune_on_first_gate_fail`: cheap profile — skip further repair after the first
        # failed attempt. Worktree release is independent (always in `_run_and_release_one`).
        if (
            self._config.prune_on_first_gate_fail
            and outcome.gate_report is not None
            and not outcome.gate_report.admitted
        ):
            return outcome

        while (
            outcome.gate_report is not None
            and not outcome.gate_report.admitted
            and round_ < self._config.max_repair_rounds
            and not should_escalate(
                failures=round_ + 1,
                files_changed=outcome.files_changed,
                diff_lines=outcome.diff_lines,
                config=self._config,
            )
        ):
            round_ += 1
            current_task = _revise_with_feedback(current_task, outcome)
            outcome = await self._executor.execute(
                current_task,
                context,
                branch_id=branch_id,
                base_commit=base_commit,
                temperature=temperature,
                repair_round=round_,
            )

        return outcome

    def distinct_candidates(self, branch_ids: list[str]) -> int:
        """Count of distinct `git diff` digests among `branch_ids` — candidates whose diffs are
        byte-identical count once. Concrete-class-only (not on `CandidateSearch`): a caller that
        only holds the port type has no way to ask "were these candidates actually different
        answers", and the `CandidateSearch` v2 Protocol has no room to add it without a version
        bump nothing else needs yet."""
        digests = {self._outcomes[b].diff_digest for b in branch_ids if b in self._outcomes}
        return len(digests)

    def batch_cost(self, branch_ids: list[str]) -> CostSummary:
        """Summed cost of **every** candidate in the batch, not just the winner.

        Best-of-N pays for all N attempts to keep one. Reporting only the selected candidate's
        cost would make BoN look free next to single-shot and turn the exit gate's
        cost-per-resolved-task comparison into a fiction — the whole point of that metric is
        that a pass-rate win bought at N× the price is a cost loss, not a win. Concrete-class
        only, like `diversity_ratio`: the `CandidateSearch` Protocol has no cost surface.
        """
        outcomes = [self._outcomes[b] for b in branch_ids if b in self._outcomes]
        costs = [o.cost for o in outcomes if o.cost is not None]
        return CostSummary(
            usd=sum(c.usd for c in costs),
            input_tokens=sum(c.input_tokens for c in costs),
            output_tokens=sum(c.output_tokens for c in costs),
            # Wall clock sums across candidates under `sequential` (they really did run one
            # after another). Under `parallel` this over-reports elapsed time; it is the
            # honest *compute* total either way, which is what a cost comparison wants.
            wall_clock_s=sum(c.wall_clock_s for c in costs),
            model_calls=sum(c.model_calls for c in costs),
        )

    def diversity_ratio(self, branch_ids: list[str]) -> float:
        """`distinct_candidates / N`. A ratio at or near `1/N` means the candidate temperature
        ladder (`SearchConfig.candidate_temperatures`) produced one answer sampled N times, not N
        different answers — Best-of-N degenerates to single-shot at N× cost, and any pass-rate
        delta measured against this batch is a sampling artifact, not a search result. This is a
        validity precondition on the v2-S4 exit gate, not a score."""
        if not branch_ids:
            return 0.0
        return self.distinct_candidates(branch_ids) / len(branch_ids)

    async def propose(self, task: TaskSpec, context: RunContext, n: int) -> list[str]:
        """Runs all `n` candidates to completion and releases each worktree once its outcome is
        captured — nothing later needs the live worktree, since `CandidateOutcome` already
        carries the gate report, cost, and diff digest. Applying the eventual winner's diff to a
        shared base is `IntegrationStep`'s job (v2-S7), not this port's — v2-S4 measures
        Best-of-N, it does not yet merge it.

        `launch_mode` selects the schedule; pruning, repair, and ranking are identical either way.
        """
        branch_ids = [f"{task.task_id}-c{i}-{uuid.uuid4().hex[:6]}" for i in range(n)]
        for branch_id in branch_ids:
            self._tasks[branch_id] = task

        if self._config.launch_mode == "parallel":
            await self._propose_parallel(task, context, branch_ids)
        else:
            await self._propose_sequential(task, context, branch_ids)

        return branch_ids

    def _temperature_for(self, i: int) -> float:
        temperatures = self._config.candidate_temperatures or (0.0,)
        return temperatures[i % len(temperatures)]

    async def _run_and_release_one(
        self, task: TaskSpec, context: RunContext, i: int, branch_id: str
    ) -> CandidateOutcome:
        """One candidate's full lifecycle — propose event, execute (with repair), gate event,
        release, release event. Shared by both launch strategies so they differ only in
        scheduling, never in what happens to an individual candidate."""
        if self._bus is not None:
            await self._bus.emit(
                CandidateProposed(
                    run_id=context.run_id, branch_id=branch_id, strategy="best_of_n", budget_usd=0.0
                )
            )

        temperature = self._temperature_for(i)
        try:
            outcome = await self._run_one_candidate(task, context, branch_id, temperature=temperature)
        finally:
            # Shielded: a sibling admitting cleanly under `cancel_on_clean_admit` cancels this
            # candidate mid-flight, but the worktree it already allocated must still be released
            # — an interrupted release is exactly the worktree-leak failure mode the exit gate
            # tests for.
            with anyio.CancelScope(shield=True):
                await self._worktree_manager.release(branch_id)

        self._outcomes[branch_id] = outcome
        if self._bus is not None and outcome.gate_report is not None:
            await self._bus.emit(GateEvaluated(run_id=context.run_id, gate_report=outcome.gate_report))
        disposition = "admitted" if outcome.gate_report and outcome.gate_report.admitted else "released"
        if self._bus is not None:
            await self._bus.emit(
                WorktreeReleased(run_id=context.run_id, branch_id=branch_id, disposition=disposition)
            )
        return outcome

    async def _propose_sequential(self, task: TaskSpec, context: RunContext, branch_ids: list[str]) -> None:
        for i, branch_id in enumerate(branch_ids):
            await self._run_and_release_one(task, context, i, branch_id)

    async def _propose_parallel(self, task: TaskSpec, context: RunContext, branch_ids: list[str]) -> None:
        """Candidates launch concurrently, bounded by `max_concurrent` and staggered by
        `stagger_s`; if `cancel_on_clean_admit` and a candidate admits cleanly, the remaining
        launches are cancelled — "bandit-flavored, but deterministic policy", per
        `docs/rationale/reviews/next_gen_architecture_specs.md` §4.
        """
        limiter = anyio.CapacityLimiter(self._max_concurrent)

        async def _worker(i: int, branch_id: str, scope: anyio.CancelScope) -> None:
            # Sleep *before* acquiring the limiter slot — staggering is meant to spread launch
            # starts out, not to hold a scarce inference-capacity slot idle while waiting to
            # start, which would shrink effective concurrency below `max_concurrent`.
            if self._config.stagger_s > 0:
                await anyio.sleep(i * self._config.stagger_s)
            async with limiter:
                outcome = await self._run_and_release_one(task, context, i, branch_id)
                if (
                    self._config.cancel_on_clean_admit
                    and outcome.gate_report is not None
                    and outcome.gate_report.admitted
                ):
                    scope.cancel()

        with anyio.CancelScope() as scope:
            async with anyio.create_task_group() as tg:
                for i, branch_id in enumerate(branch_ids):
                    tg.start_soon(_worker, i, branch_id, scope)

    async def evaluate(self, branch_id: str) -> GateReport | None:
        outcome = self._outcomes.get(branch_id)
        return outcome.gate_report if outcome else None

    async def select(self, branch_ids: list[str]) -> str:
        """Rank-never-admit, structurally: filters to the admitted subset first (if any exist),
        ranks only *within* that subset, and falls back to the full pool only when nothing
        admitted — recording which case fired in `CandidateSelected.selection_basis` so the
        contract test (and any consumer) can see the decision, not just the winner.
        """
        if not branch_ids:
            raise ValueError("select() called with no candidates")

        def _is_admitted(branch_id: str) -> bool:
            outcome = self._outcomes.get(branch_id)
            return outcome is not None and outcome.gate_report is not None and outcome.gate_report.admitted

        admitted = [b for b in branch_ids if _is_admitted(b)]
        pool = admitted if admitted else branch_ids
        selection_basis = "admitted_ranked" if admitted else "no_admitted_candidate_best_effort"

        best_branch = pool[0]
        best_score = -1.0
        for branch_id in pool:
            outcome = self._outcomes.get(branch_id)
            if outcome is None:
                continue
            task = self._tasks.get(branch_id)
            if task is None:
                continue
            review = await self._scorer.score(task, outcome)
            if review.score > best_score:
                best_score = review.score
                best_branch = branch_id

        run_id = next(
            (self._outcomes[b].run_id for b in branch_ids if b in self._outcomes),
            branch_ids[0],
        )
        winning_outcome = self._outcomes.get(best_branch)
        if self._bus is not None and winning_outcome is not None and winning_outcome.gate_report is not None:
            # `CandidateSelected.gate_report` is required — a `GateReport` is never emitted
            # empty (domain/events.py), so a candidate with no gate report at all (e.g. an
            # allocate failure) is a valid winner in the "nothing admitted" fallback case, but
            # produces no event rather than a fabricated one.
            await self._bus.emit(
                CandidateSelected(
                    run_id=run_id,
                    branch_id=best_branch,
                    gate_report=winning_outcome.gate_report,
                    selection_basis=selection_basis,
                    diversity_ratio=self.diversity_ratio(branch_ids),
                )
            )
        return best_branch

    async def score(self, task: TaskSpec, diff: str, branch_id: str) -> ReviewReport:
        outcome = self._outcomes.get(branch_id)
        if outcome is None:
            # No cached outcome (e.g. `score()` called standalone) — score a synthetic outcome
            # from the diff alone rather than raising, since the Protocol promises this method
            # always returns a rank, never an error, for any branch_id a caller names.
            outcome = CandidateOutcome(
                branch_id=branch_id,
                run_id="",
                worktree_ref=branch_id,
                diff_digest=hashlib.sha256(diff.encode()).hexdigest(),
            )
        review = await self._scorer.score(task, outcome)
        if self._bus is not None:
            await self._bus.emit(ReviewCompleted(run_id=outcome.run_id or branch_id, review=review))
        return review
