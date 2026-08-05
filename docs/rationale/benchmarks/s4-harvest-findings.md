---
status: rationale
updated: 2026-07-31
retrieval: excluded
---
> [!NOTE]
> **LLM / AI AGENT NOTICE**: This file is a historical rationale, research reference, or benchmark log (`retrieval: excluded`). It is excluded from active search indexing and context retrieval. Do not cite this file as normative status or active code contracts.

# v2-S4 — Harvest & Measurement Findings (honest negative)

**Date:** 2026-07-31 · **Repo:** SAGIHA @ `refactor_aether_v2` · **Instrument:** `sagiha harvest --validate`

This records what happened when the E0 harvester was pointed at this repository's own history to
build the pinned `benchmarks/definitions/s0-core.json` suite the v2-S4 exit gate requires. The
short version: **three instrument defects were found and fixed, and the repaired instrument then
reported that this repo cannot supply the suite.** Both halves are deliverables.

---

## 1. Three defects found while trying to harvest

Each one made the harvester certify tasks whose "failing test" failed for a reason unrelated to
the task. All three are the H-series pattern — an instrument reporting a number that is not
about what it claims to measure — and none were caught by the existing tests, because no test
had ever run the validator against a real repository.

### D1 — `failing_test_cmd` contained files pytest cannot collect

The test-file predicate was `"test" in path.lower() or path.startswith("tests/")`, which swept
in every fixture and data file under `tests/`. Harvested commands looked like:

```
pytest tests/fixtures/replay_smoke/cassette.json tests/fixtures/replay_smoke/workspace/.gitkeep …
```

`pytest <a JSON file>` exits non-zero on a *collection error*. Stage 1 of validation read that
as "the failure reproduced", and no source fix could ever make it pass. Every task harvested
from a commit that touched test fixtures was silently unusable.

**Fix:** `is_test_file` now applies pytest's own collection rule (`test_*.py` / `*_test.py`).
Candidate count moved 27 → 23, and every remaining command is a real pytest invocation.

### D2 — "could not run the test" was scored as "the test failed"

The scratch worktree is created by `allocate`, but `materialize` — the step that symlinks the
`.venv` in — was never called. A bare `pytest` therefore exited **127** (command not found), and
the validator counted 127 as a reproduced failure. Switching the default to `python -m pytest`
moved the failure but did not fix it: `python` resolves to the *system* interpreter, which has
no pytest, so the command exited **1** with `No module named pytest` — now indistinguishable
from a failing test by exit code alone.

**Fix:** three parts. `validate_task` calls `materialize`; `_INFRASTRUCTURE_EXIT_CODES`
(126/127, pytest's 4/5) and `_INFRASTRUCTURE_STDERR_MARKERS` (`No module named pytest`,
`command not found`) reject the task loudly as `test_command_not_runnable` instead of scoring
it; and `default_test_command` resolves a concrete interpreter (`<repo>/.venv/bin/python`).

### D3 — worktree isolation was defeated by the editable install *(most serious)*

The venv materialized into a worktree carries an **editable** install of this package, whose
`.pth` file points at the main checkout's `src/`. Verified directly inside a worktree pinned at
an old commit:

```
$ .venv/bin/python -c "import sagiha, os; print(os.path.dirname(sagiha.__file__))"
/home/rock_dev/Code/Harness/src/sagiha          # the live working tree, not the worktree

$ PYTHONPATH=src .venv/bin/python -c "…"
/…/scratchpad/p4/src/sagiha                     # the worktree's own source
```

So every worktree-isolated run imported whatever was in the developer's working tree at that
moment. The blast radius is wider than the harvester:

| Consumer | What it silently measured instead |
| :--- | :--- |
| `Harvester.validate_task` | current `src/`, not the task's `base_commit` |
| `BenchmarkRunner` (both arms) | current `src/`, not the task baseline |
| **`BestOfNSearch` candidates** | one shared source tree — each candidate edits its own worktree, but every candidate's tests import the same live `src/`, so **candidate diffs are invisible to the gates scoring them** |

