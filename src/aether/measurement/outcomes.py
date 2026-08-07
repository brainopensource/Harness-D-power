"""Paired-outcome models the statistics engine and the comparative rig share.

`measurement/statistics.py` is a verbatim port of the predecessor's
`e0/statistics.py`, which spoke `sagiha.domain.benchmark`'s `BenchmarkRun` /
`NoiseFloor` / `ComparisonResult`. Those types are re-expressed here — same
fields where the port depends on them, on AETHER's `Frozen` base — so the
ported algorithms can stay verbatim without dragging in a retiring package.

`TaskOutcome.resolved` is deliberately **not** `status == PASSED`. A `NONE` is
unmeasured, and B4's whole point is that it is excluded from the resolve-rate
denominator rather than counted as a failure. `resolved` answers "did this
resolve"; `measured` answers "may this task be in the denominator at all".
"""

from __future__ import annotations

from aether.domain.gate import GateStatus
from aether.domain.ids import Frozen


class TaskOutcome(Frozen):
    """One (arm, task) result. The unit the paired design pairs on."""

    task_id: str
    status: GateStatus
    wall_clock_ms: int = 0
    usd_micros: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    repair_iterations: int = 0
    detail: str = ""

    @property
    def resolved(self) -> bool:
        return self.status is GateStatus.PASSED

    @property
    def measured(self) -> bool:
        """False for `GateStatus.NONE` — an instrument failure is not a data
        point, and including one would put our own bugs in the denominator."""
        return self.status is not GateStatus.NONE


class ArmRun(Frozen):
    """One arm's pass over a manifest. The `instrument` fields are not
    decoration: `measurement.md` §6 requires a result to name its instrument,
    and a result object that cannot carry the tuple invites a report that
    omits it."""

    run_id: str
    arm_id: str
    harness_id: str
    manifest_hash: str
    split: str
    model_fingerprint: str
    seed: int
    results: tuple[TaskOutcome, ...] = ()
    topology_hash: str | None = None
    container_digest: str | None = None
    contained: bool = False


class NoiseFloor(Frozen):
    manifest_id: str
    runs_per_task: int = 2
    mean_delta: float = 0.0
    confidence_interval: tuple[float, float] = (0.0, 0.0)
    alpha: float = 0.05
    k_runs: int = 2
    n_tasks: int = 0
    seed: int = 0
    #: The discordance rates the A/A floor exists to produce. Every later
    #: family's derived N is computed from these (ADR-0003 rev. 2 §1); without
    #: them no admission run in this project can be sized.
    p01: float = 0.0
    p10: float = 0.0
    n_discordant: int = 0
    n_instrument_errors: int = 0


class ComparisonResult(Frozen):
    control_agent_id: str
    treatment_agent_id: str
    delta_pass_rate: float
    p_value: float | None
    adjusted_p_value: float | None
    n_discordant: int
    method: str
    beats_noise_floor: bool | None


__all__ = ["ArmRun", "ComparisonResult", "NoiseFloor", "TaskOutcome"]
