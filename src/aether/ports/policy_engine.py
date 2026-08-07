"""PolicyEngine — TCB. Implementation resides in kernel/, never adapters/ (spec.md §4)."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal, Protocol, runtime_checkable

from aether.domain.ids import Frozen, RunId
from aether.domain.taint import TaintSpan


class EffectRequest(Frozen):
    run_id: RunId
    effect_class: Literal["read", "write", "shell", "network", "model", "evaluate"]
    descriptor: str  # e.g. shell string, path, model name
    justifying_spans: tuple[TaintSpan, ...]  # full spans: the gate audits labels
    widens_capability: bool  # classifier output (shell_ast / static)


class Decision(StrEnum):
    GRANT = "grant"
    REJECT = "reject"
    ASK_RULE_MATCH = "ask_rule_match"
    ASK_FAIL_CLOSED = "ask_fail_closed"


class PolicyDecision(Frozen):
    decision: Decision
    rule_id: str
    rationale: str


@runtime_checkable
class PolicyEngine(Protocol):
    """TCB. The taint predicate lives here (ADR-0015): a capability-widening
    request justified by any span in UNTRUSTED labels fails closed. Note the
    port returns a *decision*, never a Grant object — grants are kernel-internal
    (spec §4: no Grant in public signatures)."""

    async def authorize(self, request: EffectRequest) -> PolicyDecision: ...
