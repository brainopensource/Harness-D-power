---
status: rationale
updated: 2026-08-06
---

# Benchmark Results

**This directory is empty of results, and that is the correct state.** No valid benchmark
number has ever been produced by this project — see [`../../measurement.md`](../measurement.md) §1.

It exists because several gates are keyed to it and **a gate keyed to a path must select
something**. Before this README, [ADR-0001](../decisions/0001-python-first-compiled-on-trigger.md),
[ADR-0002](../decisions/0002-no-number-before-the-floor.md),
[`agile/milestones.md`](../agile/milestones.md),
[`agile/backlog.md`](../agile/backlog.md) and
[`agile/sprints/sprint-01.md`](../agile/sprints/sprint-01.md) all published results into a
directory that did not exist — six inbound references to nothing.

## What lands here, and what unblocks it

| File | Content | Blocked on |
| :--- | :--- | :--- |
| `noise-floor.md` | The A/A variance floor. **Until this holds a real number the project publishes no capability number at all** (ADR-0002) | B1, B2, **B4** |
| `performance_timers.md` | Worktree creation and AST parse-and-validate latencies. These two numbers decide ADR-0001's F1 fork | The first working slice (M1a) |
| `lift-<manifest-hash>.md` | Paired lift against the pinned baseline, with CI, cost per resolved task, and both absolutes | The floor |

## Rules

- **A file here is a measurement, never an estimate.** A number that was not taken on our own
  instruments does not appear in this directory in any form.
- **Every result names its instrument**: manifest hash, model fingerprint, topology hash,
  container digests, `uv.lock` hash, seed — the reproducibility tuple from
  [`architecture/tech_stack_and_infra.md`](../architecture/tech_stack_and_infra.md) §5.
- **A run that shows nothing is recorded as showing nothing.** That rule is the one that would
  have saved the predecessor, and an empty directory is not the same artifact as a null result.
- Results are `status: rationale` — they are evidence, not contracts. What a result *changes*
  becomes an ADR.
