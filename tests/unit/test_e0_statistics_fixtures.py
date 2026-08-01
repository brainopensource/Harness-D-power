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
    holm_correct_family,
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


def test_compare_runs_populates_adjusted_p_value() -> None:
    """Defect #3 (sprint_v2_s4_fixes.md): `holm()` was written and fixture-tested but never
    invoked, so `adjusted_p_value` was `None` on every path despite the exit gate requiring
    'Holm-corrected'. `compare_runs` now runs the (family-of-one) correction itself."""
    control = _run("r1", "a1", [("t1", False), ("t2", False), ("t3", True)])
    treatment = _run("r2", "a2", [("t1", True), ("t2", True), ("t3", True)])
    comp = StatisticalAnalyzer.compare_runs(control, treatment)
    assert comp.p_value is not None
    assert comp.adjusted_p_value is not None
    assert comp.adjusted_p_value == pytest.approx(comp.p_value)  # family of one == identity


def test_holm_correct_family_corrects_across_multiple_comparisons() -> None:
    """A real multi-treatment family must get the actual Holm step-down, not each comparison's
    degenerate family-of-one correction."""
    control = _run("r1", "a1", [("t1", False), ("t2", False), ("t3", False), ("t4", False)])
    treatment_a = _run("r2", "a2", [("t1", True), ("t2", True), ("t3", True), ("t4", True)])
    treatment_b = _run("r3", "a3", [("t1", True), ("t2", False), ("t3", False), ("t4", False)])

    comp_a = StatisticalAnalyzer.compare_runs(control, treatment_a)
    comp_b = StatisticalAnalyzer.compare_runs(control, treatment_b)
    assert comp_a.p_value is not None and comp_b.p_value is not None

    corrected = holm_correct_family([comp_a, comp_b])
    expected = holm([comp_a.p_value, comp_b.p_value])
    assert [c.adjusted_p_value for c in corrected] == pytest.approx(expected)


def test_harvester_test_file_predicate_excludes_fixture_data() -> None:
    """The harvester's `failing_test_cmd` must contain only files pytest actually collects.

    The predicate used to be `"test" in path.lower() or path.startswith("tests/")`, which swept
    fixture data (`tests/fixtures/replay_smoke/cassette.json`, a `.gitkeep`) into the command.
    `pytest <a JSON file>` exits non-zero on a collection error, so validation would "confirm"
    a failing test that no source fix could ever make pass — every task harvested from a commit
    touching test fixtures was silently unusable.
    """
    from sagiha.e0.harvester import is_test_file

    assert is_test_file("tests/unit/test_best_of_n.py")
    assert is_test_file("tests/contracts/test_port_shape.py")
    assert is_test_file("src/pkg/thing_test.py")

    assert not is_test_file("tests/fixtures/replay_smoke/cassette.json")
    assert not is_test_file("tests/fixtures/replay_smoke/workspace/.gitkeep")
    assert not is_test_file("tests/conftest.py")
    assert not is_test_file("src/sagiha/e0/statistics.py")
    assert not is_test_file("docs/latest-greatest.md")


def test_default_test_command_isolates_the_worktree_source_tree(tmp_path) -> None:
    """The harvested test command must force the *worktree's* source onto `sys.path`.

    The venv materialized into a scratch worktree carries an **editable** install whose `.pth`
    points at the main checkout's `src/`. Without `PYTHONPATH=src`, `import sagiha` inside a
    worktree pinned at commit X resolves to whatever is in the developer's working tree right
    now — so the harvester validated tasks against current source rather than the task
    baseline, `BenchmarkRunner` measured the same, and Best-of-N candidates would each edit
    their own worktree while every candidate's tests imported one shared tree, making candidate
    diffs invisible to the gates scoring them.
    """
    from sagiha.e0.harvester import default_test_command

    cmd = default_test_command(tmp_path)
    assert cmd.startswith("env PYTHONPATH=src "), cmd
    assert "-m pytest" in cmd
    # No interpreter in a bare tmp dir -> falls back to python3, never a bare `pytest`.
    assert "python3 -m pytest" in cmd

    venv_bin = tmp_path / ".venv" / "bin"
    venv_bin.mkdir(parents=True)
    (venv_bin / "python").write_text("")
    assert str(venv_bin / "python") in default_test_command(tmp_path)


def test_infrastructure_failures_are_not_reproduced_test_failures() -> None:
    """A command that could not execute is not evidence about a task.

    Exit 127 (`pytest` not on PATH) and a plain exit 1 carrying `No module named pytest` both
    used to count as "the failing test reproduced", so the harvester would certify tasks whose
    failure no source fix could ever resolve.
    """
    from sagiha.e0.harvester import _is_infrastructure_failure

    assert _is_infrastructure_failure(127, "")
    assert _is_infrastructure_failure(126, "")
    assert _is_infrastructure_failure(5, "")  # pytest: no tests collected
    assert _is_infrastructure_failure(1, "/usr/bin/python: No module named pytest")
    # A real failing test: exit 1 with ordinary pytest output.
    assert not _is_infrastructure_failure(1, "2 failed, 6 passed in 0.20s")
    assert not _is_infrastructure_failure(0, "")
