"""Benchmark reporter module for rendering Markdown and JSON reports."""

from __future__ import annotations

import json

from sagiha.domain.benchmark import BenchmarkRun, ComparisonResult, NoiseFloor
from sagiha.e0.statistics import StatisticalAnalyzer


class BenchmarkReporter:
    """Renders E0 benchmark results as Markdown reports or structured JSON."""

    @staticmethod
    def render_markdown(
        run: BenchmarkRun,
        *,
        noise_floor: NoiseFloor | None = None,
        comparison: ComparisonResult | None = None,
    ) -> str:
        pass_rate = StatisticalAnalyzer.compute_pass_rate(run)
        pct = pass_rate * 100.0
        lines = [
            "# 📊 SAGIHA E0 Benchmark Report",
            "",
            f"**Run ID:** `{run.run_id}`",
            f"**Suite ID:** `{run.suite_id}`",
            f"**Agent ID:** `{run.agent_id}`",
            f"**Pass Rate:** {pct:.1f}%",
            "",
        ]
        if noise_floor:
            lines.extend(
                [
                    "## 📐 Noise Floor Calibration",
                    f"- Mean Delta: `{noise_floor.mean_delta:.4f}`",
                    "",
                ]
            )
        if comparison:
            lines.extend(
                [
                    "## ⚖️ Paired Comparison",
                    f"- Delta Pass Rate: `{comparison.delta_pass_rate:.4f}`",
                    f"- Beats Noise Floor: `{comparison.beats_noise_floor}`",
                    "",
                ]
            )
        lines.extend(
            [
                "## Tasks",
                "",
            ]
        )
        for res in run.results:
            status = "✅ PASSED" if res.resolved else "❌ FAILED"
            lines.append(f"- `{res.task_id}`: {status}")

        return "\n".join(lines)

    @staticmethod
    def render_json(
        run: BenchmarkRun,
        noise_floor: NoiseFloor | None = None,
        comparison: ComparisonResult | None = None,
    ) -> str:
        pass_rate = StatisticalAnalyzer.compute_pass_rate(run)
        data = {
            "run_id": run.run_id,
            "suite_id": run.suite_id,
            "agent_id": run.agent_id,
            "pass_rate": pass_rate,
            "results": [r.model_dump(mode="json") for r in run.results],
            "noise_floor": noise_floor.model_dump(mode="json") if noise_floor else None,
            "comparison": comparison.model_dump(mode="json") if comparison else None,
        }
        return json.dumps(data, indent=2)
