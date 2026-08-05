---
status: historical
updated: 2026-07-29
---
# **Error Taxonomy & Recovery Semantics**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Core Rules**

1. **Errors are typed domain objects**, never bare strings.
2. **Four Dispositions**: Every failure resolves to `RETRY`, `DEGRADE`, `SURFACE`, or `ABORT`. Swallowing errors is prohibited.

## **Hierarchy**

```
SagihaError
├── ControlError          — policy, budget, and authority
│   ├── PolicyDenied           (ABORT call, SURFACE to model)
│   ├── GrantExpired           (RETRY once with fresh grant)
│   ├── GrantScopeViolation    (ABORT, SURFACE — bug or attack)
│   ├── BudgetExhausted        (ABORT run, escalate to human)
│   └── ApprovalDenied         (ABORT path, SURFACE — model replans)
├── ModelError            — provider-side
│   ├── RateLimited            (RETRY, honor Retry-After)
│   ├── ProviderUnavailable    (RETRY with backoff, DEGRADE to fallback)
│   ├── ContextOverflow        (DEGRADE: compact, retry once)
│   ├── ContentFiltered        (SURFACE — model rephrases)
│   └── MalformedToolCall      (SURFACE schema error, max 2 repairs)
├── RuntimeError_         — execution surface
│   ├── SandboxUnavailable     (RETRY once, ABORT run)
│   ├── CommandTimeout         (SURFACE — operational finding)
│   ├── EditRejected           (SURFACE per-hunk detail — expected operational event)
│   └── WorktreeConflict       (DEGRADE: re-materialize/reallocate)
├── AdapterError          — infrastructure behind ports
│   ├── AdapterUnavailable     (DEGRADE to fallback adapter)
│   ├── IndexStale             (DEGRADE: serve stale, trigger re-index)
│   └── ConformanceViolation   (ABORT — contract broken)
└── TaskError             — execution outcome
    ├── AcceptanceUnmet        (terminal state, not exception)
    └── UnrecoverableLoop      (ABORT, checkpoint for diagnosis)
```

## **Retry Policy**

Only transient errors retry. Retries consume budget and are recorded in the trajectory.

| Class | Attempts | Backoff |
| :--- | :--- | :--- |
| `RateLimited` | 5 | `Retry-After` if set, else exponential + full jitter |
| `ProviderUnavailable` | 3 | 1s → 4s → 16s, full jitter |
| `SandboxUnavailable` | 1 | 2s |
| `GrantExpired` | 1 | Immediate |
| Everything else | 0 | — |

*Full jitter is required across parallel candidates to prevent thundering herd problems.*

## **Circuit Breakers**

Scoped per adapter/provider within the `ResourceGovernor`.

| State | Behavior |
| :--- | :--- |
| Closed | Normal operation |
| Open | Fail fast without call attempt (60s cooldown) |
| Half-open | Single probe; success closes, failure re-opens |

## **Degradation Ladder**

Degradation reduces capability while preserving result correctness. Every degradation emits a `DegradationEvent`.

| Component | Degrades to | Consequence |
| :--- | :--- | :--- |
| LSP server | Tree-sitter syntax check | Type errors surface at test time |
| Dense retrieval | BM25 lexical search | Broader recall, lower precision |
| Code graph | Direct imports only | Parallel decomposition disabled → serial |
| Episodic memory | Empty recall | No cross-session context |
| AOI models | Deterministic policy | No learned routing/early stopping |
| Primary provider | Configured fallback | Different cost/latency profile |

*Note*: `PolicyEngine` and `Evaluator` have **no** degraded mode and immediately `ABORT`.

## **Model Interface & Escalation**

* **Surfaced Errors**: Emitted as `ToolResult(success=False)` with actionable diagnostic details instead of stack traces.
* **Harness Faults**: Internal errors (`ConformanceViolation`, `AdapterUnavailable`) degrade or abort without surfacing to the model prompt.
* **Human Escalation**: `BudgetExhausted`, `UnrecoverableLoop`, and `SandboxUnavailable` (after retry) trigger durable `ApprovalRequested` events to park execution for human intervention.
