"""Fixture-backed tests for `e0.statistics` — proving tests for v2-S4 Epic S4.1a (H5).

These pin the pure-math functions against `tests/fixtures/statistics/*.json`, hand-verified
known-answer cases (see each fixture's `description`), independent of the rest of the E0 stack.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sagiha.domain.benchmark import BenchmarkResult, BenchmarkRun
from sagiha.e0.statistics import (
    StatisticalAnalyzer,
    bootstrap_ci,
    holm,
    mcnemar_exact,
    paired_deltas,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "statistics"


def _load(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text())


@pytest.mark.parametrize("case", _load("mcnemar.json")["cases"])
def test_mcnemar_exact_matches_fixture(case: dict) -> None:
    p = mcnemar_exact(case["b"], case["c"])
    assert p == pytest.approx(case["expected_p"], abs=1e-9)


@pytest.mark.parametrize("case", _load("bootstrap.json")["cases"])
def test_bootstrap_ci_matches_fixture(case: dict) -> None:
    ci = bootstrap_ci(case["deltas"], alpha=case["alpha"], iterations=case["iterations"], seed=case["seed"])
    assert ci == pytest.approx(tuple(case["expected_ci"]), abs=1e-9)


@pytest.mark.parametrize("case", _load("holm.json")["cases"])
def test_holm_matches_fixture(case: dict) -> None:
    adjusted = holm(case["pvalues"])
    assert adjusted == pytest.approx(case["expected_adjusted"], abs=1e-9)


def test_holm_is_order_preserving_and_monotonic() -> None:
    """Adjusted p-values must never decrease as rank increases (the running-max step)."""
    adjusted = holm([0.2, 0.001, 0.03, 0.001])
    sorted_by_original_pvalue = sorted(range(4), key=lambda i: [0.2, 0.001, 0.03, 0.001][i])
    running = [adjusted[i] for i in sorted_by_original_pvalue]
    assert running == sorted(running)


def _run(run_id: str, agent_id: str, task_results: list[tuple[str, bool]]) -> BenchmarkRun:
    return BenchmarkRun(
        run_id=run_id,
        suite_id="s1",
        agent_id=agent_id,
        results=tuple(BenchmarkResult(task_id=t, agent_id=agent_id, resolved=r) for t, r in task_results),
    )


def test_paired_deltas_joins_on_task_id_not_position() -> None:
    """An unpaired comparison (different task sets or out-of-order results) must not silently
    zip into a paired one — deltas are computed only over the intersection of task_ids."""
    control = _run("r1", "a1", [("t1", True), ("t2", False), ("t3", True)])
    treatment = _run("r2", "a2", [("t2", True), ("t1", True)])  # reordered, missing t3

    deltas = paired_deltas(control, treatment)
    # common = {t1, t2}, sorted -> t1: 1-1=0, t2: 1-0=1
    assert deltas == [0.0, 1.0]


def test_paired_deltas_pairs_repetitions_positionally_not_last_write_wins() -> None:
    """Repeated `task_id`s (k>1 repetitions from `run_suite(k=...)`) pair repetition-by-
    repetition, not by collapsing to the last-seen result — see `e0.statistics._task_outcomes`."""
    control = _run("r1", "a1", [("t1", True), ("t1", False)])
    treatment = _run("r2", "a2", [("t1", True), ("t1", True)])
    deltas = paired_deltas(control, treatment)
    assert deltas == [0.0, 1.0]  # rep0: 1-1=0, rep1: 1-0=1


def test_compare_runs_empty_noise_floor_never_reports_beats() -> None:
    """H5-shaped regression: an A/A run with zero pairable tasks must not manufacture a floor
    of (0.0, 0.0) that every non-empty delta trivially 'beats'. `beats_noise_floor` must stay
    `None` when the noise floor itself was not honestly computed from any task."""
    control = _run("r1", "a1", [])
    treatment = _run("r2", "a2", [])
    noise_floor = StatisticalAnalyzer.compute_noise_floor(control, treatment)
    assert noise_floor.n_tasks == 0

    real_control = _run("r3", "a1", [("t1", False), ("t2", False)])
    real_treatment = _run("r4", "a2", [("t1", True), ("t2", True)])
    comp = StatisticalAnalyzer.compare_runs(real_control, real_treatment, noise_floor=noise_floor)
    assert comp.beats_noise_floor is None, (
        "an empty A/A floor must never be treated as 'beaten' by a real delta — "
        "this is H5's fabrication reintroduced through an uncomputable noise floor"
    )
