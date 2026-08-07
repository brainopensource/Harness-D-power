"""Statistical engine (TASK-012).

Three groups, matching the module's own split:

* the **verbatim port** against pinned JSON fixtures and hand-computable
  values — a port is only verbatim if it still produces the same numbers;
* the **B4 layer** — instrument errors out of the denominator, discordance
  rates reported;
* the **rev. 2 layer** — derived N (validated against ADR-0003's own published
  power table) and the family gatekeeper, with the negative tests that prove
  each refusal can fire.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aether.domain.gate import GateStatus
from aether.measurement.outcomes import ArmRun, TaskOutcome
from aether.measurement.statistics import (
    FamilyRegistry,
    FamilyValidationError,
    PowerInfeasibleError,
    StatisticalAnalyzer,
    UndeclaredFamilyError,
    alternative_discordance,
    bootstrap_ci,
    derive_n,
    derive_n_for_family,
    discordance,
    family_hash,
    holm,
    holm_correct_family,
    load_family,
    mcnemar_exact,
    noise_floor_from,
    paired_deltas,
    resolve_rate,
    simulate_power,
    validate_family,
)

FIXTURES = Path(__file__).parent.parent.parent / "fixtures" / "statistics"
FAMILY_FIXTURES = Path(__file__).parent.parent.parent / "fixtures" / "families"
MALFORMED_FAMILIES = FAMILY_FIXTURES / "malformed"


def _run(arm_id: str, outcomes: dict[str, GateStatus]) -> ArmRun:
    return ArmRun(
        run_id=f"run-{arm_id}",
        arm_id=arm_id,
        harness_id="aether",
        manifest_hash="sha256:" + "1" * 64,
        split="dev",
        model_fingerprint="test:model:ep",
        seed=0,
        results=tuple(TaskOutcome(task_id=t, status=s) for t, s in outcomes.items()),
    )


# ------------------------------------------------- PART 1, the verbatim port


def test_mcnemar_matches_its_pinned_fixture() -> None:
    for case in json.loads((FIXTURES / "mcnemar_exact.json").read_text()):
        assert mcnemar_exact(case["b"], case["c"]) == pytest.approx(case["p"])


@pytest.mark.parametrize(
    ("b", "c", "expected"),
    [
        (0, 0, 1.0),  # perfect agreement is not evidence of a difference
        (0, 5, 2 * (1 / 32)),  # 2 * P(X <= 0), X ~ Binomial(5, 0.5)
        (1, 9, 2 * (1 + 10) / 2**10),
        (5, 5, 1.0),  # symmetric split: the overlapping middle term is corrected
    ],
)
def test_mcnemar_against_hand_computed_values(b: int, c: int, expected: float) -> None:
    """Fixtures pin what the code does; these pin what the *test* should be."""
    assert mcnemar_exact(b, c) == pytest.approx(expected)


def test_mcnemar_is_symmetric() -> None:
    assert mcnemar_exact(3, 8) == mcnemar_exact(8, 3)


def test_holm_matches_its_pinned_fixture() -> None:
    for case in json.loads((FIXTURES / "holm.json").read_text()):
        assert holm(case["p"]) == pytest.approx(case["adjusted"])


def test_holm_is_order_preserving_and_monotone() -> None:
    adjusted = holm([0.04, 0.01])
    assert adjusted[1] <= adjusted[0]  # the smallest raw p keeps the smallest adjusted p
    assert holm([0.001, 0.02, 0.03, 0.9])[0] == pytest.approx(0.004)


def test_bootstrap_ci_matches_its_pinned_fixture_and_is_seeded() -> None:
    case = json.loads((FIXTURES / "bootstrap_ci.json").read_text())
    first = bootstrap_ci(case["deltas"], seed=case["seed"], iterations=case["iterations"])
    second = bootstrap_ci(case["deltas"], seed=case["seed"], iterations=case["iterations"])

    assert list(first) == pytest.approx(case["ci"])
    assert first == second  # same seed, same interval — auditable, not merely plausible


def test_paired_deltas_joins_on_task_id_never_positionally() -> None:
    control = _run("a", {"t1": GateStatus.PASSED, "t2": GateStatus.FAILED})
    treatment = _run("b", {"t2": GateStatus.PASSED, "t1": GateStatus.PASSED})

    assert sorted(paired_deltas(control, treatment)) == [0.0, 1.0]


def test_a_comparison_that_cannot_be_computed_returns_none_not_a_default() -> None:
    """The H5 defect, kept closed: absence of a verdict is never a pass."""
    control = _run("a", {"t1": GateStatus.PASSED})
    treatment = _run("b", {"t1": GateStatus.PASSED})

    result = StatisticalAnalyzer.compare_runs(control, treatment)

    assert result.p_value is None
    assert result.adjusted_p_value is None
    assert result.beats_noise_floor is None


def test_holm_correct_family_replaces_the_family_of_one_correction() -> None:
    control = _run("ctl", {f"t{i}": GateStatus.FAILED for i in range(10)})
    better = _run("t1", {f"t{i}": GateStatus.PASSED for i in range(10)})
    worse = _run("t2", {f"t{i}": (GateStatus.PASSED if i < 3 else GateStatus.FAILED) for i in range(10)})

    comparisons = [
        StatisticalAnalyzer.compare_runs(control, better),
        StatisticalAnalyzer.compare_runs(control, worse),
    ]
    corrected = holm_correct_family(comparisons)

    for before, after in zip(comparisons, corrected, strict=True):
        assert after.adjusted_p_value is not None
        assert before.adjusted_p_value is not None
        assert after.adjusted_p_value >= before.adjusted_p_value


# ------------------------------------------------------------ PART 2, B4


def test_instrument_errors_are_excluded_from_the_resolve_rate_denominator() -> None:
    """B4. Two resolves out of three *measured* tasks is 2/3, not 2/4."""
    run = _run(
        "a",
        {
            "t1": GateStatus.PASSED,
            "t2": GateStatus.PASSED,
            "t3": GateStatus.FAILED,
            "t4": GateStatus.NONE,
        },
    )

    assert resolve_rate(run) == pytest.approx(2 / 3)
    # The ported pass-rate divides by everything — kept verbatim, and not what
    # the floor path uses.
    assert StatisticalAnalyzer.compute_pass_rate(run) == pytest.approx(2 / 4)


def test_a_run_with_nothing_measured_has_no_rate_rather_than_zero() -> None:
    """`0.0` and "could not be computed" are different facts — the 2026-08-01
    non-run reported the first while meaning the second."""
    assert resolve_rate(_run("a", {"t1": GateStatus.NONE, "t2": GateStatus.NONE})) is None


def test_a_pair_is_dropped_when_either_arm_hit_an_instrument_error() -> None:
    control = _run("a", {"t1": GateStatus.PASSED, "t2": GateStatus.NONE, "t3": GateStatus.FAILED})
    treatment = _run("b", {"t1": GateStatus.FAILED, "t2": GateStatus.PASSED, "t3": GateStatus.FAILED})

    b, c, n_pairs, dropped = discordance(control, treatment)

    assert (b, c) == (1, 0)
    assert n_pairs == 2
    assert dropped == 1


def test_the_floor_reports_the_discordance_rates_that_size_every_later_run() -> None:
    """Without p01/p10 no admission run in this project can be sized at all."""
    control = _run(
        "a",
        {
            "t1": GateStatus.PASSED,
            "t2": GateStatus.FAILED,
            "t3": GateStatus.PASSED,
            "t4": GateStatus.FAILED,
        },
    )
    treatment = _run(
        "b",
        {
            "t1": GateStatus.PASSED,
            "t2": GateStatus.PASSED,
            "t3": GateStatus.FAILED,
            "t4": GateStatus.FAILED,
        },
    )

    floor = noise_floor_from(control, treatment, iterations=200, seed=0)

    assert floor.n_tasks == 4
    assert floor.p01 == pytest.approx(0.25)  # t2: treatment resolved, control did not
    assert floor.p10 == pytest.approx(0.25)  # t3: the reverse
    assert floor.n_discordant == 2
    assert floor.n_instrument_errors == 0


def test_the_floor_counts_instrument_errors_separately_and_visibly() -> None:
    control = _run("a", {"t1": GateStatus.PASSED, "t2": GateStatus.NONE})
    treatment = _run("b", {"t1": GateStatus.PASSED, "t2": GateStatus.PASSED})

    floor = noise_floor_from(control, treatment, iterations=100, seed=0)

    assert floor.n_tasks == 1
    assert floor.n_instrument_errors == 1


# ------------------------------------------------------ PART 2, derived N


def test_power_matches_its_pinned_fixture() -> None:
    for case in json.loads((FIXTURES / "power.json").read_text()):
        power = simulate_power(
            case["n"],
            p01=case["p01"],
            p10=case["p10"],
            effect=case["effect"],
            alpha=case["alpha"],
            iterations=case["iterations"],
            seed=case["seed"],
        )
        assert power == pytest.approx(case["power"])


def test_the_simulation_reproduces_adr_0003s_published_power_table() -> None:
    """ADR-0003 rev. 2 publishes 0.73 for the clean discordance row at N=100,
    α=0.05, 20,000 iterations, seed 7. If this drifts, either the ADR's number
    or this implementation is wrong, and both are load-bearing: the whole
    derived-N rule rests on that table.

    (The full 12-cell table is reproduced by
    `scripts/verify_power_table.py`; one cell is gated here to keep the suite
    fast, and all twelve matched at the time of writing — sprint-03.md.)
    """
    power = simulate_power(100, p01=0.12, p10=0.02, effect=0.10, alpha=0.05, iterations=20_000, seed=7)

    assert power == pytest.approx(0.73, abs=0.005)


def test_n_50_cannot_see_the_committed_target() -> None:
    """The finding that made N derived rather than fixed: at N=50 the protocol
    detects its own committed +10-point lift under a third of the time."""
    power = simulate_power(50, p01=0.12, p10=0.02, effect=0.10, iterations=4_000, seed=7)

    assert power < 0.5


def test_derive_n_returns_the_smallest_n_reaching_the_target_power() -> None:
    n, power = derive_n(p01=0.12, p10=0.02, effect=0.10, target_power=0.8, iterations=1_500, seed=7)

    assert n > 50  # the fixed-N rev. 1 value is nowhere near enough
    assert power >= 0.8


def test_a_noisier_instrument_needs_a_larger_n() -> None:
    """The mechanism that makes the floor worth taking: N is a function of the
    instrument's measured noise, not of taste."""
    clean, _ = derive_n(p01=0.12, p10=0.02, effect=0.10, iterations=1_000, seed=7)
    noisy, _ = derive_n(p01=0.30, p10=0.20, effect=0.10, iterations=1_000, seed=7)

    assert noisy > clean


