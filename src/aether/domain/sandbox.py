"""Container spec and result for the evaluation sandbox (B3, TASK-016).

These live in `domain/` rather than `ports/` on purpose. The sandbox is **not
a ninth port** — ADR-0005 rev. 2 ratifies eight port areas / nine protocols,
and `tests/aether/ports/test_reflection.py` gates that set exactly. The
container is an implementation detail of two existing boundaries (the TCB
`Evaluator` and, later, `ToolRegistry`), so what crosses between them is a
pair of wire-serializable payloads, not a new protocol.

Placing them here is also what makes the isolation buildable at all:
`aether-tcb-isolation` forbids `measurement.evaluator` from importing
`aether.adapters`, and `aether-layers` forbids `aether.adapters` from
importing `aether.measurement`. `domain/` is the one package both may see.
"""

from __future__ import annotations

from aether.domain.ids import Frozen

CONTAINER_WORKSPACE = "/workspace"
CONTAINER_LAYERS = "/opt/aether/layers"


class ContainerLimits(Frozen):
    """Non-budget resource caps, frozen at composition (I6).

    `BudgetDims` has no memory/CPU/pids dimension, so — unlike wall-clock,
    which is lease-derived — these cannot come from a `ResourceGovernor`
    lease today. They are stated here as composition-frozen defaults rather
    than pretended to be lease-derived; see docs/agile/sprints/sprint-03.md.
    """

    memory_mb: int = 2048
    cpu_millicores: int = 1000  # integer-only; rendered as --cpus at the CLI edge
    pids_limit: int = 512


class ContainerSpec(Frozen):
    """One evaluation container invocation. All paths are strings (I3)."""

    image_digest: str  # `sha256:<hex>` or `repo@sha256:<hex>` — never a tag (B3)
    command: str  # the manifest's pinned test command, hash-verified before we get here
    worktree_host_path: str  # RW mount source: the candidate's worktree
    layers_host_path: str | None = None  # RO mount source: pinned image layers
    timeout_ms: int = 900_000
    limits: ContainerLimits = ContainerLimits()  # Frozen => safe shared default (ruff B008)
    workdir: str = CONTAINER_WORKSPACE


class ContainerResult(Frozen):
    """What the run produced. `launch_error` is set when the container never
    ran — an instrument failure, never a test result (B4)."""

    exit_code: int = -1
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    launch_error: str | None = None
    argv: tuple[str, ...] = ()  # the exact command line, for the instrument record
