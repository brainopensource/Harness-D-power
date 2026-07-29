---
status: normative
updated: 2026-07-29
---

# **Error Taxonomy & Recovery Semantics**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Why This Module Exists**

An autonomous agent runs for hours against flaky networks, rate limits, crashing language servers, and its own bad patches. Without a specified failure model, every adapter invents its own — some raise, some return `None`, some retry forever — and the agent's most common real-world experience becomes undefined behavior.

Two rules govern everything below:

1. **Errors are typed domain objects, never bare strings.** A string error cannot be routed, retried, or reasoned about by the model.
2. **Every failure resolves to one of four dispositions**: `RETRY`, `DEGRADE`, `SURFACE`, or `ABORT`. There is no fifth, and no error may be silently swallowed.

## **Hierarchy**

```
SagihaError
├── ControlError          — policy, budget, and authority
│   ├── PolicyDenied           (ABORT this call, SURFACE to model)
│   ├── GrantExpired           (RETRY once with a fresh grant)
│   ├── GrantScopeViolation    (ABORT, SURFACE — a real bug or an attack)
│   ├── BudgetExhausted        (ABORT run, escalate to human)
│   └── ApprovalDenied         (ABORT this path, SURFACE — model must replan)
├── ModelError            — provider-side
│   ├── RateLimited            (RETRY, honor Retry-After)
│   ├── ProviderUnavailable    (RETRY with backoff, then DEGRADE to fallback)
│   ├── ContextOverflow        (DEGRADE: compact, then retry once)
│   ├── ContentFiltered        (SURFACE — the model must rephrase)
│   └── MalformedToolCall      (SURFACE with the schema error, max 2 repairs)
├── RuntimeError_         — execution surface
│   ├── SandboxUnavailable     (RETRY once, then ABORT run)
│   ├── CommandTimeout         (SURFACE — often a legitimate finding)
│   ├── EditRejected           (SURFACE with per-hunk detail — expected, not exceptional)
│   └── WorktreeConflict       (DEGRADE: re-materialize or reallocate)
├── AdapterError          — infrastructure behind a port
│   ├── AdapterUnavailable     (DEGRADE to fallback adapter)
│   ├── IndexStale             (DEGRADE: serve stale, trigger re-index)
│   └── ConformanceViolation   (ABORT — an adapter broke its contract)
└── TaskError             — the work itself
    ├── AcceptanceUnmet        (normal terminal state, not an exception)
    └── UnrecoverableLoop      (ABORT, checkpoint for diagnosis)
```

`EditRejected` deserves emphasis: a failed patch is an **ordinary, expected event** in agent operation, not an exceptional condition. It carries per-hunk detail precisely so the model can repair it, and treating it as an exception is how harnesses end up aborting runs that were one retry from succeeding.

## **Retry Policy**

Only transient classes retry. Everything else surfaces immediately — retrying a `PolicyDenied` is not resilience, it is a loop.

| Class | Attempts | Backoff |
| :--- | :--- | :--- |
| `RateLimited` | 5 | `Retry-After` when present, else exponential + full jitter |
| `ProviderUnavailable` | 3 | 1s → 4s → 16s, full jitter |
| `SandboxUnavailable` | 1 | 2s |
| `GrantExpired` | 1 | immediate |
| everything else | 0 | — |

**Full jitter, not fixed backoff.** Parallel candidate exploration means *k* agents hit the same provider simultaneously; unjittered retries synchronize them into a thundering herd that reproduces the rate limit it was meant to escape.

Retries consume budget and are counted in the trajectory. A run that spends 40% of its tokens on retries is failing, even if it eventually succeeds, and the metric should say so.

## **Circuit Breakers**

Per adapter, per provider. After N consecutive failures the breaker opens, the adapter is marked unavailable, and calls degrade immediately rather than each paying full timeout.

| State | Behavior |
| :--- | :--- |
| Closed | Normal |
| Open | Fail fast, no call attempted (60s) |
| Half-open | One probe; success closes, failure re-opens |

Breaker state is `ResourceGovernor`-scoped, so parallel runs share it. Without shared state, ten concurrent runs each independently rediscover that a provider is down — ten times the wasted timeout.

## **Degradation Ladder**

Degradation is always toward **reduced capability with correct results**, never toward plausible-looking wrong ones.

| Component | Degrades to | Agent-visible consequence |
| :--- | :--- | :--- |
| LSP server | Tree-sitter syntax check only | Type errors surface later, at test time |
| Dense retrieval | BM25 lexical only | Broader recall, worse ranking |
| Code graph | Direct imports only, no closure | Parallel decomposition disabled → serialize |
| Episodic memory | Empty recall | No cross-session context |
| AOI models | Deterministic policy | No learned routing or early stop |
| Primary provider | Configured fallback | Different cost and latency profile |

Every degradation emits a `DegradationEvent`, appears in the trajectory, and is reported in the run summary. **A silent degradation is a correctness bug**: a benchmark run where retrieval quietly failed produces a number that means nothing, and the RHI loop would then attribute the regression to whatever it happened to be testing.

Two components have **no** degraded mode and abort instead: the `PolicyEngine` and the `Evaluator`. Running without policy or grading against a broken evaluator is worse than not running.

## **What the Model Sees**

Errors surfaced to the model are `ToolResult` objects with `success=false` and actionable content — never stack traces, which waste context and invite the model to debug the harness instead of the task:

```
EditRejected: 2 of 3 hunks failed in src/auth.py
  hunk 2: anchor not found — 'def validate_token(self, tok:'
           (file has 'def validate_token(self, token:')
  hunk 3: skipped, follows failed hunk
Applied: hunk 1. File is syntactically valid.
```

Harness-internal faults (`ConformanceViolation`, `AdapterUnavailable`) are **not** surfaced as task failures. They abort or degrade, and the model is told capability changed — not handed an infrastructure problem it cannot fix and will burn tokens attempting.

## **Human Escalation**

`BudgetExhausted`, repeated `UnrecoverableLoop`, and `SandboxUnavailable` after retry escalate through the same durable `ApprovalRequested` path as any gate: persisted, notified out of band, denying on timeout. The run parks rather than dying, so an operator can extend budget or fix infrastructure and resume from the last checkpoint instead of restarting.