def test_the_alternative_holds_total_discordance_fixed() -> None:
    p01, p10 = alternative_discordance(0.12, 0.12, 0.10)

    assert p01 - p10 == pytest.approx(0.10)
    assert p01 + p10 == pytest.approx(0.24)


def test_an_effect_larger_than_the_available_discordance_is_refused() -> None:
    """Rather than reporting a power number for an alternative that cannot
    exist at that discordance."""
    with pytest.raises(PowerInfeasibleError):
        alternative_discordance(0.02, 0.01, 0.10)


# --------------------------------------------------- PART 2, the gatekeeper


@pytest.fixture
def registry() -> FamilyRegistry:
    return FamilyRegistry(FAMILY_FIXTURES)


def test_a_declared_family_gets_corrected_p_values(registry: FamilyRegistry) -> None:
    assert registry.holm_for_family("test_repair_ablation", [0.02]) == pytest.approx([0.02])


def test_an_undeclared_family_is_refused(registry: FamilyRegistry) -> None:
    """**The anti-p-hacking mechanism.** Enforcement, not discipline: there is
    no way to register a family after seeing the data."""
    with pytest.raises(UndeclaredFamilyError) as exc_info:
        registry.holm_for_family("a_family_invented_after_seeing_the_data", [0.01])

    assert "never declared" in str(exc_info.value)


