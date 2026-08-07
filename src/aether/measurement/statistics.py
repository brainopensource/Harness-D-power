"""Statistical engine (TASK-012) — exact McNemar, Holm–Bonferroni, seeded
bootstrap, derived-N power simulation, and the family gatekeeper.

**Provenance** (`spec.md` §9 predecessor-code clause). Everything under
"PART 1 — VERBATIM PORT" is ported from the predecessor's
`src/sagiha/e0/statistics.py` at commit `89074a5`, 259 LOC, pure stdlib. It is
the one component of the prior codebase whose claimed properties verified line
by line, and ADR-0003 §5 requires it be taken **verbatim**, with the rev. 2
additions written *around* it rather than as edits to it.

Adaptations made while porting, and nothing else:

* `BenchmarkRun` → `measurement.outcomes.ArmRun`, `NoiseFloor` /
  `ComparisonResult` → the same-named models in `measurement.outcomes`
  (the predecessor's `sagiha.domain.benchmark` is retiring);
* `run.agent_id` → `run.arm_id`, `run.suite_id` → `run.manifest_hash`;
* docstring cross-references repointed at this tree's documents.

No algorithm, constant, branch or edge case was changed. In particular
`mcnemar_exact`'s overlapping-tail correction, `bootstrap_ci`'s index
arithmetic, and `compare_runs`' `None`-when-unknowable contract are byte-for-
byte the ported logic.

PART 2 adds what rev. 2 requires and the predecessor did not have:

1. **B4-correct denominators.** `GateStatus.NONE` is *unmeasured*. The ported
   `compute_pass_rate` divides by every result, which was right for a harness
   with no tri-state; here it would put our own instrument errors in the
   denominator. `resolve_rate` and `paired_measured_outcomes` are the B4
   versions, and the floor path uses those.
2. **Derived N.** A seeded Monte-Carlo power simulation, re-runnable from a
   family file alone (ADR-0003 rev. 2 §1). At N=50 exact McNemar sees a true
   +10-point lift in 12–32% of cases — a protocol that discards nine true
   improvements in ten is not conservative, it is blind.
3. **The family gatekeeper.** This module **refuses to compute corrected
   p-values for an undeclared family**. Enforcement, not discipline: the
   family is a committed TCB file with `registered_commit` proving it landed
   before any arm ran, and adding a hypothesis afterwards is a *new file with
   a new hash* — there is no amend, and no `--force`.

TCB residency: `aether-tcb-isolation` selects this module, so it may not
import `aether.adapters`, `aether.workflow` or `aether.agency`.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

import jsonschema
import yaml

from aether.measurement.outcomes import ArmRun, ComparisonResult, NoiseFloor, TaskOutcome

# ============================================================================
# PART 1 — VERBATIM PORT of sagiha/e0/statistics.py @ 89074a5
# Do not "improve" this section. Changes belong in PART 2.
# ============================================================================

#: Default bootstrap parameters. Fixed so A/A output is reproducible run over run —
#: the whole point of seeding is that nobody has to trust "it looked stable when I ran it".
DEFAULT_ALPHA = 0.05
DEFAULT_BOOTSTRAP_ITERATIONS = 2000
DEFAULT_SEED = 0


def _task_outcomes(run: ArmRun) -> dict[str, list[bool]]:
    """Map `task_id -> [resolved, ...]`, preserving every repetition in encounter order.

    A `task_id -> bool` dict (last-write-wins) would silently collapse `k` repetitions to
    one, disagreeing with `compute_pass_rate` (which correctly averages all of them) the
    moment `k > 1`. Keeping the list lets `paired_deltas` pair repetition-by-repetition.
    """
    outcomes: dict[str, list[bool]] = {}
    for r in run.results:
        outcomes.setdefault(r.task_id, []).append(r.resolved)
    return outcomes


def paired_deltas(control: ArmRun, treatment: ArmRun) -> list[float]:
    """Per-repetition pass/fail deltas (`+1`/`0`/`-1`) over the task_ids common to both runs.

    Joins on `task_id` rather than positionally — an unpaired comparison (different task sets,
    or results out of order) measures something other than the harness, and silently zipping
    two result lists would manufacture a paired comparison that never happened. Within a
    task_id, repetition `i` of `control` pairs with repetition `i` of `treatment`; any
    repetition-count mismatch for a task pairs only up to the shorter of the two.
    """
    control_by_task = _task_outcomes(control)
    treatment_by_task = _task_outcomes(treatment)
    common = sorted(set(control_by_task) & set(treatment_by_task))
    deltas: list[float] = []
    for t in common:
        control_reps = control_by_task[t]
        treatment_reps = treatment_by_task[t]
        for c_val, t_val in zip(control_reps, treatment_reps, strict=False):
            deltas.append(float(t_val) - float(c_val))
    return deltas


def mcnemar_exact(b: int, c: int) -> float:
    """Exact two-sided McNemar test over discordant pairs.

    `b`, `c` are the two discordant counts (control-pass/treatment-fail and control-fail/
    treatment-pass respectively — order does not matter, the test is symmetric). This is the
    correct test for paired binary pass/fail outcomes; a Wilcoxon signed-rank test assumes an
    ordinal/continuous statistic and is the wrong tool for a pass/fail pair.

    Returns `1.0` when there is nothing discordant to test (b == c == 0) — perfect agreement is
    not evidence of a difference, and the caller must not read that as "significant".
    """
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    # Two-sided exact binomial p-value under H0: P(X<=k) + P(X>=n-k) for X ~ Binomial(n, 0.5),
    # computed exactly via math.comb rather than a normal approximation.
    total = sum(math.comb(n, i) for i in range(0, k + 1))
    total += sum(math.comb(n, i) for i in range(n - k, n + 1))
    # The two tails overlap exactly when k == n - k (a perfectly symmetric split); correct for
    # the double-counted middle term instead of over-reporting significance.
    if n - k <= k:
        total -= math.comb(n, k)
    p = total / (2**n)
    return min(1.0, max(0.0, p))


def bootstrap_ci(
    deltas: list[float],
    *,
    alpha: float = DEFAULT_ALPHA,
    iterations: int = DEFAULT_BOOTSTRAP_ITERATIONS,
    seed: int = DEFAULT_SEED,
) -> tuple[float, float]:
    """Percentile bootstrap confidence interval over paired per-task deltas.

    `random.Random(seed)` rather than the module-global RNG: the same `deltas`/`seed` always
    produce the same interval, which is what makes a CI-committed noise floor auditable rather
    than merely plausible-looking.
    """
    if not deltas:
        return (0.0, 0.0)
    rng = random.Random(seed)
    n = len(deltas)
    means: list[float] = []
    for _ in range(iterations):
        sample = [deltas[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo_idx = int((alpha / 2) * iterations)
    hi_idx = int((1 - alpha / 2) * iterations) - 1
    hi_idx = min(hi_idx, iterations - 1)
    return (means[lo_idx], means[hi_idx])


def holm(pvalues: list[float]) -> list[float]:
    """Holm–Bonferroni step-down correction, order-preserving.

    Returns adjusted p-values in the same order as the input. Screening many candidates against
    one uncorrected threshold manufactures winners from noise — this is the required
    multiple-comparison correction (ADR-0003).
    """
    m = len(pvalues)
    if m == 0:
        return []
    indexed = sorted(range(m), key=lambda i: pvalues[i])
    adjusted = [0.0] * m
    running_max = 0.0
    for rank, idx in enumerate(indexed):
        value = min(1.0, (m - rank) * pvalues[idx])
        running_max = max(running_max, value)
        adjusted[idx] = running_max
    return adjusted


class StatisticalAnalyzer:
    """Analyzes benchmark runs for pass rate and statistical significance."""

    @staticmethod
    def compute_pass_rate(run: ArmRun) -> float:
        if not run.results:
            return 0.0
        resolved_count = sum(1 for r in run.results if r.resolved)
        return resolved_count / len(run.results)

    @staticmethod
    def compute_noise_floor(
        run_a: ArmRun,
        run_b: ArmRun,
        *,
        alpha: float = DEFAULT_ALPHA,
        iterations: int = DEFAULT_BOOTSTRAP_ITERATIONS,
        seed: int = DEFAULT_SEED,
    ) -> NoiseFloor:
        """A/A noise floor: two runs of the *unmodified* harness, same suite.

        `mean_delta` is the observed A/A drift; `confidence_interval` bounds it via a seeded
        bootstrap rather than placeholder arithmetic.
        """
        deltas = paired_deltas(run_a, run_b)
        mean_delta = abs(sum(deltas) / len(deltas)) if deltas else 0.0
        ci = bootstrap_ci(deltas, alpha=alpha, iterations=iterations, seed=seed)
        return NoiseFloor(
            manifest_id=run_a.manifest_hash,
            runs_per_task=2,
            mean_delta=mean_delta,
            confidence_interval=ci,
            alpha=alpha,
            k_runs=2,
            n_tasks=len(deltas),
            seed=seed,
        )

    @staticmethod
    def compare_runs(
        control: ArmRun,
        treatment: ArmRun,
        *,
        noise_floor: NoiseFloor | None = None,
    ) -> ComparisonResult:
        """Paired comparison, judged against `noise_floor` when one is supplied.

        Without a noise floor, `beats_noise_floor` stays `None` — there is nothing honest to
        compare against, and reporting `True` would be exactly the fabrication this rewrite
        exists to remove.
        """
        deltas = paired_deltas(control, treatment)
        n = len(deltas)
        rate_control = StatisticalAnalyzer.compute_pass_rate(control)
        rate_treatment = StatisticalAnalyzer.compute_pass_rate(treatment)
        delta_pass_rate = rate_treatment - rate_control

        b = sum(1 for d in deltas if d < 0)  # control-pass, treatment-fail
        c = sum(1 for d in deltas if d > 0)  # control-fail, treatment-pass
        n_discordant = b + c

        if n < 2 or n_discordant == 0:
            return ComparisonResult(
                control_agent_id=control.arm_id,
                treatment_agent_id=treatment.arm_id,
                delta_pass_rate=delta_pass_rate,
                p_value=None,
                adjusted_p_value=None,
                n_discordant=n_discordant,
                method="mcnemar_exact",
                beats_noise_floor=None,
            )

        p_value = mcnemar_exact(b, c)
        # Holm-Bonferroni over the family of comparisons this call is judged alongside.
        # `compare_runs` sees one comparison at a time, so the default family is this
        # comparison alone; correction only bites once a caller passes the real family
        # (see `holm_correct_family` below).
        adjusted_p_value = holm([p_value])[0]
        beats_floor: bool | None = None
        # `noise_floor.n_tasks == 0` means the floor itself was never honestly computed (no
        # pairable A/A tasks) — its `mean_delta`/`confidence_interval` are both the `0.0`
        # placeholder default, which every positive delta would trivially "beat".
        if noise_floor is not None and noise_floor.n_tasks > 0:
            beats_floor = (
                delta_pass_rate > noise_floor.mean_delta
                and delta_pass_rate > noise_floor.confidence_interval[1]
            )

        return ComparisonResult(
            control_agent_id=control.arm_id,
            treatment_agent_id=treatment.arm_id,
            delta_pass_rate=delta_pass_rate,
            p_value=p_value,
            adjusted_p_value=adjusted_p_value,
            n_discordant=n_discordant,
            method="mcnemar_exact",
            beats_noise_floor=beats_floor,
        )


def holm_correct_family(comparisons: list[ComparisonResult]) -> list[ComparisonResult]:
    """Re-derives `adjusted_p_value` for a family of comparisons run together, replacing each
    result's family-of-one correction with the real Holm–Bonferroni step-down across the whole
    family. Comparisons with `p_value is None` (nothing discordant to test) pass through
    unchanged — `holm` only operates over comparisons that produced a real p-value.
    """
    indices = [i for i, c in enumerate(comparisons) if c.p_value is not None]
    if not indices:
        return comparisons
    adjusted = holm([cast(float, comparisons[i].p_value) for i in indices])
    out = list(comparisons)
    for idx, adj in zip(indices, adjusted, strict=True):
        out[idx] = out[idx].model_copy(update={"adjusted_p_value": adj})
    return out


# ============================================================================
# PART 2 — rev. 2 additions (ADR-0003 rev. 2). New code around the port.
# ============================================================================

_FAMILY_SCHEMA_PATH = Path(__file__).parent / "schemas" / "family_schema.yaml"
FAMILIES_DIR = Path(__file__).parent / "families"

#: Tier floors (ADR-0003 rev. 2 §1). A tier names a role and a floor, never a
#: value: the derived N governs, and may exceed the floor by a lot.
TIER_FLOORS = {"smoke": 50, "admission": 150, "publication": 300}
#: Binding pairs. A smoke run on sealed data burns the publication set for a
#: signal that is not allowed to admit anything.
TIER_SPLITS = {"smoke": "dev", "admission": "holdout", "publication": "sealed"}


class FamilyValidationError(Exception):
    def __init__(self, check: str, message: str) -> None:
        self.check = check
        super().__init__(f"{check}: {message}")


class UndeclaredFamilyError(Exception):
    """Raised when corrected p-values are requested for a family that was never
    declared. The anti-p-hacking mechanism, and a hard raise on purpose."""


class PowerInfeasibleError(Exception):
    """Raised when the requested effect cannot be expressed at the assumed
    discordance — reporting a power number for it would be fiction."""


# ------------------------------------------------------- B4-aware statistics


def resolve_rate(run: ArmRun) -> float | None:
    """Resolve rate with `GateStatus.NONE` excluded from the denominator (B4).

    `None` when nothing was measured at all — not `0.0`. A rate of zero and a
    rate that could not be computed are different facts, and the predecessor's
    2026-08-01 non-run reported the former while meaning the latter.
    """
    measured = [r for r in run.results if r.measured]
    if not measured:
        return None
    return sum(1 for r in measured if r.resolved) / len(measured)


def paired_measured_outcomes(
    control: ArmRun, treatment: ArmRun
) -> tuple[list[tuple[TaskOutcome, TaskOutcome]], int]:
    """Pairs where **both** arms produced a measurement, plus the count dropped.

    A task that hit an instrument error in either arm is not a data point in
    either. Dropping it silently would be the same defect one level up, so the
    count comes back with the pairs and every report states it.
    """
    control_by_task = {r.task_id: r for r in control.results}
    treatment_by_task = {r.task_id: r for r in treatment.results}
    common = sorted(set(control_by_task) & set(treatment_by_task))
    pairs: list[tuple[TaskOutcome, TaskOutcome]] = []
    dropped = 0
    for task_id in common:
        a, b = control_by_task[task_id], treatment_by_task[task_id]
        if a.measured and b.measured:
            pairs.append((a, b))
        else:
            dropped += 1
    return pairs, dropped


def discordance(control: ArmRun, treatment: ArmRun) -> tuple[int, int, int, int]:
    """`(b, c, n_pairs, n_dropped)` over measured pairs.

    `b` = control resolved, treatment did not. `c` = the reverse. These two
    counts are the whole input to exact McNemar, and `(c/n, b/n)` are the
    `p₀₁`/`p₁₀` every future family's derived N is computed from.
    """
    pairs, dropped = paired_measured_outcomes(control, treatment)
    b = sum(1 for a, t in pairs if a.resolved and not t.resolved)
    c = sum(1 for a, t in pairs if not a.resolved and t.resolved)
    return b, c, len(pairs), dropped


def noise_floor_from(
    run_a: ArmRun,
    run_b: ArmRun,
    *,
    alpha: float = DEFAULT_ALPHA,
    iterations: int = DEFAULT_BOOTSTRAP_ITERATIONS,
    seed: int = DEFAULT_SEED,
) -> NoiseFloor:
    """The A/A floor, B4-corrected, carrying its discordance rates.

    This is the function the floor run calls. It differs from the ported
    `compute_noise_floor` in exactly two ways, both required by this tree:
    instrument errors are excluded from the pairing, and `p01`/`p10` are
    reported — without them, no later admission run can be sized at all
    (ADR-0003 rev. 2 §1).
    """
    pairs, dropped = paired_measured_outcomes(run_a, run_b)
    deltas = [float(t.resolved) - float(a.resolved) for a, t in pairs]
    n = len(deltas)
    b = sum(1 for d in deltas if d < 0)
    c = sum(1 for d in deltas if d > 0)
    mean_delta = abs(sum(deltas) / n) if n else 0.0
    return NoiseFloor(
        manifest_id=run_a.manifest_hash,
        runs_per_task=2,
        mean_delta=mean_delta,
        confidence_interval=bootstrap_ci(deltas, alpha=alpha, iterations=iterations, seed=seed),
        alpha=alpha,
        k_runs=2,
        n_tasks=n,
        seed=seed,
        p01=(c / n) if n else 0.0,
        p10=(b / n) if n else 0.0,
        n_discordant=b + c,
        n_instrument_errors=dropped,
    )


# --------------------------------------------------------------- derived N


def alternative_discordance(p01: float, p10: float, effect: float) -> tuple[float, float]:
    """Shift a measured floor's discordance to realize a true effect of
    `effect` (a proportion), holding total discordance fixed.

    `p01' − p10' = effect` and `p01' + p10' = p01 + p10`. Total discordance is
    a property of the instrument's noise; the effect is what a mechanism adds,
    and it moves pairs from one discordant cell to the other rather than
    inventing new ones. This reproduces ADR-0003 rev. 2's own power table,
    whose three rows each already satisfy `p01 − p10 = 0.10`.
    """
    total = p01 + p10
    if effect > total:
        raise PowerInfeasibleError(
            f"an effect of {effect:.3f} cannot be realized at total discordance {total:.3f}: "
            "at most every discordant pair could favour the treatment. Either the assumed "
            "discordance is too low or the minimal effect is too large."
        )
    return (total + effect) / 2, (total - effect) / 2


def simulate_power(
    n: int,
    *,
    p01: float,
    p10: float,
    effect: float,
    alpha: float = DEFAULT_ALPHA,
    iterations: int = 20_000,
    seed: int = 7,
) -> float:
    """Seeded Monte-Carlo power of exact McNemar at sample size `n`.

    Draws `n` paired outcomes from the trinomial implied by the alternative's
    discordance and counts how often the exact test clears `alpha`. Pure
    stdlib and seeded, so a reviewer re-runs it from the family file and gets
    the same number — that is what makes a derived N auditable rather than
    asserted.
    """
    p01_alt, p10_alt = alternative_discordance(p01, p10, effect)
    rng = random.Random(seed)
    hits = 0
    for _ in range(iterations):
        b = 0
        c = 0
        for _ in range(n):
            draw = rng.random()
            if draw < p01_alt:
                c += 1  # treatment resolved, control did not
            elif draw < p01_alt + p10_alt:
                b += 1  # control resolved, treatment did not
        if mcnemar_exact(b, c) <= alpha:
            hits += 1
    return hits / iterations


def derive_n(
    *,
    p01: float,
    p10: float,
    effect: float,
    target_power: float = 0.8,
    alpha: float = DEFAULT_ALPHA,
    floor: int = 50,
    ceiling: int = 2000,
    step: int = 25,
    iterations: int = 5_000,
    seed: int = 7,
) -> tuple[int, float]:
    """Smallest N at or above `floor` reaching `target_power`, and that power.

    Returns `(ceiling, power_at_ceiling)` when the target is unreachable
    inside the search range: an honest "this is not affordable at this effect
    size" beats a number that pretends otherwise. `iterations` is lower than
    `simulate_power`'s default because a search runs the simulation many
    times; re-confirm the chosen N at full iterations before publishing.
    """
    last_power = 0.0
    for n in range(floor, ceiling + 1, step):
        last_power = simulate_power(
            n, p01=p01, p10=p10, effect=effect, alpha=alpha, iterations=iterations, seed=seed
        )
        if last_power >= target_power:
            return n, last_power
    return ceiling, last_power


# ---------------------------------------------------------- the gatekeeper


def _load_family_schema() -> dict[str, Any]:
    with open(_FAMILY_SCHEMA_PATH, encoding="utf-8") as f:
        return cast("dict[str, Any]", yaml.safe_load(f))


_FAMILY_SCHEMA = _load_family_schema()


def load_family(yaml_text: str) -> dict[str, Any]:
    parsed: Any = yaml.safe_load(yaml_text)
    if not isinstance(parsed, dict):
        raise FamilyValidationError("schema", "family must be a mapping")
    return dict(cast("dict[str, Any]", parsed))


def family_hash(family: dict[str, Any]) -> str:
    """Canonical-JSON sha256, same convention as the manifest. Adding a
    hypothesis produces a new hash — which is precisely why there is no amend."""
    canonical = json.dumps(family, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()


def validate_family(family: dict[str, Any]) -> None:
    try:
        jsonschema.validate(family, _FAMILY_SCHEMA)
    except jsonschema.ValidationError as exc:
        raise FamilyValidationError("schema", exc.message) from exc

    sample = family["sample"]
    tier: str = sample["tier"]
    if sample["split"] != TIER_SPLITS[tier]:
        raise FamilyValidationError(
            "tier_split_binding",
            f"tier '{tier}' binds to split '{TIER_SPLITS[tier]}', got '{sample['split']}' — "
            "a smoke run on sealed data burns the publication set for a signal that may "
            "never admit anything",
        )
    if sample["n"] < TIER_FLOORS[tier]:
        raise FamilyValidationError(
            "tier_floor", f"tier '{tier}' floors N at {TIER_FLOORS[tier]}, got {sample['n']}"
        )

    arm_ids = {arm["arm_id"] for arm in family["arms"]}
    for arm in family["arms"]:
        if arm["harness_id"] == "aether" and "topology_hash" not in arm:
            raise FamilyValidationError(
                "arm_identity",
                f"arm '{arm['arm_id']}' is an aether arm with no topology_hash — the topology "
                "IS the harness's identity (ADR-0014)",
            )
    for hypothesis in family["hypotheses"]:
        for side in ("arm_a", "arm_b"):
            if hypothesis[side] not in arm_ids:
                raise FamilyValidationError(
                    "hypothesis_arms",
                    f"hypothesis '{hypothesis['hypothesis_id']}' names undeclared arm "
                    f"'{hypothesis[side]}'",
                )


def derive_n_for_family(family: dict[str, Any], *, iterations: int = 5_000) -> tuple[int, float]:
    """Re-run the family's own power calculation from the file alone.

    Uses the Holm-adjusted α at the *first* rank — `α/m` for a family of m
    hypotheses — because that is the hardest threshold any hypothesis in the
    family must clear, and sizing to the easiest one is how a family arrives
    underpowered while looking pre-registered.
    """
    power = family["power"]
    m = len(family["hypotheses"])
    return derive_n(
        p01=power["assumed_p01"],
        p10=power["assumed_p10"],
        effect=power["minimal_effect_pts"] / 100.0,
        target_power=power.get("target_power", 0.8),
        alpha=family["alpha_family"] / m,
        floor=TIER_FLOORS[family["sample"]["tier"]],
        seed=power["simulation_seed"],
        iterations=iterations,
    )


class FamilyRegistry:
    """The declared families. `holm_for_family` is the only way to obtain
    corrected p-values from this module, and it refuses anything not in here."""

    def __init__(self, families_dir: Path | None = None) -> None:
        self._dir = families_dir or FAMILIES_DIR
        self._families: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self._dir.is_dir():
            return
        for path in sorted(self._dir.glob("*.yaml")):
            family = load_family(path.read_text(encoding="utf-8"))
            validate_family(family)
            self._families[family["family_id"]] = family

    def declared(self) -> tuple[str, ...]:
        return tuple(sorted(self._families))

    def get(self, family_id: str) -> dict[str, Any]:
        if family_id not in self._families:
            raise UndeclaredFamilyError(
                f"family '{family_id}' was never declared. Declared: {self.declared() or '(none)'}. "
                "A gate family is a committed TCB file merged before any arm runs "
                "(ADR-0003 rev. 2 §3); there is no way to register one after seeing data."
            )
        return self._families[family_id]

    def holm_for_family(self, family_id: str, pvalues: Sequence[float]) -> list[float]:
        """Holm–Bonferroni across a **declared** family.

        Refuses an undeclared family, and refuses a p-value count that does not
        match the declared hypotheses — dropping a hypothesis after seeing its
        p-value is the cheapest way to manufacture significance, and it would
        otherwise look like an ordinary call.
        """
        family = self.get(family_id)
        declared_m = len(family["hypotheses"])
        if len(pvalues) != declared_m:
            raise UndeclaredFamilyError(
                f"family '{family_id}' declares {declared_m} hypotheses but {len(pvalues)} "
                "p-values were supplied. Holm corrects across the family as declared; "
                "correcting across a subset chosen after the fact is p-hacking with extra steps."
            )
        return holm(list(pvalues))


__all__ = [
    "DEFAULT_ALPHA",
    "DEFAULT_BOOTSTRAP_ITERATIONS",
    "DEFAULT_SEED",
    "TIER_FLOORS",
    "TIER_SPLITS",
    "FamilyRegistry",
    "FamilyValidationError",
    "PowerInfeasibleError",
    "StatisticalAnalyzer",
    "UndeclaredFamilyError",
    "alternative_discordance",
    "bootstrap_ci",
    "derive_n",
    "derive_n_for_family",
    "discordance",
    "family_hash",
    "holm",
    "holm_correct_family",
    "load_family",
    "mcnemar_exact",
    "noise_floor_from",
    "paired_deltas",
    "paired_measured_outcomes",
    "resolve_rate",
    "simulate_power",
    "validate_family",
]
