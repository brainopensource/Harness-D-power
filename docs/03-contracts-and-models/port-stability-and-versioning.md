---
status: rationale
updated: 2026-07-29
retrieval: excluded
---
# **Port Stability & Versioning**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Public API Surface**

| Public Surface | Non-Public Surface |
| :--- | :--- |
| `sagiha.ports.*` (Protocols) | `sagiha.kernel.*` (Orchestrator internals) |
| `sagiha.domain.*` (Cross-port models) | `sagiha.adapters.*` (First-party implementations) |
| Declared entry-point group names | `_`-prefixed modules |

## **Breaking Change Classification**

Adding methods to a `Protocol` breaks existing implementers.

| Change | Semver | Note |
| :--- | :--- | :--- |
| Add/remove/rename port method | **Major** | Breaks existing adapter implementations |
| Add required parameter / narrow param / widen return | **Major** | Protocol contract mismatch |
| Add required field to model / add union variant | **Major** | Exhaustive pattern match breaks |
| Add optional parameter or optional model field | Minor | Backward compatible |
| Widen parameter / narrow return type | Minor | Backward compatible |
| Add new port | Minor | No prior implementations |
| Docstring, rationale, internals | Patch | Documentation/internal refactor |

## **Deprecation Policy**

1. **Announce**: Docstring deprecation tag and migration path in changelog.
2. **Warn**: `DeprecationWarning` emitted at call time for **90 days** / 1 minor release.
3. **Remove**: Removed in next major release (security defects may bypass warning phase with changelog notice).

## **Port & Data Versioning**

* **`PORT_VERSION`**: Each port module exports an integer `PORT_VERSION`. Composition root rejects version mismatches at startup.
* **`schema_version`**: Event payloads and cassettes use per-event integer versioning.
* **Upcasters**: Pure transformations (`v(n) → v(n+1)`) in `sagiha/domain/upcasters.py` upcast append-only records on read without mutating history. Upcasters are retained for **two major versions**.
* **Replay Gate**: `sagiha replay --verify-all` verifies replay equality (see [STATUS.md](../STATUS.md) and [foundation review](../rationale/done/2026-07-29-foundation-review.md#11-measurement-plan)).

## **Stability Tiers**

Each port module declares `STABILITY = "provisional"` or `"experimental"`. No ports are `stable` at present.

| Tier | Scope | Ports |
| :--- | :--- | :--- |
| **Provisional** | Single implementation; signature subject to change | `ModelProvider`, `Workspace`, `ShortTermMemory`, `ToolRegistry`, `TrajectoryStore`, `PolicyEngine`, `ResourceGovernor`, `Orchestrator`, `Toolchain`, `CodeGraph`, `Indexer`, `LSPAdapter`, `CandidateSearch`, `Reviewer`, `Evaluator` |
| **Experimental** | Pre-provisional; may be removed | Advisory ports (`RewardPredictor`, `FailurePredictor`, `CostPerformanceEstimator`), `MetaImprover`, `EmbeddingProvider` |

*Graduation to Stable requires at least two independent adapter implementations and a stable conformance suite for one minor release.*

## **Pre-1.0 Policy**

Prior to 1.0, minor releases may contain breaking changes, which must be documented in the changelog with clear migration instructions.