def test_dropping_a_hypothesis_after_seeing_its_p_value_is_refused(registry: FamilyRegistry) -> None:
    """Holm across a subset chosen post hoc is the cheapest way to manufacture
    significance, and it would otherwise look like an ordinary call."""
    with pytest.raises(UndeclaredFamilyError):
        registry.holm_for_family("test_repair_ablation", [0.01, 0.02])


def test_the_registry_declares_exactly_what_is_committed(registry: FamilyRegistry) -> None:
    assert registry.declared() == ("test_repair_ablation",)


def test_a_malformed_declared_family_fails_loudly_rather_than_being_skipped() -> None:
    """Skipping it would leave a family that looks declared and corrects
    nothing — the "contract that selects no file" defect, one level up."""
    with pytest.raises(FamilyValidationError):
        FamilyRegistry(MALFORMED_FAMILIES)


@pytest.mark.parametrize(
    ("fixture", "check"),
    [
        ("bad_tier_split.yaml", "tier_split_binding"),
        ("bad_tier_floor.yaml", "tier_floor"),
        ("bad_missing_topology.yaml", "arm_identity"),
        ("bad_unknown_arm.yaml", "hypothesis_arms"),
        ("bad_correction.yaml", "schema"),
    ],
)
def test_each_family_gate_can_fail(fixture: str, check: str) -> None:
    family = load_family((MALFORMED_FAMILIES / fixture).read_text())

    with pytest.raises(FamilyValidationError) as exc_info:
        validate_family(family)

    assert exc_info.value.check == check


def test_a_family_is_identified_by_its_canonical_json_hash() -> None:
    family = load_family((FAMILY_FIXTURES / "valid_family.yaml").read_text())
    before = family_hash(family)

    family["hypotheses"].append(dict(family["hypotheses"][0], hypothesis_id="added_later"))

    assert family_hash(family) != before  # a new hypothesis is a new family, never an amend


def test_the_derived_n_is_re_runnable_from_the_family_file_alone() -> None:
    """ADR-0003 rev. 2 §1: the power simulation is re-runnable from the family
    file and nothing else, so a reviewer can check the sizing themselves."""
    family = load_family((FAMILY_FIXTURES / "valid_family.yaml").read_text())

    n, power = derive_n_for_family(family, iterations=1_000)

    assert n >= 50
    assert 0.0 <= power <= 1.0
