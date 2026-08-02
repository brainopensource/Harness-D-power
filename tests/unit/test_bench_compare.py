"""Proving tests for the v2-S4 `bench --compare` arm comparison and its verdict rules.

The exit gate's claim — "BoN beats single-shot by X ± σ over a floor of Y" — is only defensible
if the tool that emits it refuses to call a non-win a win. `BenchmarkReporter.verdict` encodes
the honest-negative clause from `docs/implementation/sprint_v2_s4_options.md` §6 as code rather
than as a paragraph a reader is trusted to apply, and these tests pin each branch of it.
"""

from __future__ import annotations

from sagiha.domain.benchmark import BenchmarkResult, BenchmarkRun, NoiseFloor
from sagiha.domain.work import CostSummary
from sagiha.e0.reporter import BenchmarkReporter, cost_per_resolved_task, per_task_cost_stats
from sagiha.e0.statistics import StatisticalAnalyzer


def _cost(usd: float) -> CostSummary:
    return CostSummary(usd=usd, input_tokens=0, output_tokens=0, wall_clock_s=0.0, model_calls=1)


def _run(
    agent_id: str,
    rows: list[tuple[str, bool, float]],
    *,
    strategy: str = "single_shot",
    diversity: float | None = None,
    candidates: int | None = None,
) -> BenchmarkRun:
    return BenchmarkRun(
        run_id=f"{agent_id}-run",
        suite_id="s0-core",
        agent_id=agent_id,
        results=tuple(
            BenchmarkResult(
                task_id=t,
                agent_id=agent_id,
                resolved=r,
                cost=_cost(usd),
                strategy=strategy,
                diversity_ratio=diversity,
                candidates=candidates,
            )
            for t, r, usd in rows
        ),
    )


def _floor(mean_delta: float, ci_hi: float, n_tasks: int = 4) -> NoiseFloor:
    return NoiseFloor(
        manifest_id="s0-core",
        runs_per_task=2,
        mean_delta=mean_delta,
        confidence_interval=(-ci_hi, ci_hi),
        alpha=0.05,
        k_runs=2,
        n_tasks=n_tasks,
        seed=0,
    )


def test_cost_per_resolved_task_counts_failed_attempts_in_the_numerator() -> None:
    """A resolved task costs what you spent to get it, including the runs that failed. Dividing
    only successful-run cost by successes would make an expensive, flaky arm look cheap."""
    run = _run("a", [("t1", True, 1.0), ("t2", False, 3.0)])
    assert cost_per_resolved_task(run) == 4.0  # $4 total / 1 resolved, not $1/1


def test_per_task_cost_stats_counts_every_result_not_just_resolved() -> None:
    run = BenchmarkRun(
        run_id="r",
        suite_id="s0-core",
        agent_id="a",
        results=(
            BenchmarkResult(
                task_id="t1",
                agent_id="a",
                resolved=True,
                cost=CostSummary(usd=1.0, input_tokens=0, output_tokens=0, wall_clock_s=0.0, model_calls=2),
                wall_clock_s=10.0,
            ),
            BenchmarkResult(
                task_id="t2",
                agent_id="a",
                resolved=False,
                cost=CostSummary(usd=3.0, input_tokens=0, output_tokens=0, wall_clock_s=0.0, model_calls=4),
                wall_clock_s=20.0,
            ),
        ),
    )
    stats = per_task_cost_stats(run)
    assert stats is not None
    assert stats["usd"]["mean"] == 2.0  # (1.0 + 3.0) / 2 tasks, not just the resolved one
    assert stats["wall_clock_s"]["mean"] == 15.0
    assert stats["model_calls"]["mean"] == 3.0


def test_per_task_cost_stats_none_when_no_result_has_cost() -> None:
    run = BenchmarkRun(
        run_id="r",
        suite_id="s0-core",
        agent_id="a",
        results=(BenchmarkResult(task_id="t1", agent_id="a", resolved=True, cost=None),),
    )
    assert per_task_cost_stats(run) is None


def test_cost_per_resolved_task_is_none_when_nothing_resolved() -> None:
    run = _run("a", [("t1", False, 1.0)])
    assert cost_per_resolved_task(run) is None


def test_verdict_indeterminate_without_a_noise_floor() -> None:
    control = _run("c", [("t1", False, 1.0)])
    treatment = _run("t", [("t1", True, 1.0)], strategy="bon")
    comp = StatisticalAnalyzer.compare_runs(control, treatment)  # no floor supplied
    assert comp.beats_noise_floor is None
    assert "INDETERMINATE" in BenchmarkReporter.verdict(treatment, control, comp)


