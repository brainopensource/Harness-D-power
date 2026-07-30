# **Sprint 4: E0 Evaluation Harness (Block 2 — Baseline Calibration & Benchmark Suite)**

> **Status**: Completed (2026-07-30) — E0-lite evaluation harness delivered.
> **Source**: [Phased Migration Matrix](../07-roadmap/phased-migration-matrix.md) — Block 2 (E0-lite).
> **Target**: Commit-replay harvester, benchmark runner (`sagiha bench`), A/A noise floor calibration, and statistical reporting.

---

## 📋 **Sprint 4 Implementation Checklist**

- [x] **1. Benchmark Domain Models (`src/sagiha/domain/benchmark.py`)**
  - [x] `HarvestedTask` (task_id, repo, base_commit, target_commit, failing_test_cmd, files_changed).
  - [x] `BenchmarkResult` (task_id, agent_id, resolved, gate_report, cost, steps, wall_clock_s, error).
  - [x] `BenchmarkSuite` (suite_id, repo, tasks, created_at).
  - [x] `BenchmarkRun` (run_id, suite_id, agent_id, results, status, timestamps).
  - [x] `NoiseFloor` (manifest_id, runs_per_task, mean_delta, std_delta, confidence_interval_95, max_acceptable_delta).

- [x] **2. Commit-Replay Harvester (`src/sagiha/e0/harvester.py`)**
  - [x] Asynchronous git log walker inspecting recent commits.
  - [x] Identification of fix-commits modifying both source and test files.
  - [x] Harvesting into versioned `BenchmarkSuite` JSON files (`sagiha harvest`).

- [x] **3. Benchmark Task Runner (`src/sagiha/e0/runner.py`)**
  - [x] Executes agent or cassette over individual harvested tasks or entire suites.
  - [x] Wires `RunLoop`, `GateEvaluator`, and workspace execution per task.
  - [x] Captures per-task admission, step count, latency, and exceptions into `BenchmarkRun`.

- [x] **4. A/A Noise Floor & Paired Statistics (`src/sagiha/e0/statistics.py`)**
  - [x] Pass rate calculation over benchmark runs.
  - [x] A/A Noise Floor calculation measuring stochastic variance across two un-mutated passes.
  - [x] 95% Confidence Interval estimation.
  - [x] Paired comparison (`compare_runs`) testing treatment vs control against the noise floor.

- [x] **5. Benchmark Reporter (`src/sagiha/e0/reporter.py`)**
  - [x] Render Markdown formatted benchmark reports (`sagiha bench -o report.md`).
  - [x] Render structured JSON evaluation output (`sagiha bench -o report.json`).

- [x] **6. CLI Commands (`src/sagiha/cli.py`)**
  - [x] `sagiha harvest`: Harvest tasks from repository history into `BenchmarkSuite`.
  - [x] `sagiha bench`: Run evaluation suite, optional A/A calibration (`--aa`), export report.

- [x] **7. Conformance & Unit Tests (`tests/unit/`)**
  - [x] `test_harvester.py`: Test git log analysis, task generation, suite save/load.
  - [x] `test_benchmark_runner.py`: Test single task and full suite execution.
  - [x] `test_e0_statistics.py`: Test pass rate calculation, noise floor derivation, markdown/JSON reporting.

---

## 🎯 **Verification**

```bash
uv run pytest tests/unit/test_harvester.py tests/unit/test_benchmark_runner.py tests/unit/test_e0_statistics.py -v
uv run sagiha harvest --help
uv run sagiha bench --help
```
