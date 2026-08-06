---
status: normative
updated: 2026-08-06
---

# STATUS

**Nothing is implemented.** `src/aether/` is empty.

That is the correct content for this file today, and it stays until a line-level code read
supports something else.

| Area | State |
| :--- | :--- |
| `src/aether/` | Empty. No ports, no domain, no kernel |
| Benchmark results | **None.** No valid number has ever been produced — see [`measurement.md`](./measurement.md) §1 |
| A/A variance floor | Not established. Blocked on B1, B2b and **B4** |
| Benchmark suite (`benchmarks/definitions/`) | Does not exist, and is **git-untracked**. The `bench-aa` CI job is consequently a no-op, held open by a strict `xfail` |
| Phase 0 decisions | **Ratified and locked.** Twelve forks, the workflow DAG, and four ADRs added by the lock audit — [`decisions/`](./decisions/README.md) |
| Documentation | **Phase 0 locked** (2026-08-06). D1–D21 reconciled; 17 ADRs; both docs gates green and covered by a negative test |
| Predecessor (`src/sagiha/`) | 12,949 LOC. Reference material, being retired. Not a foundation |

## What CI currently proves

| Gate | State |
| :--- | :--- |
| `ruff`, `pyright` strict, `import-linter` (5 contracts) | Green — **and keyed to `sagiha`.** `root_package = sagiha`; see the `tcb-check` row |
| Docs word budget (`--max 15000`) | **Green.** 7,259 normative words across 6 files, 7,741 under the ceiling |
| Relative links | **Green.** 201 files, zero dead links |
| Docs gates can fail | **Green** — `tests/unit/test_docs_gates.py`, 10 cases. Both gates were reported green here while red until 2026-08-06 |
| Path-constant drift | Green — 1 strict `xfail` holding the missing benchmark suite visible |
| `tcb-check` | Green, **and keyed to `src/sagiha/` paths.** It goes vacuous at the `src/aether/` migration unless moved in the same change — owner: [`TASK-000`](./agile/backlog.md), M0 Exit Gate 0 |
| `bench-aa` | **No-op.** Guarded on a suite that does not exist |

## What was wrong with this file until 2026-08-06

Recorded rather than quietly corrected, because the failure is the interesting part.

This file reported **"Docs word budget, relative links — Green"** as a single row. Both were
red. `check_links.py` was returning **7 dead links** — every core document pointed at
`docs/00/`, a directory that does not exist — and `docs_budget.py` was failing on **5 files
with no `status:` frontmatter**.

Neither was subtle, and neither had been run. A file whose first rule is *"no claim here is
unsupported by a line-level code read"* carried two claims unsupported by running a script.

Worth keeping: **the gates were correct and the report was wrong.** The mechanism worked; what
was missing was anything forcing the report to be derived from it. That gap is now closed by
`tests/unit/test_docs_gates.py`, which plants a dead link and an untagged file and asserts each
gate returns non-zero — and which, on its first run, found that the link checker's *failure
path* crashed on a `--docs-root` outside the repo. The error branch had never executed.

## Rules this file is held to

- No claim here is unsupported by a line-level code read **or by running the gate and pasting
  what it said**.
- A gate that cannot fail is not counted as a gate.
- "Not implemented" is a legitimate and expected entry. A plausible-sounding estimate is not.
- A gate reported green here names the command that produced the green.
