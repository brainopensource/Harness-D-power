---
status: normative
updated: 2026-07-31
---

# ADR-0019: Port Consolidation — Delete Unbacked Protocols While They Are Free

**Status**: Accepted
**Date**: 2026-07-31

## Context

The v2 corpus states the consolidation target as "21 → 15 ports". **That number is wrong**, and an
exit gate stated against a wrong number is unverifiable. Recounted mechanically against the tree:

```
grep -rn "(Protocol)" src/sagiha/ports/   # 24 Protocols across 19 files
```

The "21" appears to have counted files, or an older tree. The real starting point is **24
Protocols / 19 files**.

Four of those Protocols have **zero adapters, zero call sites, and zero importers** anywhere in
`src/`. They are contracts with no implementation and no consumer — pure speculative surface. Each
is currently free to delete: none is imported by `composition.py`, `run_loop.py`, `dispatch.py`, or
any adapter, so deletion breaks no execution flow. After Phase 4 writes real consumers against
them, the same change costs roughly 10× more.

`tests/contracts/test_port_shape.py` enumerates ports **dynamically** via `pkgutil` +
`importlib`, so file deletions self-heal the shape suite. No test edits are needed for removals —
which is itself evidence the suite was built correctly.

## Decision

**Target: 24 → 19 Protocols, 19 → 16 files.** State this number in the exit gate; it is checkable.

| Action | Port | Rationale |
| :--- | :--- | :--- |
| **Delete** | `ports/reviewer.py` | Zero adapters, zero external imports. The semantics that matter — a frontier judge is not a generator, and a soft score never gates admission — move to `ports/search.py` and its new `score()` method. `domain/work.py::ReviewReport` **stays**: it becomes `score()`'s return type |
| **Delete** | `ports/embedding.py` | Zero adapters, zero importers. [ADR-0014](./0014-defer-dense-retrieval.md) already defers the dense tier. A Protocol for a tier we decided not to build is a decision recorded twice, once bindingly and once speculatively |
| **Edit** | `ports/memory.py` | Delete the `ShortTermMemory` Protocol. Its adapter was removed under R7; what remains is a contract with no implementation and no consumer. `Memory` stays. Remove the now-unused `TrajectoryStep` import |
| **Rewrite** | `ports/advisory.py` | Three Protocols → one. `Advisory.predict(kind: PredictionKind, task, branch_id) -> Prediction`, with `PredictionKind = Literal["reward","failure","cost_performance"]` in `domain/work.py`. Three Protocols differing only in which scalar they predict is a taxonomy, not three contracts. `PORT_VERSION = 2`; zero adapters and zero call sites, so no breakage is possible |
| **Keep** | `ports/meta_improver.py` | Dormant per the Tier-C ruling ([ADR-0022](./0022-rhi-economic-refounding.md)). It costs 22 LOC and [ADR-0023](./0023-port-rent-rule.md) governs it |

**Re-promotion conditions.** A deleted Protocol is not a foreclosed idea. Each returns on evidence:

* **`Embedding`** — re-create it *inside* the dense adapter when ADR-0014's recall@10 trigger
  fires. It does not return to `ports/` until a second dense backend exists, because one
  implementation does not need an interface.
* **`Reviewer`** — returns as a separate port if and only if a judge model needs a lifecycle
  `CandidateSearch` cannot express. Sharing a port is correct while the judge is a scoring call.
* **`ShortTermMemory`** — returns when something other than the loop's in-process history needs it,
  which today is nothing.

## Consequences

**Easy.** The contract surface a v2 consumer must learn shrinks by a fifth. The `Advisory` merge in
particular replaces three near-identical Protocols with one dispatching call, which is what a
future AOI adapter would have had to implement three times.

**Hard.** Nothing measurable. This is the cheapest change in the plan, which is exactly why it is
sequenced now rather than later.

**Foreclosed.** Nothing. Every deletion has a written re-promotion condition, and the semantics of
each deleted Protocol are preserved somewhere concrete rather than discarded.

**Risk accepted.** Someone rebuilds a deleted Protocol from scratch in six months, unaware it
existed. Mitigated by this record — which is why the re-promotion conditions are stated rather than
implied.

## Reversal Conditions

* **A second implementation appears.** The moment any deleted Protocol has two real backends, it
  earns its interface back. One backend does not.
* **The recount was wrong.** If `grep -rn "(Protocol)" src/sagiha/ports/` does not yield 19 after
  this lands, the target was misstated again and the gate must be restated before it is claimed.
* **The `Advisory` merge leaks.** If `PredictionKind` accumulates variants whose payloads diverge
  structurally — rather than differing only in the predicted scalar — the merge was premature and
  the Protocols should split again along the real seam.

## Related

[ADR-0014](./0014-defer-dense-retrieval.md) (dense tier deferred) ·
[ADR-0023](./0023-port-rent-rule.md) (port rent) ·
[Port Stability & Versioning](../03-contracts-and-models/port-stability-and-versioning.md) ·
[Hexagonal Ports](../03-contracts-and-models/hexagonal-ports.md)