def test_verdict_negative_when_delta_does_not_clear_the_floor() -> None:
    """The honest-negative clause: below the floor, publish the number and ship it off."""
    control = _run("c", [("t1", False, 1.0), ("t2", True, 1.0), ("t3", True, 1.0), ("t4", True, 1.0)])
    treatment = _run(
        "t",
        [("t1", True, 1.0), ("t2", True, 1.0), ("t3", True, 1.0), ("t4", True, 1.0)],
        strategy="bon",
    )
    # A floor wide enough to swallow a 1-of-4 improvement.
    comp = StatisticalAnalyzer.compare_runs(control, treatment, noise_floor=_floor(0.5, 0.9))
    assert comp.beats_noise_floor is False
    verdict = BenchmarkReporter.verdict(treatment, control, comp)
    assert "NEGATIVE" in verdict
    assert "OFF by default" in verdict


def test_verdict_reports_cost_loss_when_pass_rate_wins_but_cost_rises() -> None:
    """The gate's cost-normalized rule, verbatim: a pass-rate win at a cost-per-resolved-task
    loss is a cost loss. This is the branch Best-of-N is most likely to land on, since it pays
    for N candidates to keep one."""
    control = _run("c", [("t1", False, 1.0), ("t2", False, 1.0), ("t3", True, 1.0), ("t4", True, 1.0)])
    treatment = _run(
        "t",
        [("t1", True, 9.0), ("t2", True, 9.0), ("t3", True, 9.0), ("t4", True, 9.0)],
        strategy="bon",
        diversity=1.0,
        candidates=3,
    )
    comp = StatisticalAnalyzer.compare_runs(control, treatment, noise_floor=_floor(0.0, 0.05))
    assert comp.beats_noise_floor is True
    verdict = BenchmarkReporter.verdict(treatment, control, comp)
    assert "COST LOSS" in verdict


def test_verdict_invalid_when_diversity_ratio_sits_at_the_one_over_n_floor() -> None:
    """Diversity is a validity precondition, checked before the delta is believed at all: N
    identical candidates means BoN paid N× for single-shot's answer, so any delta is a
    sampling artifact rather than a search result."""
    control = _run("c", [("t1", False, 1.0), ("t2", False, 1.0), ("t3", True, 1.0), ("t4", True, 1.0)])
    treatment = _run(
        "t",
        [("t1", True, 1.0), ("t2", True, 1.0), ("t3", True, 1.0), ("t4", True, 1.0)],
        strategy="bon",
        diversity=1 / 3,  # all three candidates produced the same diff
        candidates=3,
    )
    comp = StatisticalAnalyzer.compare_runs(control, treatment, noise_floor=_floor(0.0, 0.05))
    verdict = BenchmarkReporter.verdict(treatment, control, comp)
    assert "INVALID" in verdict
    assert "sampling artifact" in verdict


def test_verdict_positive_only_when_it_beats_the_floor_at_no_worse_cost() -> None:
    control = _run("c", [("t1", False, 2.0), ("t2", False, 2.0), ("t3", True, 2.0), ("t4", True, 2.0)])
    treatment = _run(
        "t",
        [("t1", True, 1.0), ("t2", True, 1.0), ("t3", True, 1.0), ("t4", True, 1.0)],
        strategy="bon",
        diversity=1.0,
        candidates=3,
    )
    comp = StatisticalAnalyzer.compare_runs(control, treatment, noise_floor=_floor(0.0, 0.05))
    verdict = BenchmarkReporter.verdict(treatment, control, comp)
    assert "POSITIVE" in verdict


def test_render_markdown_publishes_cost_and_diversity_when_a_control_is_supplied() -> None:
    """The exit gate requires cost-per-resolved-task published *alongside* pass rate, and
    `diversity_ratio` printable. Both were computable but unreported before this."""
    control = _run("c", [("t1", False, 2.0), ("t2", True, 2.0)])
    treatment = _run(
        "t", [("t1", True, 1.0), ("t2", True, 1.0)], strategy="bon", diversity=0.667, candidates=3
    )
    comp = StatisticalAnalyzer.compare_runs(control, treatment, noise_floor=_floor(0.0, 0.05))
    md = BenchmarkReporter.render_markdown(
        treatment, noise_floor=_floor(0.0, 0.05), comparison=comp, control=control
    )
    assert "Cost per resolved task" in md
    assert "diversity_ratio" in md
    assert "VERDICT:" in md


def test_comparison_result_carries_the_arms_it_compared() -> None:
    """Two runs of the same arm must never be presentable as a treatment effect — the arm is
    recorded per result so a report can show what was actually compared."""
    control = _run("sagiha-single_shot", [("t1", False, 1.0)])
    treatment = _run("sagiha-bon", [("t1", True, 1.0)], strategy="bon")
    assert {r.strategy for r in control.results} == {"single_shot"}
    assert {r.strategy for r in treatment.results} == {"bon"}
    comp = StatisticalAnalyzer.compare_runs(control, treatment)
    assert comp.control_agent_id == "sagiha-single_shot"
    assert comp.treatment_agent_id == "sagiha-bon"
