"""BudgetDims: integer-only arithmetic by type."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from aether.domain.budget import Actuals, BudgetDims, Lease
from aether.domain.ids import LeaseId, RunId


def test_budget_dims_defaults_are_zero_ints() -> None:
    dims = BudgetDims()
    assert dims.usd_micros == 0
    assert dims.prompt_tokens == 0
    assert dims.completion_tokens == 0
    assert dims.wall_clock_ms == 0
    assert dims.concurrency_slots == 0


def test_budget_dims_rejects_float() -> None:
    with pytest.raises(ValidationError):
        BudgetDims(usd_micros=1.5)  # type: ignore[arg-type]


def test_budget_dims_is_frozen() -> None:
    dims = BudgetDims(usd_micros=10)
    with pytest.raises(ValidationError):
        dims.usd_micros = 20  # type: ignore[misc]


def test_lease_carries_optional_parent_for_fanout() -> None:
    lease = Lease(
        lease_id=LeaseId("lease-1"),
        run_id=RunId("run-1"),
        reserved=BudgetDims(usd_micros=100),
        parent=LeaseId("lease-0"),
        issued_at=datetime.now(UTC),
    )
    assert lease.parent == LeaseId("lease-0")


def test_actuals_wraps_budget_dims() -> None:
    actuals = Actuals(dims=BudgetDims(prompt_tokens=42))
    assert actuals.dims.prompt_tokens == 42
