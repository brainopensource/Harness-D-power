---
status: normative
updated: 2026-07-31
---

# ADR-0023: The Port-Rent Rule — Ports Pay Rent in Adapters

**Status**: Accepted
**Date**: 2026-07-31

## Context

[ADR-0019](./0019-port-consolidation.md) deletes four Protocols that had zero adapters, zero call
sites, and zero importers. That is a cleanup. Without a standing rule it is also a cleanup that
will be needed again, because nothing in the process prevented those Protocols from accumulating in
the first place.

The pressure is structural, not careless. A hexagonal architecture makes adding a port feel free:
it is a Protocol, it costs a few dozen lines, and it documents an intention. But an unbacked port
is not free. It is contract surface that `test_port_shape.py` must satisfy, that a reader must
learn, that a retrieval index will surface as though it were real, and that a future contributor
will treat as a commitment. `docs/STATUS.md` reported "24 ports backed by 4 adapters" as progress;
read honestly, that ratio was the problem.

The same failure mode produced the docs overshoot in Phase 0 — mass accumulating because nothing
mechanically opposed it — and the fix has the same shape: a ratchet, not an intention.

## Decision

**A port that ships zero non-test adapters for two consecutive blocks is automatically demoted to
`experimental` and enters deletion review.**

* **The clock.** Counted in phases (`v2-S<n>`), starting from the phase in which the port was
  introduced or last had an adapter land. Two consecutive phases with no non-test adapter triggers
  it.
* **"Non-test" is load-bearing.** A fake or in-memory adapter written to satisfy a conformance
  suite is not evidence of demand. It is evidence the Protocol is implementable, which was never
  the question.
* **Demotion is automatic; deletion is not.** Demotion to `experimental` happens by rule. Deletion
  is a review with a written outcome: delete, or state the phase in which an adapter lands and what
  blocks it until then. **A port may be kept, but not silently.**
* **Deletion follows ADR-0019's discipline.** Record the re-promotion condition. A deleted port is
  a decision that can be revisited on evidence, not an idea that was rejected.
* **Exemption: ports the TCB requires.** `PolicyEngine`, `Evaluator`, and `ResourceGovernor` are
  structural regardless of adapter count. They are the boundary, not a bet on one.

`ports/meta_improver.py` is the first named subject: dormant per
[ADR-0022](./0022-rhi-economic-refounding.md), kept deliberately, and now kept *under a rule* rather
than by inattention.

## Consequences

**Easy.** "Should we add a port for this?" gets a cheap answer: add it, and if nothing implements it
in two phases it leaves on its own. The rule makes speculative ports safe to try precisely because
it makes them unsafe to forget.

**Hard.** Somebody must run the check. It is a candidate for a CI script — walk `ports/`, count
non-test implementers, compare against a phase-stamped introduction date — and should become one
once the phase stamp has a machine-readable home. Until then it is a phase-exit checklist item,
which is weaker and is stated here as a known gap rather than assumed away.

**Foreclosed.** Ports as documentation of intent. If an interface exists to communicate a plan, the
plan belongs in an ADR or in `STATUS.md` — both of which are read as plans, and neither of which a
retrieval index will surface as an implemented contract.

**Risk accepted.** A genuinely useful port could be deleted a phase before its adapter arrives. The
written re-promotion condition makes restoring it a `git revert` plus a note, and the port was by
definition unused during the window.

## Reversal Conditions

* **Deletion churn.** If more than one port is deleted and then re-promoted within a year, two
  phases is too short a window and the clock should be lengthened rather than the rule abandoned.
* **The rule is never triggered.** If no port is ever demoted, either the discipline is working
  upstream — in which case keep it as the reason it is working — or nobody is running it, in which
  case automate it or delete this ADR. **A governance rule nobody executes is worse than none**, as
  it creates false confidence that the surface is being managed.
* **The architecture stops being hexagonal.** If ports cease to be the primary extension mechanism,
  this rule's premise goes with them.

## Related

[ADR-0019](./0019-port-consolidation.md) (the consolidation this rule prevents repeating) ·
[ADR-0022](./0022-rhi-economic-refounding.md) (`meta_improver` dormancy) ·
[Port Stability & Versioning](../03-contracts-and-models/port-stability-and-versioning.md) ·
[Hexagonal Ports](../03-contracts-and-models/hexagonal-ports.md)
