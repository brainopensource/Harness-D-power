---
status: normative
updated: 2026-07-31
---
# **FrozenRunState**

A run that must stop — budget exhausted, provider failing over, a human interrupting — needs to
stop **without losing its work and without leaking its authority**. `FrozenRunState` is the
serializable form of a paused run.

## Schema lives in `src/`

Per [Contracts to Code](../implementation/contracts-to-code.md), this page defines nothing. The
schema is `FrozenRunState` in **`src/sagiha/domain/control.py`**. Code wins.

## The grants-absent invariant

**No field of `FrozenRunState` is `Grant`-typed, and no field transitively contains a `Grant`.**

A capability grant is a short-lived, scoped authorization minted by the PolicyEngine at the moment
of use. Serializing one to disk converts it into a long-lived bearer token whose scope outlives the
conditions it was granted under — and a thaw hours later would replay authority the policy engine
would no longer issue. Freezing state is not a reason to freeze permission.

Thaw therefore **re-authorizes on demand**: rebuild the kernel, re-materialize the workspace at
`worktree_ref`, and mint fresh grants against current policy as the run proceeds. A thawed run that
can no longer do what it could before is behaving correctly.

This is enforced, not asserted: the existing `test_no_grant_in_any_public_signature` contract test
extends to assert it over every `FrozenRunState` field.

## Consumers

Budget-park (the run stops at its cap and can resume when funded), provider failover, and the
`v2-S7` interactive interrupt. One mechanism, three callers — which is why it is a domain model
rather than a feature of any one of them.

**Proving test:** freeze → `kill -9` → thaw → identical final `GateReport`, three times.

*Lands `v2-S3` (PR-3.4).*
