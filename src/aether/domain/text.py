"""Pure text helpers with no I/O (I1) — small enough to live in `domain/` and
shared by both a TCB module and a mutable one, which is exactly why they
belong here rather than in either.
"""

from __future__ import annotations

_TAIL_CHARS = 4000  # tail-biased truncation: keep the failure block, not the pass list


def tail_biased(text: str, limit: int = _TAIL_CHARS) -> str:
    """Tail-biased truncation. Test output is failure-at-the-end shaped: the
    traceback is what a reader needs, the pass list is what burns the budget.

    Moved here from `measurement/evaluator.py` (ADR-0018, T1.4): after the
    lattice change `agency/` may not import `measurement/`
    (`aether-agency-cannot-reach-the-judge`), and `agency.capabilities.sources
    .GateOutputSource` must truncate identically to the gate that produced the
    text it is reading — "the gate keeps the fuller detail for the trajectory,
    the prompt pays tokens for it" is a property of the pair, not of either
    side alone. `measurement/evaluator.py` re-exports this name for one
    release so existing callers are undisturbed.
    """
    return text[-limit:]


__all__ = ["tail_biased"]
