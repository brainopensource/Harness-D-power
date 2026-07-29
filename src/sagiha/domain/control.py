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
