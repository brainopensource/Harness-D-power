"""The A/A floor's own tooling (Sprint 3 Task 5).

The floor is a measurement, so its generator and its report are instruments
too, and instruments get gates. Three things must hold or the floor is not
re-runnable and not readable:

* the suite regenerates **identically** — same trees, same base commit SHAs,
  on any machine, or the pinned manifest is valid only where it was built;
* every generated defect is **observable** — a task whose tests already pass at
  the base commit is a free resolve for every arm (the canary caught 16 of
  those on the first generator, which is why this test exists);
* the report carries its **full instrument tuple** — Sprint 3 DoD item 10.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType

import pytest

from aether.domain.gate import GateStatus
from aether.measurement.outcomes import ArmRun, TaskOutcome
from aether.measurement.statistics import load_family, noise_floor_from

SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"


def _load_script(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


builder = _load_script("build_floor_manifest")
floor = _load_script("run_aa_floor")


# ------------------------------------------------------------- determinism


@pytest.mark.skipif(shutil.which("git") is None, reason="git required")
def test_the_suite_regenerates_with_identical_base_commits(tmp_path: Path) -> None:
    """Pinned author identity and pinned commit dates, so a manifest built on
    one machine still resolves on another. Without this the base commits differ
    per generation and the pinned manifest is a local artefact."""
    first = [builder.generate_task(tmp_path / "a", i) for i in range(4)]
    second = [builder.generate_task(tmp_path / "b", i) for i in range(4)]

    assert [t.base_commit for t in first] == [t.base_commit for t in second]
    assert [t.instance_id for t in first] == [t.instance_id for t in second]
    assert all(len(t.base_commit) == 40 for t in first)


@pytest.mark.skipif(shutil.which("git") is None, reason="git required")
def test_regeneration_is_idempotent_in_the_same_workdir(tmp_path: Path) -> None:
    once = builder.generate_task(tmp_path, 3)
    twice = builder.generate_task(tmp_path, 3)

    assert once.base_commit == twice.base_commit
    assert once.gold_patch == twice.gold_patch


@pytest.mark.skipif(shutil.which("git") is None, reason="git required")
def test_the_gold_patch_applies_cleanly_with_git(tmp_path: Path) -> None:
    """Produced by the same `git diff` the workspace adapter later applies — a
    gold patch made by a different tool than the one applying it is a canary
    for the wrong thing."""
    candidate = builder.generate_task(tmp_path, 0)
    repo = tmp_path / candidate.instance_id
    patch_file = tmp_path / "gold.patch"
    patch_file.write_text(candidate.gold_patch)

    result = subprocess.run(
        ["git", "apply", "--check", str(patch_file)], cwd=repo, capture_output=True, text=True
    )

    assert result.returncode == 0, result.stderr


# ------------------------------------------------------------ observability


@pytest.mark.parametrize("index", range(len(builder.BUG_SHAPES) * 3))
def test_every_generated_defect_is_observable(index: int) -> None:
    """The buggy body must give a different answer than the fixed one **for
    this instance's constants**.

    This is the test the first generator did not have: with one constant rule
    for every shape, 16 of 84 tasks had `a > b` for `abs_diff` (or `b` dividing
    `a` for `floor_div`), where the "bug" returns the right answer and the
    empty patch passes. The canary excluded them correctly — and a generator
    that emits them is producing free resolves, so the check belongs here too.
    """
    shape, buggy, fixed, expected = builder.BUG_SHAPES[index % len(builder.BUG_SHAPES)]
    a, b = builder._constants(shape, index)

    buggy_result = eval(buggy.removeprefix("return "), {}, {"a": a, "b": b})  # noqa: S307
    fixed_result = eval(fixed.removeprefix("return "), {}, {"a": a, "b": b})  # noqa: S307

    assert fixed_result == expected(a, b), f"{shape}: the 'fixed' body is not the expected answer"
    assert buggy_result != fixed_result, (
        f"{shape} at a={a}, b={b}: the bug is invisible — this task's tests pass with no patch, "
        "which is a free resolve for every arm (measurement.md §4.3)"
    )


def test_the_declared_floor_family_is_pinned_to_the_committed_manifest() -> None:
    """Pre-registration is only pre-registration if it names the manifest it
    was registered against."""
    from aether.measurement.manifest import load_manifest, manifest_hash

    manifest_path = Path(floor.DEFAULT_MANIFEST)
    if not manifest_path.exists():
        pytest.skip("no pinned floor manifest in this checkout")
    family = load_family(
        (Path(__file__).resolve().parents[3] / "src" / "aether" / "measurement" / "families"
         / "aa_floor_smoke_01.yaml").read_text()
    )
    manifest = load_manifest(manifest_path.read_text())

    assert family["manifest_hash"] == manifest_hash(manifest)
    assert family["sample"] == {"tier": "smoke", "n": 50, "split": "dev"}


# ---------------------------------------------------------------- the report


def _arm(arm_id: str, statuses: list[GateStatus]) -> ArmRun:
    return ArmRun(
        run_id=f"{arm_id}-1",
        arm_id=arm_id,
        harness_id="aether",
        manifest_hash="sha256:" + "a" * 64,
        split="dev",
        model_fingerprint="openai_compatible:test-model:endpoint",
        seed=7,
        topology_hash="sha256:" + "b" * 64,
        container_digest="sha256:" + "c" * 64,
        contained=True,
        results=tuple(
            TaskOutcome(task_id=f"t{i}", status=s, wall_clock_ms=100 + i)
            for i, s in enumerate(statuses)
        ),
    )


def test_the_report_carries_its_whole_instrument_tuple() -> None:
    """Sprint 3 DoD item 10: manifest hash, split, model fingerprint, topology
    hash, container digests, lockfile hash and seed — every one, every time."""
    arm_a = _arm("aether_a", [GateStatus.PASSED, GateStatus.FAILED, GateStatus.PASSED])
    arm_b = _arm("aether_b", [GateStatus.PASSED, GateStatus.PASSED, GateStatus.FAILED])
    family = {"family_id": "aa_floor_smoke_01", "registered_at": datetime.now(UTC).isoformat()}

    report = floor.build_report(
        noise_floor_from(arm_a, arm_b, iterations=100, seed=7), arm_a, arm_b, family, 1.0, 1.0, 12.5
    )

    for required in (
        "sha256:" + "a" * 64,  # manifest hash
        "sha256:" + "b" * 64,  # topology hash
        "sha256:" + "c" * 64,  # container digest
        "openai_compatible:test-model:endpoint",
        "Lockfile hash",
        "aa_floor_smoke_01",
    ):
        assert required in report
    assert "Seed | 7" in report or "| 7 |" in report


def test_the_report_states_the_discordance_rates_the_floor_exists_to_produce() -> None:
    arm_a = _arm("aether_a", [GateStatus.PASSED, GateStatus.FAILED])
    arm_b = _arm("aether_b", [GateStatus.FAILED, GateStatus.FAILED])
    result = noise_floor_from(arm_a, arm_b, iterations=100, seed=7)

    report = floor.build_report(result, arm_a, arm_b, {"family_id": "f", "registered_at": "x"}, 1.0, 1.0, 1.0)

    assert "Discordance p₀₁" in report
    assert "Discordance p₁₀" in report
    assert "per-task wall-clock" in report.lower()


def test_the_report_says_which_suite_the_floor_belongs_to() -> None:
    """A floor is a property of an instrument *and* a task set. A reader who
    takes this for a SWE-bench floor has been misled by us, not by themselves."""
    arm = _arm("aether_a", [GateStatus.PASSED])
    report = floor.build_report(
        noise_floor_from(arm, arm, iterations=50, seed=7), arm, arm,
        {"family_id": "f", "registered_at": "x"}, 1.0, 1.0, 1.0,
    )

    assert "not for SWE-bench" in report


def test_instrument_errors_are_reported_not_hidden() -> None:
    arm_a = _arm("aether_a", [GateStatus.PASSED, GateStatus.NONE])
    arm_b = _arm("aether_b", [GateStatus.PASSED, GateStatus.PASSED])

    result = noise_floor_from(arm_a, arm_b, iterations=50, seed=7)
    report = floor.build_report(result, arm_a, arm_b, {"family_id": "f", "registered_at": "x"}, 1.0, 1.0, 1.0)

    assert result.n_instrument_errors == 1
    assert "Instrument errors excluded (B4) | 1" in report
