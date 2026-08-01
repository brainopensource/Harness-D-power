---
status: rationale
retrieval: excluded
updated: 2026-08-01
---
# V2-S4 Honest Closeout — Deep Review

> [!IMPORTANT]
> **Verdict: The plan is 85% correct.** The overall direction — honest-negative empirical half, `search.enabled=false`, split prune vs repair, corpus-free test/CI gaps — is sound and well-aligned with every doc. But there are **5 real issues** that will bite you during execution or leave debt for S5 if not fixed now.

---

## ✅ What's Correct and Well-Aligned

| Todo Item | Alignment | Notes |
|:---|:---|:---|
| `default-off` — flip `SearchConfig.enabled` to `False` | ✅ Perfect | Matches honest-negative clause in [sprint_v2_s4_options.md](../../implementation/sprint_v2_s4_options.md#L153), [STATUS.md](../../STATUS.md#L168), and [s4-harvest-findings.md](../benchmarks/s4-harvest-findings.md#L120). Currently `True` at [config.py:310](../../../src/sagiha/domain/config.py#L310) |
| `split-knobs` — prune vs repair semantics | ✅ Correct diagnosis | Defect #5 from [sprint_v2_s4_fixes.md](sprint_v2_s4_fixes.md#L25). Current while-loop at [best_of_n.py:121-132](../../../src/sagiha/adapters/search/best_of_n.py#L121-L132) confirms `not self._config.prune_on_first_gate_fail` makes `max_repair_rounds=2` dead code |
| `exporter-tests` | ✅ Valid gap | [eligibility.py](../../../src/sagiha/outer_loop/export/eligibility.py) exists with 4-criteria `assess()` but grep confirms zero tests cover it |
| `ci-install` | ✅ Real issue | [ci.yml](../../../.github/workflows/ci.yml) does `uv pip install --system` then `uv run` — mixed install paths |
| `status-close` | ✅ Correct | STATUS must be updated day-of-close per standing rule |
| Keeping `bench-aa` guard | ✅ Correct | Guard is honest; `s0-core.json` doesn't exist |
| Not fabricating `noise-floor.md` numbers | ✅ Correct | Matches honest-negative doctrine |
| Leaving `noise-floor.md` as template | ✅ Correct | Template exists at [noise-floor.md](../benchmarks/noise-floor.md) |

---

## 🔴 Issues That Must Be Fixed Before Execution

### Issue 1: `prune_on_first_gate_fail` Default Flip Creates a Config Validator Contradiction

**Severity: HIGH — will break the judge-separation validator on default config**

Your plan says flip `prune_on_first_gate_fail` default to `False`. That's correct for repair semantics. **But** look at what happens:

- [config.py:310](../../../src/sagiha/domain/config.py#L310): `SearchConfig.enabled` is currently `True`
- [config.py:493-507](../../../src/sagiha/domain/config.py#L493-L507): `validate_security_invariants` enforces judge ≠ execution **only when `search.enabled=True`**

When you flip `enabled` to `False`, the judge-separation validator stops firing. That's fine — search is off, no judge needed. **But the default tier config still has `frontier` (claude-3-5-sonnet) as judge and `workhorse` (claude-3-5-haiku) as execution** — these are different, so no issue today.

The **real problem** is: if someone sets `enabled=true` with default `prune_on_first_gate_fail=False`, repair is now ON, but the escalation ladder at [best_of_n.py:42-56](../../../src/sagiha/adapters/search/best_of_n.py#L42-L56) still caps repair at 1 round because `escalate_after_failures=2` and `failures=round_+1=2` triggers escalation immediately after the first repair round. Your plan says raise `escalate_after_failures` to 3 — **you must do this in the same PR as the prune default flip**, or you ship a config where `prune=False` + `max_repair_rounds=2` still only runs 1 repair round. That's defect #6 from [sprint_v2_s4_fixes.md](sprint_v2_s4_fixes.md#L28) surviving the fix.

> **Fix:** Bundle `escalate_after_failures` default `2 → 3` into `split-knobs` task. Your plan mentions it in the prose but it's not in the todo item. Make it explicit.

---

### Issue 2: The `batch_cost` Todo Misunderstands What Needs Testing

**Severity: MEDIUM — correct intent, wrong scope**

Your plan says "Direct unit test: N candidates with costs → sum all, not winner." That's correct — [batch_cost](../../../src/sagiha/adapters/search/best_of_n.py#L155-L175) sums all candidates.

**But** the deeper issue is that `batch_cost` is a **concrete-class-only method** (not on the `CandidateSearch` protocol). The `BenchmarkRunner` and `BenchmarkReporter` must call it through the concrete `BestOfNSearch` type, not through the port. Your test should verify:

1. `batch_cost` sums ALL N candidates (not just winner) ✅ in your plan
2. `batch_cost` handles candidates cancelled by `cancel_on_clean_admit` (they have outcomes in `_outcomes` because `_run_and_release_one` stores them before the cancel scope fires at [best_of_n.py:235](../../../src/sagiha/adapters/search/best_of_n.py#L235))
3. Candidates where `cost is None` are excluded (line [165](../../../src/sagiha/adapters/search/best_of_n.py#L165)) — test this edge

> **Fix:** Expand the `batch-cost-parallel` task description to cover case 2 and 3.

---

### Issue 3: The Parallel Worktree Leak Test Is Missing `FakeWorktreeManager`

**Severity: MEDIUM — test infrastructure doesn't exist yet**

Your plan says "extend `FakeWorktreeManager`" for the parallel release accounting test. But grep confirms **`FakeWorktreeManager` does not exist in `tests/`**. The [test_best_of_n.py](../../../tests/unit/test_best_of_n.py) file at line 234 uses a `FakeWorktreeManager` that's defined locally in that test file — check whether it tracks allocate/release pairs.

Looking at the existing test at [line 234](../../../tests/unit/test_best_of_n.py#L234), `FakeWorktreeManager` already exists as a test helper within the test module. You need to verify it has `allocate` and `release` tracking to assert every allocate has a matching release. If it doesn't track that yet, you need to add it.

> **Fix:** Verify the existing `FakeWorktreeManager` in the test file and extend it with allocate/release accounting if needed. The plan implies it exists project-wide; it's local to the test file.

---

### Issue 4: CI Install Fix Is Under-Specified and Risky

**Severity: MEDIUM — could break CI if done wrong**

Your plan says: "after system install use bare `python` / `sagiha` / `pytest` consistently." But look at [ci.yml](../../../.github/workflows/ci.yml):

- **quality-gates** (line 38): `uv pip install --system -e ".[dev]"` then `uv run python scripts/gen_event_catalog.py --check`
- **conformance** (line 79): same pattern
- **tests** (line 94): same pattern
- **bench-aa** (line 109): same pattern, then `uv run sagiha bench`
- **replay** (line 139): same pattern, then `uv run sagiha replay`

The issue: `uv pip install --system` puts packages in the system Python. Then `uv run` creates a **new virtual environment** and may not see the system-installed packages. Either:
- Use `uv pip install --system` + bare `python`/`pytest`/`sagiha` everywhere, OR
- Use `uv run` everywhere (which manages its own venv)

**But** your plan says "keep bench-aa guard" — that's fine. The risk is that switching from `uv run sagiha` to bare `sagiha` in bench-aa means the `sagiha` CLI must be on `PATH` via the system install. Since `pip install -e ".[dev]"` installs the `sagiha` entry point, bare `sagiha` should work after system install. But **test this in a clean container first**.

> **Fix:** Decide which pattern and be explicit: either `uv pip install --system` + bare commands, or `uv sync` + `uv run`. Don't mix. Document the decision in the PR.

---

### Issue 5: Example TOML Profiles Say `enabled = true` — Must Change to `false`

**Severity: LOW but will confuse users**

Both [sagiha.cpu.example.toml:27](../../../sagiha.cpu.example.toml#L27) and [sagiha.gpu.example.toml:25](../../../sagiha.gpu.example.toml#L25) currently say `enabled = true`. Your plan correctly says to sync these, but you should also update the **comments** in these files to explain that search is off by default because the empirical exit gate was not met.

> **Fix:** Add a one-line comment in each TOML: `# Off by default: empirical exit gate not met (s4-harvest-findings.md). Set true once a task corpus exists.`

---

## 🟡 Warnings — Not Blocking but Worth Knowing

### Warning 1: `s4-harvest-findings.md` Needs a Closing Section

Your plan mentions "Add a short closing section to s4-harvest-findings.md stating the default flip." The file currently ends at [line 152](../benchmarks/s4-harvest-findings.md#L152) with reproduction instructions. A §5 "Closeout" section recording the default flip, the `prune`/`repair` split, and the fact that `s4_bon_delta.md` is intentionally unpublished is appropriate. **Don't over-write it — 5 lines max.**

### Warning 2: STATUS Block 3 Wording Needs Care

The current STATUS at [line 97](../../STATUS.md#L97) says search.enabled "remains an untested default." After your closeout it becomes `search.enabled=False`. The STATUS update should say:

> Block 3 — Best-of-N search | **Mechanism complete; shipped off by default** (`search.enabled=false`). Never measured against a real suite — 0/23 tasks validate (findings). Protocol and adapter retained; default flip and suite are explicit pre-S6 hard dependencies for ablation gates.

### Warning 3: The `development_plan_v2.md` Checkboxes

The plan at [development_plan_v2.md](../../implementation/development_plan_v2.md) has all S4 epics as `- [ ]`. Your closeout should mark S4.0–S4.4 mechanism as done with a note that the empirical gate is deferred. Don't touch S4 verification checkboxes — they're honestly not met.

### Warning 4: Test Count Monotonicity

Current baseline: **266 tests** per [STATUS.md:119](../../STATUS.md#L119). Your closeout adds exporter tests + batch_cost test + parallel leak test + repair/prune split tests. New count should be **≥ 270**. State the expected floor in the PR.

### Warning 5: The `--compare` Path Is Documented but Untested

Your plan correctly identifies this: "`--compare` never run live — document in STATUS/findings as highest-risk untested path." This is the right call for S4 closeout. **But for S5 readiness**: `--compare` depends on having a real suite. Until S6's ablation gates need it, this is acceptable debt. Document it explicitly as a pre-S6 dependency.

---

## 📋 Corrected Todo Ordering

Based on the dependency analysis, the correct execution order is:

```
1. split-knobs          ← DO FIRST (code change, most complex)
   - prune_on_first_gate_fail default True → False
   - escalate_after_failures default 2 → 3     ← MUST be in same PR
   - Repair loop refactor in best_of_n.py
   - Replace test_prune_on_first_gate_fail_default_disables_repair

2. default-off          ← After split-knobs (config change)
   - SearchConfig.enabled True → False
   - Sync .example.toml files with enabled=false + comment
   - Closing section in s4-harvest-findings.md

3. exporter-tests       ← Independent, can parallel with 4
   - test_export_eligibility.py
   - SFT/DPO shape tests

4. batch-cost-parallel  ← Independent, can parallel with 3
   - batch_cost unit test (sum all, not winner; None-cost edge; cancelled candidate)
   - Parallel launch worktree leak test (extend FakeWorktreeManager)

5. ci-install           ← Independent
   - Pick one pattern: system-install+bare OR uv-run
   - Apply consistently across all jobs

6. status-close         ← LAST (depends on all above)
   - STATUS.md: mark v2-S4 closed, honest-negative
   - development_plan_v2.md: S4 notes
   - Verify test count ≥ 270
   - All seven signals green
```

---

## 🔑 Summary: What to Fix in the Todo Before Starting

| # | What | Why |
|:--|:-----|:----|
| 1 | Add `escalate_after_failures 2→3` explicitly to `split-knobs` | Without it, repair is still capped at 1 round even with `prune=False` |
| 2 | Expand `batch-cost-parallel` scope | Missing cancelled-candidate and None-cost edge cases |
| 3 | Clarify `FakeWorktreeManager` is test-local, not project-wide | Avoids confusion during implementation |
| 4 | Make CI install pattern decision explicit | "Use bare commands" or "use uv run" — don't say "consistent" without deciding which |
| 5 | Add comment to TOML files explaining why `enabled=false` | Prevents next user from re-enabling without understanding the context |

Everything else in the plan is correct. The honest-negative framing is exactly right, the scope fence is appropriate, and the deferred items (suite, noise-floor, bench-aa unconditional) are properly placed as pre-S6 dependencies. Execute in the order above and S5 starts clean.
