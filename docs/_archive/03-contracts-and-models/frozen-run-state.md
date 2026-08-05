---
status: historical
updated: 2026-07-31
---
# **FrozenRunState**

`FrozenRunState` is the serializable state of a paused run (budget cap reached, provider failover, interactive interrupt).

## **Schema Location**

Defined in `src/sagiha/domain/control.py`. See [Contracts to Code](../implementation/contracts-to-code.md).

## **Grants-Absent Invariant**

**`FrozenRunState` contains no `Grant` instances directly or transitively.**

Capability grants are short-lived tokens minted at point-of-use. Serializing grants converts them into long-lived bearer tokens that outlive their authorization conditions.

On thaw, the kernel **re-authorizes on demand**: re-materializes workspace at `worktree_ref` and mints fresh grants against current policy. Enforced via `test_no_grant_in_any_public_signature`.

## **Consumers & Verification**

* **Consumers**: Budget-park, provider failover, `v2-S7` interactive interrupt.
* **Proving test**: freeze → `kill -9` → thaw → identical final `GateReport` (3x).
* Lands `v2-S3` (PR-3.4).
