"""Benchmark reporter module for rendering Markdown and JSON reports.

Format follows `docs/06-guides-and-patterns/benchmark-curation.md`'s report template: resolved
count with variance across repetitions, cost/success, wall/success, cache-hit rate, and a
gate-failure breakdown — not just a bare pass rate. `tests_unmodified != 0` is a validity
precondition, not a score: a run with any unmodified-test-gate failure signals grader tampering
and the report says so explicitly rather than folding it into the headline number.
"""

from __future__ import annotations

import json
import statistics as pystats
from collections import Counter, defaultdict

from sagiha.domain.benchmark import BenchmarkRun, ComparisonResult, NoiseFloor
from sagiha.e0.statistics import StatisticalAnalyzer


def _per_task_pass_rates(run: BenchmarkRun) -> dict[str, list[bool]]:
    by_task: dict[str, list[bool]] = defaultdict(list)
    for result in run.results:
        by_task[result.task_id].append(result.resolved)
    return by_task


def cost_per_resolved_task(run: BenchmarkRun) -> float | None:
    """Total USD spent across **all** attempts divided by the number that resolved.

    Denominator is resolved tasks, numerator is every task's cost including the failures —
    that is what a resolved task actually costs you. `None` when nothing resolved (an infinite
    cost is not a number to publish) or when no result carried a cost at all.

    This is the exit gate's cost-normalized comparison: a pass-rate win bought at a
    cost-per-resolved-task loss is reported as a cost loss, not a win.
    """
    costs = [r.cost.usd for r in run.results if r.cost is not None]
    if not costs:
        return None
    resolved = sum(1 for r in run.results if r.resolved)
    if resolved == 0:
        return None
    return sum(costs) / resolved


def _mean_diversity_ratio(run: BenchmarkRun) -> float | None:
    ratios = [r.diversity_ratio for r in run.results if r.diversity_ratio is not None]
    return sum(ratios) / len(ratios) if ratios else None


def _resolved_mean_std(run: BenchmarkRun) -> tuple[float, float]:
    """Mean resolved count per task and its stddev across repetitions (k >= 3 for a real sigma)."""
    by_task = _per_task_pass_rates(run)
    per_task_means = [sum(v) / len(v) for v in by_task.values()]
    if not per_task_means:
        return 0.0, 0.0
    mean = sum(per_task_means)
    std = pystats.pstdev(per_task_means) if len(per_task_means) > 1 else 0.0
    return mean, std