That last row is the one that matters for this sprint: a BoN-vs-single-shot comparison run
against a self-hosted task suite would have produced a number with no relationship to the
candidates being compared.

**Fix:** `default_test_command` emits `env PYTHONPATH=src <interpreter> -m pytest`. It is
embedded in the recorded `failing_test_cmd`, so a task carries its own isolation rather than
depending on every future runner remembering to add it.

---

## 2. What the repaired instrument reports

```
$ uv run sagiha harvest --repo . --validate --min-tasks 30 --k-determinism 1
Harvested 23 candidate tasks
Validating 23 candidate tasks (k=1)...
Validated 0/23 tasks (need >= 30)
```

Rejection breakdown: `fix_did_not_resolve` ×15, `failure_did_not_reproduce` ×5,
`source_checkout_failed` ×3. Spot-checked by hand against a manually constructed worktree; the
rejections are genuine, not a fourth instrument defect.

**Interpretation.** Commit-replay harvesting assumes a history of small, self-contained fix
commits: one bug, one test, one source change. This repository's history is **sprint-sized
commits** (`feat: V2-S3 done`, `feat: V2-S1 and V2-S2 done`) touching dozens of co-evolving
modules. Checking out the fix commit's test files onto the parent yields tests that import
symbols which do not exist at the parent yet, producing collection errors rather than the clean
single failure the protocol requires. This is a property of the corpus, not a bug in the gate —
the gate is doing exactly its job by refusing them.

---

## 3. Consequence for the v2-S4 exit gate

The gate has two halves. They are now in different states, and it is worth being precise about
which is which:

| Half | State |
| :--- | :--- |
| **Instrument** — honest statistics, validation gate, `bench --compare` wiring, cost-per-resolved-task, `diversity_ratio`, machine-checked verdict | **Done.** Every mechanism the claim needs exists and is tested. |
| **Empirical claim** — "BoN beats single-shot by X ± σ over a floor of Y" | **Not made.** It requires ≥30 validated tasks, and this repo yields 0. |

**The claim is not made, and no number is published in its place.** Per the standing rule that
honest negatives are deliverables, this document *is* the deliverable for the empirical half.

Unblocking it needs a task corpus, not more code. In rough order of cost:

1. **Point the harvester at an external repository** with small fix-commits (the harvester takes
   `--repo`; nothing is SAGIHA-specific). Cheapest path to a real suite.
2. **Hand-author a synthetic suite** of ≥30 seeded single-bug tasks. Fully controlled, but the
   tasks are then only as representative as their author.
3. **Wait for this repo's own history** to accumulate small fix commits under a
   one-fix-per-commit discipline. Free, slow, and only works going forward.

Whichever is chosen, the `bench-aa` CI job stays a documented no-op until
`benchmarks/definitions/s0-core.json` exists — the guard is honest and should not be removed to
make the job look green.

---

## 4. Reproducing

```bash
uv run sagiha harvest --repo . --validate --min-tasks 30 --k-determinism 1 \
    --output /tmp/s0-core.json

# Once a suite exists, the comparison the gate asks for:
uv run sagiha bench --suite benchmarks/definitions/s0-core.json --runs 3 --aa \
    --compare single_shot,bon --output docs/rationale/benchmarks/s4_bon_delta.md
```

`--compare` refuses to run without `--aa` or `--noise-floor`: a delta with no floor to beat
reports `beats_noise_floor=None`, and publishing that as a result is the defect this sprint
removed.

---

## 5. Closeout (2026-07-31)

`SearchConfig.enabled` defaults to `false`; prune/repair knobs are split (`prune` default
false, `escalate_after_failures=3`). `s4_bon_delta.md` is intentionally unpublished. Live
`--compare` remains the highest-risk untested path until a suite exists (pre-S6).
