"""Unit tests for statistical analyzer and report generator."""

from __future__ import annotations

from sagiha.domain.benchmark import BenchmarkResult, BenchmarkRun, NoiseFloor
from sagiha.e0.reporter import BenchmarkReporter
from sagiha.e0.statistics import StatisticalAnalyzer


def test_compute_pass_rate() -> None:
    res1 = BenchmarkResult(task_id="t1", agent_id="a1", resolved=True)
    res2 = BenchmarkResult(task_id="t2", agent_id="a1", resolved=False)
    run = BenchmarkRun(run_id="r1", suite_id="s1", agent_id="a1", results=(res1, res2))

    pass_rate = StatisticalAnalyzer.compute_pass_rate(run)
    assert pass_rate == 0.5


def test_compute_noise_floor() -> None:
    res1_a = BenchmarkResult(task_id="t1", agent_id="a1", resolved=True)
    res2_a = BenchmarkResult(task_id="t2", agent_id="a1", resolved=False)
    run_a = BenchmarkRun(run_id="r1", suite_id="s1", agent_id="a1", results=(res1_a, res2_a))

    res1_b = BenchmarkResult(task_id="t1", agent_id="a1", resolved=True)
    res2_b = BenchmarkResult(task_id="t2", agent_id="a1", resolved=True)
    run_b = BenchmarkRun(run_id="r2", suite_id="s1", agent_id="a1", results=(res1_b, res2_b))

    noise_floor = StatisticalAnalyzer.compute_noise_floor(run_a, run_b)
    assert isinstance(noise_floor, NoiseFloor)
    assert noise_floor.manifest_id == "s1"
    assert noise_floor.runs_per_task == 2
    assert noise_floor.mean_delta == 0.5


def test_compare_runs() -> None:
    res1_a = BenchmarkResult(task_id="t1", agent_id="a1", resolved=False)
    run_control = BenchmarkRun(run_id="r1", suite_id="s1", agent_id="a1", results=(res1_a,))

    res1_b = BenchmarkResult(task_id="t1", agent_id="a2", resolved=True)
    run_treatment = BenchmarkRun(run_id="r2", suite_id="s1", agent_id="a2", results=(res1_b,))

    comp = StatisticalAnalyzer.compare_runs(run_control, run_treatment)
    assert comp.delta_pass_rate == 1.0
    assert comp.beats_noise_floor is True


def test_benchmark_reporter_markdown_and_json() -> None:
    res1 = BenchmarkResult(task_id="t1", agent_id="a1", resolved=True, steps=3, wall_clock_s=1.2)
    run = BenchmarkRun(run_id="r1", suite_id="s1", agent_id="a1", results=(res1,))

    md = BenchmarkReporter.render_markdown(run)
    assert "# 📊 SAGIHA E0 Benchmark Report" in md
    assert "`t1`" in md
    assert "100.0%" in md

    json_str = BenchmarkReporter.render_json(run)
    assert '"pass_rate": 1.0' in json_str
