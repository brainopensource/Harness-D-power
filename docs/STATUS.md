---
status: normative
updated: 2026-08-05
---

# STATUS

**Nothing is implemented.** `src/aether/` is empty.

That is the correct content for this file today, and it stays until a line-level code read
supports something else.

| Area | State |
| :--- | :--- |
| `src/aether/` | Empty. No ports, no domain, no kernel |
| Benchmark results | **None.** No valid number has ever been produced — see [`measurement.md`](./measurement.md) §1 |
| A/A variance floor | Not established. Blocked on B1 |
| Benchmark suite (`benchmarks/definitions/`) | Does not exist. The `bench-aa` CI job is consequently a no-op, held open by a strict `xfail` |
| Phase 0 decisions | **Ratified.** Twelve forks plus the workflow DAG — [`decisions/`](./decisions/README.md) |
| Documentation | Tier 1 and Tier 2 landed |
| Predecessor (`src/sagiha/`) | 12,949 LOC. Reference material, being retired. Not a foundation |

## What CI currently proves

| Gate | State |
| :--- | :--- |
| `ruff`, `pyright` strict, `import-linter` (5 contracts) | Green |
| Docs word budget, relative links | Green |
| Path-constant drift | Green — 1 strict `xfail` holding the missing benchmark suite visible |
| `tcb-check` | Green, **and keyed to `src/sagiha/` paths.** It goes vacuous at the `src/aether/` migration unless moved in the same change |
| `bench-aa` | **No-op.** Guarded on a suite that does not exist |

## Rules this file is held to

- No claim here is unsupported by a line-level code read.
- A gate that cannot fail is not counted as a gate.
- "Not implemented" is a legitimate and expected entry. A plausible-sounding estimate is not.
