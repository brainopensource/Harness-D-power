"""Capability control — see docs/03-contracts-and-models/domain-schemas.md#control.

`Grant` never crosses a port signature — see docs/02-architecture/car-model.md. It is defined
here as a domain model because it is still data (minted, stored, and correlated by id), but no
`sagiha.ports` module may reference it as a parameter or return type. Enforced by
tests/contracts/test_port_shape.py::test_no_grant_in_any_public_signature.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

TaskStatus = Literal[
    "submitted", "working", "input-required", "auth-required", "completed", "failed", "canceled"
]
"""Mirrors the A2A task lifecycle so a remote pilot needs no translation layer."""


class Grant(BaseModel):
    """Unforgeable capability token, scoped to tool and paths, with expiry.

    Minted only by `PolicyEngine`. Held only inside `kernel/dispatch.py`. Possession confers
    nothing; reachability is the control, enforced by module structure plus import-linter.
    """

    model_config = ConfigDict(frozen=True)

    grant_id: str
    tool_name: str
    scope_paths: tuple[str, ...]
    run_id: str  # binds to one run; prevents cross-run reuse
    issued_at: datetime
    expires_at: datetime


class Decision(BaseModel):
    model_config = ConfigDict(frozen=True)

    allowed: bool
    reason: str
    requires_human: bool = False
    grant_id: str | None = None  # correlation only — the Grant itself never leaves dispatch


class RunContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    autonomy_level: Literal["interactive", "hybrid", "autonomous", "scheduled"]
    workspace_root: str  # opaque identifier, not a Path
    budget_remaining_usd: float
    #: Git sha captured before step 1, and the ref every coding gate diffs against.
    #: Optional so existing callers and recorded contexts stay valid; the gates fail
    #: closed when it is absent, because "no base ref" means "cannot evaluate", never
    #: "passed" (H1).
    base_commit: str | None = None


FreezeReason = Literal["budget", "failover", "interrupt", "checkpoint"]
"""Why a run stopped. One mechanism, and these are its callers — see
docs/03-contracts-and-models/frozen-run-state.md."""


class FrozenRunState(BaseModel):
    """The serializable form of a paused run — see docs/03-contracts-and-models/frozen-run-state.md.

    A run that must stop (budget exhausted, provider failing over, a human interrupting)
    needs to stop **without losing its work and without leaking its authority**.

    ## The grants-absent invariant

    **No field here is `Grant`-typed, and no field transitively contains a `Grant`.** That is
    not stylistic. A grant is a short-lived, scoped authorization minted at the moment of
    use; serializing one to disk converts it into a long-lived bearer token whose scope
    outlives the conditions it was issued under, and a thaw hours later would replay
    authority the policy engine would no longer grant. Freezing state is not a reason to
    freeze permission.

    Thaw therefore **re-authorizes on demand**: rebuild the kernel, re-materialize the
    workspace at `worktree_ref`, and mint fresh grants against current policy as the run
    proceeds. A thawed run that can no longer do what it could before is behaving correctly.

    Enforced, not asserted:
    `tests/contracts/test_port_shape.py::test_no_grant_in_frozen_run_state`.

    ## What is deliberately *not* here

    The `TaskSpec`. `domain/work.py` imports this module, so referencing `TaskSpec` here
    would be an import cycle — but the constraint points at the right design anyway: the
    task is already durable in `TrajectoryStore`'s `RunRecord`, and a second copy on disk is
    a second thing that can disagree. `task_id` plus `run_id` recover it.
    """

    model_config = ConfigDict(frozen=True)

    run_id: str
    task_id: str
    autonomy_level: Literal["interactive", "hybrid", "autonomous", "scheduled"]
    workspace_root: str
    budget_remaining_usd: float
    #: Git ref the workspace is re-materialized at on thaw. `None` for a run in the
    #: primary checkout rather than an allocated worktree.
    worktree_ref: str | None = None
    #: The ref the coding gates diff against. Preserved across freeze/thaw: re-checkpointing
    #: on thaw would measure the diff against the agent's own prior work and gate nothing.
    base_commit: str | None = None
    #: `seq` the resumed loop starts from — the high-water mark already in the trajectory.
    next_seq: int = 1
    #: Anchored state that must survive the process, mirroring `AnchoredState`'s mutable
    #: half. The transcript itself is not here: it is in `TrajectoryStore`, and duplicating
    #: it would make the freeze file the larger, staler copy.
    plan: tuple[str, ...] = ()
    open_files: tuple[str, ...] = ()
    #: T7 taint, carried across the freeze. Monotonic means monotonic: a run does not
    #: launder its taint by stopping and starting, which would make freeze/thaw an untaint
    #: primitive and hand an attacker the bypass the gate exists to close.
    tainted: bool = False
    frozen_at: datetime
    reason: FreezeReason = "checkpoint"

    def to_run_context(self) -> RunContext:
        """Rebuild the `RunContext` a thawed run resumes under.

        Note what is reconstructed rather than restored: authority. The context carries
        scope and budget; every grant is minted fresh against current policy.
        """
        return RunContext(
            run_id=self.run_id,
            autonomy_level=self.autonomy_level,
            workspace_root=self.workspace_root,
            budget_remaining_usd=self.budget_remaining_usd,
            base_commit=self.base_commit,
        )
