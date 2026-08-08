"""Tri-state gate outcome (measurement.md §5, B4)."""

from __future__ import annotations

from enum import StrEnum

from aether.domain.ids import Frozen


class GateStatus(StrEnum):
    """Tri-state (spec §7). NONE means *unmeasured / instrument error* and never
    silently passes — B4's typed distinction lives here."""

    PASSED = "passed"
    FAILED = "failed"
    NONE = "none"


class GateReport(Frozen):
    gate: str
    status: GateStatus
    detail: str = ""
    instrument_error: str | None = None  # populated iff status == NONE
