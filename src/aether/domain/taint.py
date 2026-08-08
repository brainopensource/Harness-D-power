"""Provenance labels and context spans (ADR-0015)."""

from __future__ import annotations

from enum import StrEnum

from pydantic import AwareDatetime

from aether.domain.ids import Frozen, SpanId


class Provenance(StrEnum):
    """Taint labels (ADR-0015). Ordering is not trust ordering; the policy
    predicate names admissible sets explicitly."""

    TRUSTED_SYSTEM = "trusted-system"
    OPERATOR = "operator"
    AGENT = "agent"
    UNTRUSTED_EXTERNAL = "untrusted-external"
    UNTRUSTED_DERIVED = "untrusted-derived"


UNTRUSTED: frozenset[Provenance] = frozenset({Provenance.UNTRUSTED_EXTERNAL, Provenance.UNTRUSTED_DERIVED})


class TaintSpan(Frozen):
    """A contiguous slice of context with a single provenance label.

    Spans are the atoms of the TaintGate; they are never merged across labels.
    """

    span_id: SpanId
    label: Provenance
    text: str
    source: str  # e.g. "issue_body", "tool:pytest", "layer:L1"
    created_at: AwareDatetime