class BenchmarkReporter:
    """Renders E0 benchmark results as Markdown reports or structured JSON."""

    @staticmethod
    def verdict(
        treatment: BenchmarkRun,
        control: BenchmarkRun,
        comparison: ComparisonResult,
    ) -> str:
        """The exit gate's pass/fail sentence, computed rather than asserted by a human.

        Encodes the honest-negative clause from `sprint_v2_s4_options.md` §6 literally: a
        treatment that does not beat the floor is a NEGATIVE, and so is one that wins on pass
        rate while losing on cost-per-resolved-task. Both outcomes ship as a published number
        and a default-off feature — which is only possible if the tool says so plainly instead
        of leaving the reader to notice the cost column.
        """
        if comparison.beats_noise_floor is None:
            return (
                "VERDICT: INDETERMINATE — no honest noise floor was available, so the delta has "
                "nothing to beat. Not a win and not a loss; re-run with a computable A/A floor."
            )

        t_cost = cost_per_resolved_task(treatment)
        c_cost = cost_per_resolved_task(control)
        diversity = _mean_diversity_ratio(treatment)
        n_candidates = next((r.candidates for r in treatment.results if r.candidates), None)

        # Diversity is a *validity precondition*, checked before the delta is believed at all:
        # if candidates were one answer sampled N times, the delta is a sampling artifact.
        if diversity is not None and n_candidates and n_candidates > 1:
            floor_ratio = 1.0 / n_candidates
            if diversity <= floor_ratio + 1e-9:
                return (
                    f"VERDICT: INVALID — diversity_ratio {diversity:.3f} is at the {floor_ratio:.3f} "
                    f"floor (1/N for N={n_candidates}). The candidates were one answer sampled "
                    f"{n_candidates} times, so any delta here is a sampling artifact, not a search result."
                )

        if not comparison.beats_noise_floor:
            return (
                f"VERDICT: NEGATIVE — delta {comparison.delta_pass_rate:+.4f} does not clear the "
                "noise floor. Per the honest-negative clause, publish this number and ship the "
                "treatment OFF by default (search.enabled = false)."
            )

        if t_cost is not None and c_cost is not None and t_cost > c_cost:
            return (
                f"VERDICT: COST LOSS — pass rate improved by {comparison.delta_pass_rate:+.4f} "
                f"beyond the floor, but cost-per-resolved-task rose ${c_cost:.4f} -> ${t_cost:.4f}. "
                "A pass-rate win at a cost-per-resolved-task loss is reported as a cost loss, not a win."
            )

        return f"VERDICT: POSITIVE — delta {comparison.delta_pass_rate:+.4f} beats the noise floor" + (
            f" at equal-or-better cost (${t_cost:.4f}/resolved)." if t_cost is not None else "."
        )

    @staticmethod
    def render_markdown(
        run: BenchmarkRun,
        *,
        noise_floor: NoiseFloor | None = None,
        comparison: ComparisonResult | None = None,
        control: BenchmarkRun | None = None,
        suite_version: str = "",
        harness_version: str = "",
        model: str = "",
    ) -> str:
        pass_rate = StatisticalAnalyzer.compute_pass_rate(run)
        pct = pass_rate * 100.0
        resolved_mean, resolved_std = _resolved_mean_std(run)
        n_tasks = len(_per_task_pass_rates(run))

        costs = [r.cost.usd for r in run.results if r.resolved and r.cost is not None]
        walls = [r.wall_clock_s for r in run.results if r.resolved]
        cache_hits = [r.cache_hit for r in run.results if r.cache_hit is not None]
        gate_failures = Counter(r.gate_failure_kind for r in run.results if r.gate_failure_kind)
        # tests_unmodified is a validity precondition (grader tampering), never folded into the
        # headline pass rate as though it were an ordinary failure mode.
        tests_unmodified_failures = gate_failures.get("tests_unmodified", 0)

        header = f"Suite: {run.suite_id}"
        if suite_version:
            header += f" {suite_version}"
        header += f" ({n_tasks} tasks)"
        if model:
            header += f" · model {model}"
        if harness_version:
            header += f" · harness {harness_version}"

        lines = [
            "# 📊 SAGIHA E0 Benchmark Report",
            "",
            header,
            f"**Run ID:** `{run.run_id}` · **Agent ID:** `{run.agent_id}`",
            "",
            f"**Resolved:** {resolved_mean:.1f} / {n_tasks}  ({pct:.1f}% ± {resolved_std * 100:.1f}pp)"
            if n_tasks
            else "**Resolved:** 0 / 0",
        ]
        if costs:
            lines.append(
                f"**Cost/success:** ${sum(costs) / len(costs):.2f} ± "
                f"${pystats.pstdev(costs) if len(costs) > 1 else 0.0:.2f}"
            )
        if walls:
            avg_wall = sum(walls) / len(walls)
            lines.append(f"**Wall/success:** {avg_wall:.1f}s")
        if cache_hits:
            lines.append(f"**Cache hit:** {sum(cache_hits) / len(cache_hits):.2f}")
        lines.append("")

        if gate_failures:
            lines.append("## Gate Failures")
            for name, count in sorted(gate_failures.items()):
                lines.append(f"- `{name}`: {count}")
            lines.append("")
            if tests_unmodified_failures:
                lines.append(
                    f"> **{tests_unmodified_failures} run(s) failed `tests_unmodified`** — "
                    "a validity precondition, not a score. These indicate grader tampering, "
                    "not ordinary task difficulty, and should be investigated before trusting "
                    "the headline resolved rate."
                )
                lines.append("")

        if noise_floor:
            ci_lo, ci_hi = noise_floor.confidence_interval
            lines.extend(
                [
                    "## 📐 Noise Floor Calibration (A/A)",
                    f"- Mean Delta: `{noise_floor.mean_delta:.4f}`",
                    f"- {int((1 - noise_floor.alpha) * 100)}% Bootstrap CI: "
                    f"`[{ci_lo:.4f}, {ci_hi:.4f}]` (seed={noise_floor.seed}, n={noise_floor.n_tasks})",
                    "",
                ]
            )
        if comparison:
            p_str = f"{comparison.p_value:.4f}" if comparison.p_value is not None else "N/A"
            adj_str = (
                f"{comparison.adjusted_p_value:.4f}" if comparison.adjusted_p_value is not None else "N/A"
            )
            beats_str = (
                "N/A (not computed)"
                if comparison.beats_noise_floor is None
                else str(comparison.beats_noise_floor)
            )
            lines.extend(
                [
                    "## ⚖️ Paired Comparison",
                    f"- Delta Pass Rate: `{comparison.delta_pass_rate:.4f}`",
                    f"- p-value ({comparison.method or 'n/a'}): `{p_str}` "
                    f"(discordant pairs: {comparison.n_discordant})",
                    f"- Holm-adjusted p-value: `{adj_str}`",
                    f"- Beats Noise Floor: `{beats_str}`",
                ]
            )
            if control is not None:
                t_cost = cost_per_resolved_task(run)
                c_cost = cost_per_resolved_task(control)
                lines.append(
                    "- Cost per resolved task: "
                    f"control `{'n/a' if c_cost is None else f'${c_cost:.4f}'}` -> "
                    f"treatment `{'n/a' if t_cost is None else f'${t_cost:.4f}'}`"
                )
                diversity = _mean_diversity_ratio(run)
                if diversity is not None:
                    n_candidates = next((r.candidates for r in run.results if r.candidates), None)
                    floor_note = f" (1/N floor = {1.0 / n_candidates:.3f})" if n_candidates else ""
                    lines.append(f"- Mean `diversity_ratio`: `{diversity:.3f}`{floor_note}")
            lines.append("")
            if control is not None:
                lines.extend([BenchmarkReporter.verdict(run, control, comparison), ""])

        lines.extend(["## Tasks", ""])
        for task_id, outcomes in sorted(_per_task_pass_rates(run).items()):
            resolved_frac = sum(outcomes) / len(outcomes)
            status = (
                "✅ PASSED" if resolved_frac == 1.0 else ("❌ FAILED" if resolved_frac == 0.0 else "🟡 FLAKY")
            )
            suffix = f" ({sum(outcomes)}/{len(outcomes)})" if len(outcomes) > 1 else ""
            lines.append(f"- `{task_id}`: {status}{suffix}")

        return "\n".join(lines)

    @staticmethod
    def render_json(
        run: BenchmarkRun,
        noise_floor: NoiseFloor | None = None,
        comparison: ComparisonResult | None = None,
        control: BenchmarkRun | None = None,
    ) -> str:
        pass_rate = StatisticalAnalyzer.compute_pass_rate(run)
        gate_failures = Counter(r.gate_failure_kind for r in run.results if r.gate_failure_kind)
        costs = [r.cost.usd for r in run.results if r.resolved and r.cost is not None]
        cache_hits = [r.cache_hit for r in run.results if r.cache_hit is not None]
        data = {
            "run_id": run.run_id,
            "suite_id": run.suite_id,
            "agent_id": run.agent_id,
            "pass_rate": pass_rate,
            "n_tasks": len(_per_task_pass_rates(run)),
            "n_results": len(run.results),
            "cost_per_success_usd": (sum(costs) / len(costs)) if costs else None,
            "cost_per_resolved_task_usd": cost_per_resolved_task(run),
            "diversity_ratio": _mean_diversity_ratio(run),
            "cache_hit_rate": (sum(cache_hits) / len(cache_hits)) if cache_hits else None,
            "gate_failures": dict(gate_failures),
            "results": [r.model_dump(mode="json") for r in run.results],
            "noise_floor": noise_floor.model_dump(mode="json") if noise_floor else None,
            "comparison": comparison.model_dump(mode="json") if comparison else None,
            "control": (
                {
                    "run_id": control.run_id,
                    "agent_id": control.agent_id,
                    "pass_rate": StatisticalAnalyzer.compute_pass_rate(control),
                    "cost_per_resolved_task_usd": cost_per_resolved_task(control),
                }
                if control is not None
                else None
            ),
            "verdict": (
                BenchmarkReporter.verdict(run, control, comparison)
                if control is not None and comparison is not None
                else None
            ),
        }
        return json.dumps(data, indent=2)
