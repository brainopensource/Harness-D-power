---
status: normative
updated: 2026-08-05
---
# ADR-0001: Python-First; Compiled Sidecars Only on a Measured Trigger

**Status**: Accepted · **Date**: 2026-08-05 · **Fork**: F1

## Context

Two proposals disagreed. One wanted a Rust `core_rs/` with eight modules at Sprint 0, with
`<50 ns`, `<10 ms` and `0 ms` as sprint acceptance gates. The other wanted Python monoglot
with sidecars behind measured triggers, but never named a module and deferred to triggers
nobody had instrumented.

**Neither side had a measurement.** The audit found that the `<50 ns` / `<10 ms` / `0 ms`
figures are stated bare and self-contradictory — the same tree-sitter parse appears as
`<50 ns` in four places and "em milissegundos" in another. The external figures that would
justify a Sprint 0 Rust core (`<8 ms`, `<5 ms`, `<15 ms`, printed under a "Performance
Benchmarks" heading) **appear nowhere in the source they cite**. And the opposing latency
table — the load-bearing argument for the monoglot position — carries no benchmark, no
hardware and no citation either.

The archive has nothing to say about this fork. It is the only one where that is true, which
is why it needs a measurement rather than a debate.

## Decision

- **Python 3.13, monoglot.** No `core_rs/` at Sprint 0.
- **Two timers land in the first working slice**: worktree creation, and AST
  parse-and-validate. One afternoon of work, and the number picks the side.
- Compiled sidecars are admitted **per component**, never as a core, and only on a trigger
  that has been instrumented.
- **A trigger nobody has instrumented cannot fire.** Each threshold below must have a named
  measurement before it counts.

| Trigger | Threshold |
| :--- | :--- |
| **RT-1** | Cold index > 10 min on 1M LOC, after worker-process parallelism |
| **RT-2** | RSS > 300 MB, or idle CPU > 1%, attributable to interpreter overhead |
| **RT-3** | Incremental single-file re-index > 200 ms |

## Consequences

- No build step in the developer loop, and none inside the self-improvement loop.
- Invariant I3 (wire-serializable ports) is what makes this cheap to reverse per component:
  a port can move out of process without changing a caller. That invariant is now
  load-bearing and not merely tidy.
- Three checks are recorded so they are not re-litigated: `<50 ns` is the FFI crossing cost,
  not a parse; `<10 ms` worktree creation may already be free on a reflink-capable host;
  `0 ms` pool allocation is amortized and **drains under Best-of-N fan-out**, which is the
  workload it exists for.

## Reversal Conditions

A measured number crossing RT-1, RT-2 or RT-3 on real hardware, recorded in
`docs/rationale/benchmarks/`, promotes **exactly the component that crossed it** — never the
whole core.

The two timers may reverse this ADR directly. If worktree creation or AST parse-and-validate
is measurably a bottleneck at our scale, that component becomes a sidecar candidate
immediately, without waiting for RT-1/2/3.
