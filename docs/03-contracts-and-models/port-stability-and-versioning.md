---
status: rationale
updated: 2026-07-29
retrieval: excluded
---
# **Port Stability & Versioning**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Why This Module Exists**

The ports *are* the product. A framework whose contracts move without notice teaches its extenders to
stop upgrading, and it teaches them once — the second time an adapter breaks silently, they vendor a
fork and stop tracking upstream.

This file is the contract about the contracts: what is public, what stability it carries, how a
breaking change is made, and how recorded data survives it.

## **Public API Surface**

Exactly three things are public and carry the stability guarantees below:

| Public | Not public |
| :--- | :--- |
| `sagiha.ports.*` — the Protocols | `sagiha.kernel.*` — dispatch, orchestrator internals |
| `sagiha.domain.*` — models crossing ports | `sagiha.adapters.*` — first-party implementations |
| Declared entry-point group names | Anything under a `_`-prefixed module |

`sagiha.adapters` is deliberately excluded. First-party adapters are implementations, not interfaces;
depending on one directly is depending on a detail. Extend by implementing the port.

## **What Counts as Breaking**

Applied to a `Protocol`, the usual intuitions invert. A Protocol is implemented by parties you do not
control, so **adding a method is a breaking change** — every existing adapter stops satisfying it.

| Change | Semver | Note |
| :--- | :--- | :--- |
| Add a method to a port | **major** | Breaks every existing adapter |
| Remove or rename a method | **major** | |
| Add a required parameter | **major** | |
| Narrow a parameter type / widen a return type | **major** | |
| Add a **required** field to a payload model | **major** | |
| Add an optional parameter with a default | minor | |
| Add an optional field to a payload model | minor | |
| Widen a parameter type / narrow a return type | minor | |
| Add a new port | minor | Nothing implemented it yet |
| Add a variant to a discriminated union | **major** | Exhaustive consumers stop being exhaustive |
| Docstring, rationale, internals | patch | |

The union row is the one that surprises people. Adding a `ContentBlock` kind breaks every consumer
that matched exhaustively over the union — which, under pyright strict, is all of them.

## **Deprecation Policy**

No port method is removed or changed incompatibly without passing through deprecation:

1. **Announce** — the replacement ships in the same release; the old method is marked deprecated in
   the docstring and the changelog names the migration.
2. **Warn** — one full minor release emits `DeprecationWarning` at call time. Minimum **90 days**.
3. **Remove** — at the next major.

Emergency exception: a contract that is a security defect may skip step 2. It still gets an entry in
the changelog explaining why, because an unexplained emergency is indistinguishable from carelessness.

## **Port Version Declaration**

Each port module declares a major version:

```python
# sagiha/ports/indexer.py
PORT_VERSION = 2
```

An extension declares which major it implements. The composition root compares and **refuses a
mismatch at startup**, naming the port, the expected version, and the offending extension. Failing at
composition is the whole point: the alternative is an `AttributeError` at first dispatch, forty
minutes into an autonomous run.

## **Data Schema Versioning**

Contracts govern code. `schema_version` governs recorded data, and the two evolve independently.

The `events` table and cassette headers each carry `schema_version: int`, **versioned per event type
rather than globally** — bumping `ToolCallRequested` must not invalidate cassettes containing only
model calls.

### Replay compatibility window

The *policy* below is the ADR-0012 target. The CLI gate that enforces it —
`sagiha replay --verify-all` — is **Planned — Sprint 3** ([STATUS.md](../STATUS.md)); graded
fidelity (L0/L1/L2) is defined in the [foundation review](../rationale/done/2026-07-29-foundation-review.md#11-measurement-plan).

`sagiha replay --verify-all` asserts byte-for-byte step-sequence equality against recorded cassettes
at fidelity L2 for `replay_relevant` events; earlier Sprint 3 work targets L1 digest matching first.

* The current major reads **all** `schema_version`s it has ever written, via upcasters.
* An **upcaster** is a pure function `v(n) → v(n+1)` in `sagiha/domain/upcasters.py`, chained on read.
  Recorded data is never rewritten in place — the store is append-only, and mutating history to fix a
  schema is the same defect as mutating a trajectory to fix a score.
* Every upcaster ships with a round-trip test over a real recorded fixture.
* A major release may drop upcasters older than **two majors**, announced in the changelog. Cassettes
  beyond the window are re-recorded, which is a cost the harvester makes cheap by design.

### Trajectory retention

Trajectories are the training substrate for the outer loop and the audit record for everything else.
They outlive the code that produced them, which is why the format is versioned data rather than
pickled objects, and why upcasting is a first-class module instead of a migration script.

## **Stability Tiers**

Not every port is equally settled, and pretending otherwise is how a 1.0 becomes a lie.

**No port in this suite is `stable` today.** A stability label is evidence about adapters that
exist, not aspiration about a design that is believed correct — and as of this writing every port
has at most one first-party implementation (often only a cassette or in-memory stub). Marking
`ModelProvider` or `Workspace` `stable` while `ModelRequest` cannot yet describe a real request
(see the foundation review) was a lying label, not an optimistic one — corrected 2026-07-30.

This project uses three tiers, not four. An earlier draft of this page introduced a fourth name,
`Draft`, for what is really `Provisional` pre-graduation; that was reverted to keep one vocabulary
with the comparative analysis and the port stability discussion in the Sprint 0 decision record.

| Tier | Meaning | Ports |
| :--- | :--- | :--- |
| **Provisional** | At most one implementation; signature may change at any minor without a deprecation cycle | `ModelProvider`, `Workspace`, `ShortTermMemory`, `ToolRegistry`, `TrajectoryStore`, `PolicyEngine`, `ResourceGovernor`, `Orchestrator`, `Toolchain`, `CodeGraph`, `Indexer`, `LSPAdapter`, `CandidateSearch`, `Reviewer`, `Evaluator` |
| **Experimental** | No guarantee; may be removed | AOI ports (`RewardPredictor`, `FailurePredictor`, `CostPerformanceEstimator`), `MetaImprover`, `EmbeddingProvider` |

Each port module states its tier next to `PORT_VERSION` as the literal `STABILITY` string —
`"provisional"` or `"experimental"` (`"stable"` is reserved for a port that has actually graduated;
none has). This table is hand-maintained today; generating it from the `STABILITY` declarations and
`--check`-ing it in CI, the same pattern `scripts/gen_event_catalog.py` already uses for events, is
tracked as Sprint 3b hygiene rather than done here.

A port graduates from **Provisional** to **Stable** — and only then does the full deprecation policy
above apply — when at least two independent adapters implement it and the conformance suite has been
stable for one minor release: evidence, not calendar. Until that graduation, treat every signature in
this suite as subject to change without notice.

## **Pre-1.0**

Until 1.0 the project is Provisional throughout: minors may break, and the changelog says so. What
does **not** change before 1.0 is the *process* — every break is announced, dated, and given a
migration note. A project that skips that discipline early never acquires it later.
