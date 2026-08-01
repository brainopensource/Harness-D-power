"""Regression test for `k > 1` repetition handling across `run_suite(k=...)` and
`e0.statistics.paired_deltas`.

`BenchmarkRunner.run_suite` appends `k` results per task into one flat `BenchmarkRun.results`
tuple. `e0.statistics._task_outcomes` must preserve every repetition (not collapse to the last
one via a `task_id -> bool` dict) so `paired_deltas`'s sample agrees with `compute_pass_rate`,
which correctly averages every repetition. This was flagged in review as a real defect (H5-
adjacent) and has since been fixed — this test pins the fix rather than proving the bug.
"""

from __future__ import annotations

from sagiha.domain.benchmark import BenchmarkResult, BenchmarkRun
from sagiha.e0.statistics import StatisticalAnalyzer, paired_deltas


def _repeated_run(run_id: str, agent_id: str, per_task_outcomes: dict[str, list[bool]]) -> BenchmarkRun:
    results = []
    for task_id, outcomes in per_task_outcomes.items():
        for resolved in outcomes:
            results.append(BenchmarkResult(task_id=task_id, agent_id=agent_id, resolved=resolved))
    return BenchmarkRun(run_id=run_id, suite_id="s1", agent_id=agent_id, results=tuple(results))


def test_paired_deltas_reflects_every_repetition_not_just_the_last() -> None:
    """k=3 repetitions of one task: control resolves 2/3, treatment resolves 0/3."""
    control = _repeated_run("r1", "a1", {"t1": [True, True, False]})
    treatment = _repeated_run("r2", "a2", {"t1": [False, False, False]})

    rate_control = StatisticalAnalyzer.compute_pass_rate(control)
    rate_treatment = StatisticalAnalyzer.compute_pass_rate(treatment)
    assert rate_control == 2 / 3
    assert rate_treatment == 0.0

    deltas = paired_deltas(control, treatment)
    assert len(deltas) == 3
    assert sum(deltas) / len(deltas) == rate_treatment - rate_control


def test_paired_deltas_repetition_count_mismatch_pairs_up_to_the_shorter_run() -> None:
    control = _repeated_run("r1", "a1", {"t1": [True, True, True]})
    treatment = _repeated_run("r2", "a2", {"t1": [False]})
    deltas = paired_deltas(control, treatment)
    assert len(deltas) == 1
