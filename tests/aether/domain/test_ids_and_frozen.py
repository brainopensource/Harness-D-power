"""Frozen base class: immutability, closed schema, tz-aware datetimes."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from aether.domain.gate import GateReport, GateStatus
from aether.domain.ids import Frozen, SpanId
from aether.domain.taint import Provenance, TaintSpan


class _Dummy(Frozen):
    value: int


def test_frozen_model_is_immutable() -> None:
    instance = _Dummy(value=1)
    with pytest.raises(ValidationError):
        instance.value = 2  # type: ignore[misc]


def test_frozen_model_forbids_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        _Dummy(value=1, extra_field="not allowed")  # type: ignore[call-arg]


def test_taint_span_requires_tz_aware_datetime() -> None:
    with pytest.raises(ValidationError):
        TaintSpan(
            span_id=SpanId("s1"),
            label=Provenance.AGENT,
            text="hello",
            source="test",
            created_at=datetime.now(),  # naive — must be rejected
        )


def test_taint_span_accepts_tz_aware_datetime() -> None:
    span = TaintSpan(
        span_id=SpanId("s1"),
        label=Provenance.AGENT,
        text="hello",
        source="test",
        created_at=datetime.now(UTC),
    )
    assert span.created_at.tzinfo is not None


def test_gate_report_none_status_carries_instrument_error() -> None:
    report = GateReport(
        gate="tests_unmodified",
        status=GateStatus.NONE,
        instrument_error="exit-127",
    )
    assert report.status is GateStatus.NONE
    assert report.instrument_error == "exit-127"
