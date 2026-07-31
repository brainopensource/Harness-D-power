"""Candidate scoring — S-0 through S-2 of the scoring ladder
(`docs/implementation/sprint_v2_s4_options.md` §3). `CandidateScorer` is an adapter-internal
Protocol (`adapters/search/protocols.py`), not a hexagonal port: it ranks, it never admits, and
`GateReport` — the thing that does admit — never depends on it.

Gates admit; scores rank. A candidate that fails `no_new_suppressions` is never admitted
regardless of what any scorer here returns.
"""

from __future__ import annotations

from sagiha.adapters.search.protocols import CandidateOutcome, CandidateScorer
from sagiha.domain.config import ScoringConfig
from sagiha.domain.work import ReviewReport, TaskSpec

_JUDGE_MODEL_LABEL = "deterministic-composite-v0"
_RUBRIC_VERSION = "s0"


def _pass_fraction(outcome: CandidateOutcome) -> float:
    """Fraction of required `AcceptanceCriterion`s that passed. `GateReport.criteria` already
    holds this; a candidate with no gate report at all (e.g. an allocate failure) scores 0."""
    if outcome.gate_report is None or not outcome.gate_report.criteria:
        return 0.0
    required = [c for c in outcome.gate_report.criteria if c.required]
    if not required:
        return 1.0
    return sum(1 for c in required if c.passed) / len(required)


def _diff_penalty(outcome: CandidateOutcome, *, max_diff_lines: int) -> float:
    """Normalized `[0, 1]` diff-size penalty — bigger diffs rank lower, all else equal."""
    if max_diff_lines <= 0:
        return 0.0
    return min(1.0, outcome.diff_lines / max_diff_lines)


class DeterministicCompositeScorer:
    """S-0: a pure function over `GateReport` and diff-size features already available on every
    `CandidateOutcome` — 0ms, $0, no training, fully replayable.

    `Score = w_pass·PassFraction + w_coverage·Δcoverage − w_diff·ΔDiffLength
             − w_suppression·suppression_penalty`

    Shipped default has `w_coverage = w_suppression = 0.0`, so the composite is really the
    two-term form `w_pass·PassFraction − w_diff·ΔDiff`: Δcoverage has no honest value until a
    `Toolchain` adapter exists (v2-S6), and `no_new_suppressions` is already a hard gate — scoring
    it too would double-count an admission decision that was already made.
    """

    def __init__(self, config: ScoringConfig, *, max_diff_lines: int = 1000) -> None:
        self._config = config
        self._max_diff_lines = max_diff_lines

    async def score(self, task: TaskSpec, outcome: CandidateOutcome) -> ReviewReport:
        pass_fraction = _pass_fraction(outcome)
        diff_penalty = _diff_penalty(outcome, max_diff_lines=self._max_diff_lines)
        # Δcoverage placeholder (v2-S6). Suppression penalty deliberately not derived from the
        # gate result — see the class docstring.
        delta_coverage = 0.0
        suppression_penalty = 0.0

        raw = (
            self._config.w_pass * pass_fraction
            + self._config.w_coverage * delta_coverage
            - self._config.w_diff * diff_penalty
            - self._config.w_suppression * suppression_penalty
        )
        score = max(0.0, min(1.0, raw))

        return ReviewReport(
            score=score,
            findings=(),
            judge_model=_JUDGE_MODEL_LABEL,
            rubric_version=_RUBRIC_VERSION,
        )


class NullScorer:
    """Constant-score scorer for `scoring.enabled = false` profiles — every candidate ranks
    identically, so `select()` falls back to gate admission alone (or candidate order, among
    equally-admitted candidates)."""

    async def score(self, task: TaskSpec, outcome: CandidateOutcome) -> ReviewReport:
        return ReviewReport(score=0.5, findings=(), judge_model="null-scorer", rubric_version="s0")


def build_scorer(
    config: ScoringConfig,
    *,
    max_diff_lines: int = 1000,
    judge_provider: object | None = None,
    judge_model_label: str = "",
) -> CandidateScorer:
    """Composition-time backend selection — the scoring ladder's swap point.

    `backend="judge"` and `backend="learned"` are the S-1/S-2 rungs from
    `docs/implementation/sprint_v2_s4_options.md` §3. `judge_provider`/`judge_model_label` are
    only required when `backend="judge"` — the default `"composite"` path never constructs a
    model provider, so choosing the deterministic scorer never pays a live-model construction
    cost it does not need.
    """
    if config.backend == "composite":
        return DeterministicCompositeScorer(config, max_diff_lines=max_diff_lines)
    if config.backend == "null":
        return NullScorer()
    if config.backend == "judge":
        from sagiha.adapters.search.judge import LocalJudgeScorer

        if judge_provider is None:
            raise ValueError("scoring backend 'judge' requires judge_provider")
        return LocalJudgeScorer(config, model_provider=judge_provider, model_label=judge_model_label)  # type: ignore[arg-type]
    raise NotImplementedError(
        f"scoring backend {config.backend!r} — v2-S6+, see docs/08-decisions/0025-candidate-search-seams.md"
    )
