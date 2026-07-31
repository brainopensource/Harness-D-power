"""Unit tests for `adapters/search/scoring.py` — S-0 deterministic composite (v2-S4 Epic S4.3)."""

from __future__ import annotations

import pytest

from sagiha.adapters.search.protocols import CandidateOutcome
from sagiha.adapters.search.scoring import DeterministicCompositeScorer, NullScorer, build_scorer
from sagiha.domain.config import ScoringConfig
from sagiha.domain.work import CriterionResult, GateReport, TaskSpec


def _task() -> TaskSpec:
    return TaskSpec(task_id="t1", goal="fix it", acceptance=())


def _outcome(*, criteria: tuple[CriterionResult, ...] | None, diff_lines: int = 0) -> CandidateOutcome:
    gate_report = None
    if criteria is not None:
        gate_report = GateReport(criteria=criteria)
    return CandidateOutcome(
        branch_id="b1", run_id="r1", worktree_ref="b1", gate_report=gate_report, diff_lines=diff_lines
    )


@pytest.mark.asyncio
async def test_composite_scorer_no_gate_report_scores_zero() -> None:
    scorer = DeterministicCompositeScorer(ScoringConfig())
    review = await scorer.score(_task(), _outcome(criteria=None))
    assert review.score == 0.0


@pytest.mark.asyncio
async def test_composite_scorer_all_required_passed_scores_full_pass_fraction() -> None:
    scorer = DeterministicCompositeScorer(ScoringConfig(w_pass=1.0, w_diff=0.0))
    criteria = (
        CriterionResult(description="a", check="a", passed=True, required=True),
        CriterionResult(description="b", check="b", passed=True, required=True),
    )
    review = await scorer.score(_task(), _outcome(criteria=criteria))
    assert review.score == 1.0


@pytest.mark.asyncio
async def test_composite_scorer_diff_penalty_reduces_score() -> None:
    scorer = DeterministicCompositeScorer(ScoringConfig(w_pass=1.0, w_diff=0.5), max_diff_lines=100)
    criteria = (CriterionResult(description="a", check="a", passed=True, required=True),)
    small_diff = await scorer.score(_task(), _outcome(criteria=criteria, diff_lines=10))
    large_diff = await scorer.score(_task(), _outcome(criteria=criteria, diff_lines=100))
    assert large_diff.score < small_diff.score


@pytest.mark.asyncio
async def test_composite_scorer_score_clamped_to_unit_interval() -> None:
    scorer = DeterministicCompositeScorer(ScoringConfig(w_pass=1.0, w_diff=0.0))
    criteria = (CriterionResult(description="a", check="a", passed=False, required=True),)
    review = await scorer.score(_task(), _outcome(criteria=criteria))
    assert 0.0 <= review.score <= 1.0


@pytest.mark.asyncio
async def test_null_scorer_ranks_every_candidate_identically() -> None:
    scorer = NullScorer()
    outcome_a = _outcome(criteria=(CriterionResult(description="a", check="a", passed=True, required=True),))
    outcome_b = _outcome(criteria=None)
    review_a = await scorer.score(_task(), outcome_a)
    review_b = await scorer.score(_task(), outcome_b)
    assert review_a.score == review_b.score


def test_build_scorer_composite_default() -> None:
    scorer = build_scorer(ScoringConfig(backend="composite"))
    assert isinstance(scorer, DeterministicCompositeScorer)


def test_build_scorer_null() -> None:
    scorer = build_scorer(ScoringConfig(backend="null"))
    assert isinstance(scorer, NullScorer)


def test_build_scorer_judge_requires_provider() -> None:
    with pytest.raises(ValueError, match="judge_provider"):
        build_scorer(ScoringConfig(backend="judge"))


def test_build_scorer_learned_not_implemented() -> None:
    with pytest.raises(NotImplementedError, match="v2-S6"):
        build_scorer(ScoringConfig(backend="learned"))
