---
status: rationale
retrieval: excluded
---
> [!NOTE]
> **LLM / AI AGENT NOTICE**: This file is a historical rationale, research reference, or benchmark log (`retrieval: excluded`). It is excluded from active search indexing and context retrieval. Do not cite this file as normative status or active code contracts.

# 📊 SAGIHA Pre-Honesty Baseline Benchmark Report (v2-S1) — RC-7

**Date reconstructed:** 2026-07-31 (retroactive — see method note below)
**Sprint:** `v2-S1` (Instrument Honesty), state **before** PR-1a
**Source commit:** `113561f` (`feat: Sprint 3`), the last commit before
`16b48bc fix/core(v2): PR-1a - real coding gates (H1)`

## Method note (why this is reconstructed, not re-run)

RC-7 (`docs/implementation/development_plan_v2.md`) asks for the *before* honesty report that PR-1.5
should have committed alongside the *after* one — only the after report
([`s1_honest_baseline.md`](./s1_honest_baseline.md)) exists. Re-running `sagiha bench --aa` against
the historical commit was considered and rejected: that would require checking out
`GateEvaluator.evaluate()` in its fabricating form and executing it against live tasks, producing a
"result" that is trivially 100% by construction rather than a measurement of anything — running it
would not make the number more honest, it would just cost compute to re-derive an outcome already
provable by reading the code. This report reconstructs the *reason* the drop in
`s1_honest_baseline.md` is correct, verified against the historical source at the file:line level,
per this repository's own audit-methodology convention (every claim about behavior carries a
file:line anchor, not a copied claim).

## Verbatim state at `113561f:src/sagiha/outer_loop/evaluator/gate_evaluator.py`

```python
    async def evaluate(self, task: TaskSpec, ctx: RunContext) -> GateReport:
        ...
        # Coding profile: set all gates explicitly (D20).
        return GateReport(
            criteria=tuple(criteria),
            no_new_suppressions=True,
            tests_unmodified=True,
            coverage_not_decreased=True,
            diff_within_bounds=True,
        )
```

Every one of the four coding-profile gates is an unconditional Python literal `True` — not derived
from any `git diff`, not conditioned on `RunContext.base_commit` (which did not yet exist as a
field), independent of what the run actually did to the repository.

## What that means for a benchmark number

Under this evaluator, `GateReport.admitted` reduces to `acceptance_met` alone: whatever the task's
own `AcceptanceCriterion` checks report, ANDed with four constants that are always `True`. A
benchmark run's "pass rate" at this commit therefore measures **only whether the model's final
shell command exited zero** — it is blind to whether the model edited `tests/`, edited unbounded
amounts of code, or introduced suppressions. A model that deleted the failing test and printed
"done" would score `admitted=True` under this evaluator, identically to a model that fixed the bug.

**This is why no fabricated pass-rate number is recorded here.** Inventing one (e.g. "84% resolved
pre-honesty") would itself be exactly the H1-class dishonesty this sprint exists to remove — a
number that looks like a measurement but is not gated on anything the harness can defend. The
correct, honest content of a "before" report at this commit is the fact established above: **every
coding-relevant admission the harness has ever reported before `16b48bc` is unconditionally true
regardless of code quality**, which is precisely why `s1_honest_baseline.md`'s drop to **0.0%** on
the same suite is the fix working, not a regression.

## Cross-reference

See [`s1_honest_baseline.md`](./s1_honest_baseline.md) for the *after* report and
[`docs/STATUS.md`](../../STATUS.md) H1 for the finding this closes.
