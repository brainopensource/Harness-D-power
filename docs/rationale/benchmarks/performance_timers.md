---
status: rationale
updated: 2026-08-07
---

# F1 Performance Timers — Worktree Creation & AST Parse-and-Validate

[ADR-0001](../../decisions/0001-python-first-compiled-on-trigger.md) names these two timers
as the measurement that settles the Python-vs-Rust (F1) fork, against triggers RT-1/RT-2/RT-3.
This is the first real run, produced by `TASK-021`.

## Method

- **Script**: `src/aether/measurement/timers.py`, run via `python -m aether.measurement.timers`.
- **Worktree creation**: wraps `GitCliWorktreeManager.create()` (`src/aether/adapters/workspace/git_cli.py`,
  TASK-017) — `time.perf_counter()` around one `git worktree add --detach` call per rep, on a
  throwaway repo seeded with `src/aether/domain/`'s `.py` files (9 files) committed once.
- **AST parse-and-validate**: wraps `TreeSitterIndexer.build()` (`src/aether/adapters/indexer/tree_sitter.py`)
  — parses every `.py` file in one created worktree with `tree-sitter` + `tree-sitter-language-pack`,
  extracting top-level function/class symbols.
- **Reps**: 10 per operation, sequential (no warmup discard — first-rep cost is part of the number).
- **Hardware**: recorded per run by the script itself (`platform.processor()`/`os.cpu_count()`).

## Result (2026-08-07)

**Hardware**: x86_64, 16 logical CPUs, Linux 6.18.33.2-microsoft-standard-WSL2 (WSL2, ext4-backed
worktree root under `/tmp`).

| Operation | Reps | Mean | p95 |
| :--- | :---: | :---: | :---: |
| Worktree creation | 10 | 8.42 ms | 9.12 ms |
| AST parse-and-validate (9 files) | 10 | 1.04 ms | 1.43 ms |

## Comparison against RT-1/RT-2/RT-3

| Trigger | Threshold | This measurement | Crossed? |
| :--- | :--- | :--- | :--- |
| RT-1 | Cold index > 10 min on 1M LOC, after worker-process parallelism | Not measured at 1M-LOC scale — 9-file sample only | Not applicable at this sample size |
| RT-2 | RSS > 300 MB, or idle CPU > 1%, attributable to interpreter overhead | Not instrumented by this script (no RSS/idle-CPU sampling here) | Not measured |
| RT-3 | Incremental single-file re-index > 200 ms | AST parse-and-validate mean 1.04 ms, p95 1.43 ms — two orders of magnitude under threshold | **Not crossed** |

Worktree creation itself carries no named RT threshold (ADR-0001's own text calls `<10 ms`
"already free on a reflink-capable host" without promoting it to a numbered trigger) — recorded
here as context: 8.42 ms mean is consistent with that expectation on this filesystem.

## Reading this result

Per ADR-0001's Reversal Conditions: "a measured number crossing RT-1, RT-2 or RT-3 ... promotes
exactly the component that crossed it — never the whole core." RT-3, the one trigger this sample
size can actually speak to, is **not crossed** — AST parse-and-validate on a small repo is roughly
140x under the 200 ms single-file re-index threshold. This is a real, settled "no bottleneck"
result at this scale, not an unmeasured gap: it does not promote the indexer to a compiled
sidecar. RT-1 and RT-2 require a 1M-LOC corpus and RSS/idle-CPU instrumentation this sprint's
9-file sample does not provide, and are left open rather than claimed either way — recording that
gap honestly is part of what this document is for.
