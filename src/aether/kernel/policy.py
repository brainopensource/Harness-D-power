"""DefaultPolicyEngine — TCB. Implements the one binding rule spec.md §5 states
explicitly: a request that widens capability fails closed when any span
justifying it is untrusted or untrusted-derived (I11).

This is a real, narrow implementation, not a stub. The full red-team-corpus-
verified TaintGate and Reject/AskRuleMatch/AskFailClosed escalation taxonomy
(ADR-0015, ADR-0008) is TASK-030b/TASK-030a — out of scope here.
"""

from __future__ import annotations

from aether.domain.taint import UNTRUSTED
from aether.ports.policy_engine import Decision, EffectRequest, PolicyDecision


class DefaultPolicyEngine:
    async def authorize(self, request: EffectRequest) -> PolicyDecision:
        if request.widens_capability and any(span.label in UNTRUSTED for span in request.justifying_spans):
            return PolicyDecision(
                decision=Decision.ASK_FAIL_CLOSED,
                rule_id="i11-untrusted-widen",
                rationale=(
                    "request widens capability and is justified by an untrusted or "
                    "untrusted-derived span (spec.md §5, ADR-0015 binding rule)"
                ),
            )
        return PolicyDecision(
            decision=Decision.GRANT,
            rule_id="default-grant",
            rationale="no untrusted span justifies a capability-widening effect",
        )
