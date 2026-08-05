---
status: historical
updated: 2026-07-31
---
# ADR-0019: Port Consolidation — Delete Unbacked Protocols While They Are Free

**Status**: Accepted-Implemented  
**Date**: 2026-07-31  

## Context

The initial port count was stated as 21, but direct tree inspection (`grep -rn "(Protocol)" src/sagiha/ports/`) revealed **24 Protocols across 19 files**. Four Protocols had zero adapters, call sites, or importers. Removing unbacked speculative surface early avoids 10× refactoring costs later.

`tests/contracts/test_port_shape.py` discovers ports dynamically via `pkgutil` + `importlib`, allowing self-healing test execution upon deletion.

## Decision

**Consolidate target surface: 24 → 19 Protocols, 19 → 16 files.**

| Action | Port | Rationale |
| :--- | :--- | :--- |
| **Delete** | `ports/reviewer.py` | Zero adapters/imports. Semantics move to `ports/search.py` via `score()`. `ReviewReport` remains in `domain/work.py`. |
| **Delete** | `ports/embedding.py` | Zero adapters/imports. Deferred by [ADR-0014](./0014-defer-dense-retrieval.md). |
| **Edit** | `ports/memory.py` | Delete `ShortTermMemory` Protocol (unbacked). Keep `Memory`. |
| **Rewrite** | `ports/advisory.py` | Consolidate 3 Protocols into 1: `Advisory.predict(kind: PredictionKind, task, branch_id) -> Prediction` (`PredictionKind = Literal["reward", "failure", "cost_performance"]`). `PORT_VERSION = 2`. |
| **Keep** | `ports/meta_improver.py` | Dormant per Tier-C ruling ([ADR-0022](./0022-rhi-economic-refounding.md)), governed by [ADR-0023](./0023-port-rent-rule.md). |

### Re-promotion Conditions

Deleted Protocols return on evidence:
- **`Embedding`**: Re-created inside dense adapter when ADR-0014 recall@10 trigger fires. Returns to `ports/` only when a 2nd dense backend arrives.
- **`Reviewer`**: Returns as separate port if judge models require lifecycles unsuited for `CandidateSearch`.
- **`ShortTermMemory`**: Returns when an external consumer beyond in-process loop history requires it.

## Consequences

- **Easy**: Reduces v2 contract surface by 20%. `Advisory` merge replaces 3 near-identical Protocols with 1 dispatch method.
- **Hard**: None.
- **Foreclosed**: Speculative interface definitions without implementations.

## Reversal Conditions

- A second implementation appears for a deleted Protocol.
- Protocol recount diverges from target (19).
- `PredictionKind` variants diverge structurally, requiring Protocol re-splitting.

## Related

[ADR-0014](./0014-defer-dense-retrieval.md) · [ADR-0022](./0022-rhi-economic-refounding.md) · [ADR-0023](./0023-port-rent-rule.md) · [Port Stability & Versioning](../03-contracts-and-models/port-stability-and-versioning.md) · [Hexagonal Ports](../03-contracts-and-models/hexagonal-ports.md)
