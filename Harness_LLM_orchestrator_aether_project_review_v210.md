---
status: rationale
updated: 2026-08-01
retrieval: excluded
---

# SAGIHA v2.1.0 — Post-Remediation Audit & Forward Architecture Plan

| Field | Value |
| :--- | :--- |
| **Document ID** | `Harness_LLM_orchestrator_aether_project_review_v210` |
| **Date** | 2026-08-01 |
| **Branch / HEAD** | `refactor_aether_V210` @ `0b7804b` (+ staged W9 work) |
| **Predecessors** | `Harness_LLM_orchestrator_project_review.md` (audit V3) · `sprints_0_to_6_fix_plan.md` (W0–W9) · `concept_review.md` (v3 concepts) |
| **Scope** | (a) verify the W0–W8 remediation, (b) find what is still open, (c) **refine v2-S7 and design v2-S8+** |
| **Weighting** | Deliberately future-heavy. §1–§3 are the verified present; **§4–§8 are the plan** |
| **Method** | Every present-state claim comes from a command run against this tree today. No code or docs were changed producing this report |

---

# §1 — Executive Summary

## 1.1 The remediation worked

W0–W8 closed **every Critical and Major defect** in audit V3 that was closable without network
access or a human TCB commit. I re-verified the two that mattered most, empirically rather than by
reading the diff:

- **C-1 is genuinely dead.** `search("Fix the bug in greet() so it returns a name")` now returns
  hits where it silently returned `[]` before. `'!!!'` and `''` return `[]` **without touching the
  database** — a true empty, honestly produced. Non-cold-DB `OperationalError` now propagates.
- **M-5 works and is measurable.** Against the real `src/sagiha` tree (642 chunks), searching a
  bare path fragment (`pkg/util.py`) and a dotted symbol (`pkg.util.greet`) both retrieve the
  chunk. The envelope is doing the job it was specified to do.
- **Retrieval quality is better than the plan's own risk register feared.** The `_fts_query`
  OR-join was flagged as a precision risk; BM25 ranking absorbs it.
  `'compactor exchange token budget'` ranks `agency/context/compactor.py` in the top 3.

The engineering quality of the remediation is high, and in three places it is higher than the
plan asked for. `L-10` correctly *refused* a plan step after finding its premise wrong
(`find_symbols` uses `LIKE`, not `MATCH`, so routing it through `_fts_query` would have introduced
a defect). `L-12` found that two "deleted" link targets had merely moved and repointed instead of
deleting. `L-21` refused to author a TCB file and wrote the proposal instead. **An implementer that
declines a written instruction because verification contradicted it is the behaviour this
project's whole doctrine exists to produce.**

## 1.2 But the tree is red right now, and it regressed *after* W8

`scripts/verify.sh` — the instrument W5 built precisely so nobody would report gate state from
memory — **exits 1 on this tree today**:

| Signal | W8 (`3c576e8`) | **Now** | Cause |
| :--- | :--- | :--- | :--- |
| pytest | 358 passed | **356 passed, 2 failed** | staged `e0/repo_cache.py` |
| ruff | 0 | **344 errors** | 343 from `.sagiha/repo-cache/`, 1 from staged code |
| format | 0 | **37 files** | `scripts/import_swebench_lite.py` landed unformatted in `0b7804b` |
| pyright · imports · budget · links · catalog | green | **green** | — |

None of this is in the W0–W8 work. All of it arrived with the W9 benchmark effort — commit
`0b7804b` plus the staged working tree. **The status summary reporting "Gates now: pytest 358 ·
ruff 0 · format 0" is describing `3c576e8`, not `HEAD`.** That is the C-2 defect recurring one
layer up: a green number, true when measured, restated after the tree moved. The fix is not more
discipline; it is `scripts/verify.sh` before every commit, which is what D14 already requires.

## 1.3 The three things that most shape what comes next

1. **`Orchestrator` has zero implementations, and it is the Conductor's entire downward surface.**
   `agi_evolution_path.md §2.1` states the Conductor's whole contract with the engine is
   `Orchestrator.execute(TaskSpec, RunContext) -> AsyncIterator[Event]`. Nothing in `src/`
   imports `ports/orchestrator.py` — not `composition.py`, not `cli.py`. C0 is blocked on a
   prerequisite no sprint has scheduled. **This is the highest-leverage missing piece in the
   roadmap** (§4.4, §5.2).
2. **v2-S7 as written bundles three unrelated capabilities behind one exit gate**, and one of
   them (Story-DAG) is gated on an ablation that cannot be run until W9 completes. As specified,
   S7 either ships partially-gated or blocks on empirics it does not need. It should be split
   into four independently-gated sprints (§4.2).
3. **The measurement track is now the critical path for everything empirical.** W9 is ~70% done
   and its remaining work is a real capability addition to `e0/`, not a remediation fix. Until it
   lands, S7.1's ablation gate, every default flip, and Conductor C0's cost-ledger gate are all
   unmeasurable (§5.1).

## 1.4 Verdict

| Question | Answer |
| :--- | :--- |
| Did W0–W8 close the audit? | **Yes** — every Critical and Major defect except M-2 (needs a human TCB commit) |
| Is the tree tag-ready today? | **No** — three gates red from in-flight W9 work; ~1 hour to green |
| Was P0 genuinely achieved? | **Yes, at `0389f89`** — and `verify-W5-p0-complete.txt` records it honestly |
| Should v2-S7 start as written? | **No** — split it first (§4.2) |
| Is anything overengineered? | **Yes** — 4 zero-rent ports, 868 MB of untracked vendored trees inside `src/` (§6) |

---

# §2 — Verification of the W0–W8 Remediation

Spot-checked against code, not against the plan's own checkboxes.

| Defect | Claimed | Verified | Notes |
| :--- | :--- | :--- | :--- |
| **C-1** FTS5 silent empty | W1 | ✅ **Confirmed empirically** | Goal-shaped queries return hits; punctuation-only returns `[]` with no SQL; non-cold errors raise |
| **C-3** no conformance edge | W2 | ⚠️ **Partial** — see **N-M1** | Mechanism is excellent (static + runtime + meta-guard) but covers **7 of 17 ports** |
| **C-R1** `Indexer.neighbors` | W2 | ✅ Confirmed | Port is 3 methods; `neighbors` deleted; ADR-0026 records the port-rent reasoning |
| **m-4** `_db_path` leak | W2 | ✅ Confirmed | `replace_file_chunks` / `clear_path` are public; no `sqlite3.connect(_db_path)` in `service.py` |
| **m-14 / ruff / format** | W3 | ✅ Confirmed at W8, ❌ **regressed since** | See **N-C1**, **N-C3** |
| **C-2b** docs budget | W4 | ✅ Confirmed | 14,899 / 15,000 — but only a **101-word margin** (L-16). See **N-m3** |
| **C-3d** 106 dead links | W4 | ✅ Confirmed | 0 dead links across 122 files |
| **m-12** untagged docs | W4 | ✅ Confirmed | `docs_budget.py` now fails closed on untagged files |
| **C-2** STATUS honesty | W5 | ✅ Confirmed mechanism | `verify.sh` exists and is authoritative; **the discipline lapsed at W9** (N-C3) |
| **M-6 / M-7** plan drift | W5 | ✅ Confirmed | "17 ports (ADR-0019 restated + ADR-0024)"; 15 epics ticked with L-14 explaining the 3 left unticked — correctly |
| **m-8 / m-9** doc amendments | W5 | ✅ Confirmed | S5 credential wording now states exactly what exists |
| **m-3 / M-3** shared vocabulary | W6 | ✅ Confirmed | `walk.py` is the single definition; `module_name` is full-dotted in both indexer and graph |
| **M-4** dead knob | W6 | ✅ Confirmed | Field gone; `MAX_CHUNK_TOKENS` is one constant; ADR-0027 records it |
| **M-5** chunk envelope | W6 | ✅ **Confirmed empirically** | `Chunk.body` preserves the raw span; path and symbol both retrievable |
| **M-8** lying stub | W7 | ✅ Confirmed | `sequential.py` deleted; the 4 tests that asserted its fabrications deleted with it (L-19 — correctly reasoned) |
| **m-1/m-2/m-5/m-7** | W7 | ✅ Confirmed | init graph wiring, discovery naming, orphan prune, export schema warning |
| **M-2** Podman CI | W8 | ⚠️ **OPEN** | 8.2–8.4 landed; 8.1 correctly refused as TCB (L-21). **Still open** |
| **M-1** benchmark suite | W9 | ◐ **~70%** | Suite committed and pinned; runner support in flight; **no floor, no ablations** |

**Deviation-log quality.** §5 of the fix plan holds 21 entries, several of which *correct the
audit that commissioned them* (L-1 withdrew m-13; L-10 refused a step on verified grounds; L-14
declined to tick 3 boxes). This is the artifact working as designed and is worth preserving as a
pattern for future sprints.

---

# §3 — Open Defects in the Present Code

New IDs, `V210-` prefixed, to avoid collision with audit V3.

## CRITICAL — blocks any tag or push

### N-C1 — `.sagiha/repo-cache/` is neither gitignored nor tool-excluded, and tests write into it

| | |
| :--- | :--- |
| **Evidence** | `ruff check .` → 344 errors, **343 of them under `.sagiha/repo-cache/`**. `.gitignore` names `.sagiha/trajectories.db*` specifically but not `.sagiha/` or the cache. `du -sh .sagiha/repo-cache` → 3.5 MB and growing per benchmark run |
| **Worse** | The cache contains directories named `__tmp__pytest-of-rock_dev__pytest-151__test_benchmark_runner_single_t0`. `repo_cache.DEFAULT_CACHE_DIR` is `Path(".sagiha") / "repo-cache"` — **relative to CWD**, so unit tests running with a `tmp_path` workspace root mangle that tmp path into a cache key and write it into the developer's real working tree |
| **Why critical** | Three separate harms: the CI lint gate goes red on vendored upstream source; an unignored 3.5 MB+ directory is one `git add -A` from being committed; and a test suite that writes outside its `tmp_path` is not hermetic |
| **Fix** | (1) `.gitignore`: add `.sagiha/` wholesale, or at minimum `.sagiha/repo-cache/`. (2) `pyproject.toml` `[tool.ruff] extend-exclude`: add `.sagiha`. (3) Make `cache_dir` a required constructor argument on the resolve path, or derive it from the workspace root, so a test with `tmp_path` caches inside `tmp_path`. (4) Delete the leaked `__tmp__pytest-*` directories |

### N-C2 — Staged `e0/repo_cache.py` breaks 2 tests

| | |
| :--- | :--- |
| **Evidence** | `uv run pytest -q` → `2 failed, 356 passed`: `tests/unit/test_benchmark_runner.py::test_benchmark_runner_single_task` and `::test_benchmark_runner_suite_run`, both with `git init failed` / `git remote add failed` |
| **Cause** | `BenchmarkRunner._repo_root_for` now routes **every** task through `resolve_task_root(task.repo, …)`. For a harvested/synthetic task whose `repo` is a local tmp path, this attempts to treat that path as an upstream `owner/name` and clone it |
| **Fix** | Discriminate imported from local tasks explicitly rather than by inference. The suite already carries the signal — an imported suite has `suite_id` `s0-core-swebench-lite-30` and per-task `validation_reason: "imported from SWE-bench Lite…"`. Add an explicit `origin: Literal["harvested","imported"]` to the suite schema and branch on it; do not guess from the shape of a path string |

### N-C3 — Commit `0b7804b` landed without `verify.sh`, and the plan does not record it

| | |
| :--- | :--- |
| **Evidence** | `scripts/import_swebench_lite.py`, added in `0b7804b`, fails `ruff format --check`. The plan's §3 still shows **W9 as ☐ (not started)** and §4's W9 row is empty, while `benchmarks/definitions/s0-core.json`, the importer, and a rewritten `noise-floor.md` are all committed |
| **Why critical** | This is precisely the defect class W5 built `verify.sh` to end. The rule exists (fix-plan rule 4, D14); it was followed for nine consecutive waves and dropped on the tenth. It is also **plan/reality drift** — the M-6 defect, recurring in the remediation plan itself |
| **Fix** | Run `ruff format`; run `verify.sh`; amend §3 W9 checkboxes and §4's W9 row from real output; add an L-entry recording that W9 began before W8 closed |

> **Note on what `0b7804b` got right.** The rewritten `noise-floor.md` is the best artifact
> produced in this whole cycle. It refuses to publish the `0.0%` pass rate the attempted run
> printed, explains that it is 30 infrastructure failures rather than 30 unsolved tasks, and
> quotes it *only* so nobody re-derives it and mistakes it for a result. It also marks all 30
> tasks `validated: false` because SWE-bench's own validation "is not ours to claim." That is the
> honesty doctrine applied without being asked. **The process lapse is real; the judgement is
> excellent.**

## MAJOR

### N-M1 — Adapter conformance covers 7 of 17 ports

`tests/contracts/test_adapter_conformance.py` is well built — static assignability at the call
site, runtime construction, plus a meta-test guarding the registry. But its required-pair list
names 8 pairs across **7 distinct ports**. Ten ports have no assignability assertion, and five of
those have **live adapters wired in `composition.py`**:

| Port | Live adapter | Asserted? |
| :--- | :--- | :--- |
| `ModelProvider` | `OpenAIProvider`, `CassetteProvider`, `FallbackProvider` | ❌ |
| `ToolRegistry` | `DefaultToolRegistry` | ❌ |
| `Memory` | `InMemoryMemory` (`composition.py:189`) | ❌ |
| `Evaluator` | `GateEvaluator` | ❌ |
| `WorktreeManager` | `GitWorktreeManager` | ❌ |

C-R1 drifted on `Indexer`; nothing structural prevents the identical drift on `ModelProvider`,
whose `PORT_VERSION` is already 2 and which has three adapters. **Fix:** extend the registry to
every port with ≥1 adapter, and make the meta-guard derive its list from `ports/` by enumeration
rather than from a hand-maintained literal — a hand-maintained list of what must be tested is the
same artifact class as a hand-maintained regression table.

### N-M2 — ADR-0023's port-rent rule has never once been executed

Four ports have **zero importers anywhere in `src/`** — not composition, not adapters, not tests:
`advisory`, `meta_improver`, `toolchain`, `orchestrator`. ADR-0023 states the rule: *zero
non-test adapters for two consecutive blocks ⇒ automatic demotion to `experimental` and deletion
review.* S5 and S6 have both closed. The rule has fired for none of them, because **nothing
executes it** — it is a policy with no mechanism, which is the C-2 pattern applied to
architecture governance.

Three of the four should be demoted or deleted. **`orchestrator` is the exception and must go the
other way — it needs an implementation, urgently** (§4.4).

### N-M3 — The E0 runner was model-blind (fix in flight, credit where due)

The staged `runner.py` diff fixes a defect audit V3 did not find: `BenchmarkRunner` constructed
`ModelConfig(mode=mode_val)` with **no tier or role binding**, so it fell back to ModelConfig's
defaults (an Anthropic tier) regardless of the endpoint actually configured. A local Ollama
endpoint was being asked for a Claude model and 404ing on every task. **A benchmark harness that
cannot be pointed at a model is not a benchmark harness**, and this sat undetected because the
suite it would have run against did not exist. Land the fix, and add a unit test that asserts
`BenchmarkRunner` propagates its `model_config` — the regression is invisible without a live
endpoint otherwise.

## MINOR

| ID | Defect | Evidence | Fix |
| :--- | :--- | :--- | :--- |
| **N-m1** | `_fts_query` has no stopword floor | `search("the")` returns 10 arbitrary chunks rather than `[]` | Require ≥1 token below a document-frequency threshold, or drop a small stopword set. Do **not** tune blind — make it a W9 ablation input |
| **N-m2** | `repo_cache.py:76` E501 (111 > 110) | `ruff check src/sagiha` | Wrap the f-string |
| **N-m3** | Docs budget margin is 101 words, not the 526 D10 bought | L-16 records this honestly | The next docs PR should ratchet toward 14,474. At 101 words, one paragraph re-reds the gate |
| **N-m4** | `reindex_root` returns 105 while `chunk_count()` reports 642 | Observed on `src/sagiha` | Return value is files-indexed; the name reads as chunks. Rename or document |
| **N-m5** | `.sagiha/repo-cache` fetches are per-task and serial | `repo_cache.ensure_repo` | Fine for 30 tasks; document the cost, and make the cache dir configurable so CI can warm it |

---

# §4 — v2-S7: Refinement Required Before It Starts

## 4.1 What the current S7 specification gets right

`development_plan_v2.md` S7 is well reasoned in three ways worth preserving verbatim:

- **`IntegrationStep` is named as load-bearing.** Most Story-DAG designs treat integration as
  plumbing; this one identifies rebase-onto-a-moving-base as the hard part and specifies
  closure-invalidation ⇒ back to the board, never a silent merge.
- **`ResolveConflictTask` goes through the inner loop**, budget-capped and hunk-confined,
  explicitly "never a gate-bypassing repair call." That closes the obvious hole before anyone
  opens it.
- **The ADR-0018 gate is stated honestly**: if planning does not beat no-planning, "the Protocol
  stays, the pipeline does not ship."

## 4.2 Problem 1 — S7 bundles three unrelated capabilities behind one exit gate

S7.1 (Story-DAG), S7.2 (MCP client) and S7.3 (streaming/steer) share no code, no dependency, and
no risk. They are bundled only because `next_gen_architecture_specs.md` grouped B5b/B5c. The
plan's **own Standing Rule 2** — *"no periphery before the gate: a sprint's exit gate is the only
thing that closes it"* — argues directly against this shape, and the same bundling is what audit
V3 flagged in the original Block 5.

The exit gate compounds it: *"ablation-positive macro layer **and** first external MCP tool **and**
interactive steering demo."* MCP and streaming would sit finished behind an ablation that cannot
run until W9 completes.

**Decision: split S7 into four independently-gated sprints.** See §5.

## 4.3 Problem 2 — S7.1's gate is unmeasurable on today's tree

S7.1 requires *"planning beats feeding the raw prompt to the inner loop, beyond the floor,
including 2-way parallel stories."* That needs: a pinned suite (✅ exists), a measured A/A floor
(❌ does not exist), a runnable E0 loop over imported tasks (◐ in flight), and a model (✅ now
available). **Three of four prerequisites live in W9.** Starting S7.1 before W9 closes guarantees
one of two bad outcomes: the mechanism ships with the empirical half deferred *again* — the S4 and
S6 pattern, now a habit — or the sprint stalls waiting on measurement it did not schedule.

## 4.4 Problem 3 — the missing `Orchestrator` adapter is nobody's sprint

This is the most consequential gap in the entire forward plan and it appears in no sprint.

- `agi_evolution_path.md §2.1`: *"The Conductor's entire downward surface is the existing
  `Orchestrator` Protocol."* Its three structural facts all rest on it.
- `next_gen_architecture_specs.md §3.2`: A2A remote peers are `Orchestrator` adapters; sub-agents
  are "the degenerate local case of the same contract."
- **The tree has zero implementations.** `RunLoop.run()` returns a `RunLoopResult`, not an
  `AsyncIterator[Event]`. `cli.py` drives `RunLoop` directly.

Consequences, all currently unscheduled:

1. **Conductor C0 cannot start.** Its exit gate ("a 3-story sequential mission survives `kill -9`
   ×3") requires dispatching stories through a port with no implementation.
2. **Sub-agents are unavailable** — and `concept_review.md §2.9` argues they are the *lossless*
   answer to context pressure where compaction is lossy.
3. **A2A stays theoretical**, correctly deferred but with no landing strip.

A `LocalOrchestrator` wrapping `RunLoop` and yielding the event stream is a small, well-understood
adapter. It is the single highest-leverage unbuilt thing in the tree.

## 4.5 Problem 4 — S7.2's MCP dependency chain has an unstated prerequisite

S7.2 says discovered MCP tools "register `trusted_output=False`, dispatch through the same choke
point, grant-gated." Correct. But `DefaultToolRegistry` currently registers tools at composition
time from a static builtin set, and the **20-tool prompt budget** (`agi_evolution_path.md §6.1`)
has no enforcement anywhere in the tree. An MCP server exposing 40 tools would silently blow the
budget that doctrine says exists for measured reasons. Add a registry-level cap that **refuses at
composition** — the same refuse-at-load pattern `domain/config.py` already uses for autonomy and
judge separation.

---

# §5 — Proposed Sprint Plan: v2-S7a … v2-S10

Split S7; add three sprints; then Conductor. Every sprint below has **one** theme and **one**
falsifiable exit gate.

## 5.1 v2-S7a — Measurement Closeout *(finish W9)* — **do this first**

**Why first:** it is the critical path for every ablation-gated sprint that follows, it is ~70%
done, and both blockers it identified are now solved or solvable.

| Epic | Contents |
| :--- | :--- |
| **S7a.0** | Fix **N-C1**, **N-C2**, **N-C3** — gitignore + ruff-exclude the cache, make the cache dir test-local, discriminate imported suites explicitly, run `verify.sh`, reconcile the plan |
| **S7a.1** | Land `e0/repo_cache.py` + runner `model_config` plumbing with unit tests (**N-M3**) |
| **S7a.2** | Add `origin: Literal["harvested","imported"]` to the suite schema; runner branches on it |
| **S7a.3** | Run the A/A noise floor: `bench --suite s0-core.json --aa --runs 2`. **Publish whatever comes out** |
| **S7a.4** | Run the three ablations — BoN vs single-shot, retrieval on/off, init on/off |
| **S7a.5** | Flip defaults **only** where a delta beats the floor; publish every negative as a negative |

**Exit gate:** `noise-floor.md` contains numbers from a real run, or a published explanation of why
it still cannot. Each ablation is a published number or an explicit not-measured. **`bench-aa`
unguarded in CI.**

**Warning to carry into this sprint:** the first honest ablation may well show retrieval-off ≥
retrieval-on. That is a *result*, not a failure — and `concept_review.md §5.1` predicts it
("does retrieval help at all in a repo with a good `AGENTS.md`?"). Budget for the outcome where
the correct action is to shelve a subsystem.

## 5.2 v2-S7b — Orchestrator Adapter & Sub-Agents *(new — unblocks the most)*

| Epic | Contents |
| :--- | :--- |
| **S7b.1** | `adapters/orchestrator/local.py::LocalOrchestrator` implementing `Orchestrator`, wrapping `RunLoop`, yielding the typed event stream and terminating in a `GateReport` |
| **S7b.2** | Add `LocalOrchestrator→Orchestrator` to the conformance registry; rewire `cli.py run` through the port so it is exercised on every run, not just by tests |
| **S7b.3** | `spawn_subagent` as the degenerate local case (`next_gen_architecture_specs.md §3.2`): a grant-subset, budget-slice `TaskSpec` dispatched through the same port, returning a summary rather than a transcript |
| **S7b.4** | Registry tool-cap refusal at composition (**§4.5**) |

**Exit gate:** `cli.py` drives the engine through `Orchestrator` only; a sub-agent task completes
under a strict grant subset and returns ≤N tokens to the parent context; **an E0 ablation shows
sub-agent delegation beats in-context search on a retrieval-heavy task class, or it ships off by
default.** (Requires S7a.)

**Why this before Story-DAG:** it is smaller, it unblocks C0, and sub-agents may make the macro
layer cheaper to build — a story dispatched to a sub-agent is most of what `CodingStep` does.

## 5.3 v2-S7c — Streaming & Interrupt-and-Steer *(was S7.3)*

Unchanged in content from the current S7.3; now independently gated. Notably **not** blocked by
S7a — its gate is mechanical (<2 s to steerable, tail-cache hit on steer), not empirical.

**Exit gate:** interrupt→steerable < 2 s; steer turn shows `cache_read_tokens ≥ prior tail`;
resumed-after-steer run replays byte-identically.

## 5.4 v2-S7d — MCP Client *(was S7.2)*

Unchanged; independently gated. Depends on S7b.4's tool cap.

**Exit gate:** external tool round-trip under grant + `<untrusted-data>` envelope; MCP output
marked tainted end-to-end; registry refuses a server that would exceed the tool cap.

## 5.5 v2-S7e — Story-DAG Macro Layer *(was S7.1)*

Unchanged in content. **Hard dependency on S7a** — its gate is an ablation.

**Exit gate:** ADR-0018 to the letter. If negative, the Protocol stays and the pipeline does not
ship, published as a number.

## 5.6 v2-S8 — Contract Surface Truth-Up *(new)*

The governance sprint that S0 was for docs, applied to code contracts.

| Epic | Contents |
| :--- | :--- |
| **S8.1** | Extend adapter conformance to **every port with ≥1 adapter** (**N-M1**); derive the required-pair list by enumerating `ports/` rather than by hand |
| **S8.2** | **Execute ADR-0023.** Demote or delete `advisory`, `meta_improver`, `toolchain` (**N-M2**). Record each in an ADR with re-promotion conditions |
| **S8.3** | Add `scripts/check_port_rent.py` to CI: a port with zero non-test importers for two consecutive sprints fails the build. *A rule with no mechanism is not a rule* |
| **S8.4** | Generate the reference docs layer from `src/` — port surface, tool schemas, config schema, CLI reference — each with `--check` in CI, following the `gen_event_catalog.py` pattern that is the one docs gate never to have gone red (`concept_review.md §2.2`) |

**Exit gate:** every port either has a conformance assertion or a deletion ADR; `check_port_rent`
green in CI; ≥3 reference docs generated and `--check`ed; normative hand-written prose back under
14,000 words as a side effect (**N-m3**).

## 5.7 v2-S9 — Observability & Cost Attribution *(new)*

The tree records trajectories but has no analysis surface; `otel.py` is still a loud stub.

| Epic | Contents |
| :--- | :--- |
| **S9.1** | OTel exporter behind `telemetry.otel_exporter` (spec'd in `next_gen_architecture_specs.md §1.3`, never built) |
| **S9.2** | **DuckDB read-only over exported trajectories** — the one `harness_research_2026_briefing.md` stack recommendation worth taking (`concept_review.md` Ch.3). Offline analysis only; never in the write path |
| **S9.3** | Per-`(role, tier, task-class)` cost attribution from the ledger H2 already produces |
| **S9.4** | Failure taxonomy report — RHI Tier B trace mining (`next_gen_architecture_specs.md §2.3`), which has been specified since v2 and never scheduled |

**Exit gate:** a single command answers "which failure class killed the most runs last week, and
what did each cost." **Tier B is the cheapest unbuilt thing in the RHI design.**

## 5.8 v2-S10 — Prompt Regression CI (RHI Tier A) *(new)*

`next_gen_architecture_specs.md §2.3` calls Tier A *"90% of self-improvement's defensive value at
CI cost."* It has never been built, because it needs a suite — which S7a delivers.

| Epic | Contents |
| :--- | :--- |
| **S10.1** | Any PR touching `src/sagiha/prompts/`, `[context]` or `[search]` config triggers the pinned suite, paired against baseline, judged against the stored floor with Holm correction. Red ⇒ merge blocked |
| **S10.2** | Exemplar mining from gate-admitted trajectories (Tier B), adopted only through S10.1's gate |
| **S10.3** | **Rename the capability in all docs from "recursive harness improvement" to "prompt regression testing"**, and delete `ports/meta_improver.py` unless S8.2 already did |

**Exit gate:** a deliberately-regressed prompt is caught by CI. **The system then has a real,
working self-improvement mechanism and a claim that exactly matches it** — versus today's claim
without mechanism.

## 5.9 Then: Conductor C0

With S7a (honest bench), S7b (`Orchestrator`), and S7c (steer) landed, C0's stated hard
dependencies are genuinely satisfied rather than nominally so. Carry one amendment from
`concept_review.md §2.6`: introduce `(mission_id, story_id, run_id)` identifiers and a **budget
tree** now, while only one task ever runs. Both are free today and touch every event, every
trajectory row, and every index if retrofitted later.

## 5.10 Sequencing

```
S7a Measurement Closeout ──┬──► S7e Story-DAG ────────────┐
  (unblocks all empirics)  │                              │
                           ├──► S10 Prompt Regression CI  │
                           └──► S7b Orchestrator ──┬──────┤
                                 (unblocks C0)     │      │
                                                   ▼      ▼
S7c Streaming ─── independent ────────────────►  Conductor C0
S7d MCP ───────── after S7b.4 ────────────────►
S8 Contract Truth-Up ── independent, any time ─►
S9 Observability ────── after S7a ─────────────►
```

Genuinely parallel: **S7c** and **S8** depend on nothing in this diagram and can run alongside
S7a with a second pair of hands.

---

# §6 — Architectural Review: Additions, Removals, De-Overengineering

## 6.1 Remove — 868 MB of untracked vendored trees inside `src/`

| Tree | Size | Python files | Tracked in git? |
| :--- | ---: | ---: | :--- |
| `src/hermes_agent` | 728 MB | 3,634 | **No** |
| `src/grok_build` | 91 MB | 3 | No |
| `src/claude_code` | 46 MB | 0 | No |
| `src/open_code` | 3.4 MB | 0 | No |
| **`src/sagiha`** | — | **105** | Yes |

Untracked reference material sits inside the package root, and is the sole reason **both** pyright
and ruff carry exclusion lists — `pyproject.toml:63-70` and `:91-97`, each with its own prose
rationale for the same problem. It is also why `ruff check .` was red for an entire sprint (m-14)
and is why the `.sagiha/repo-cache` exclusion (N-C1) was missed: the pattern of "add another path
to another exclusion list" was already normalized.

**Proposal:** move all four to `reference/` at repo root, gitignored. Then delete both exclusion
lists. One structural change removes an entire class of configuration drift, ~35 s off every ruff
invocation, and 868 MB of accidental import-path surface.

## 6.2 Remove — three zero-rent ports (**N-M2**)

`advisory`, `meta_improver`, `toolchain` — zero importers, two closed blocks, ADR-0023 already
governs them. Deleting a Protocol is free and reversible: `ports/embedding.py` was deleted in S2
under exactly this rule and nothing missed it. Each deletion gets an ADR with re-promotion
conditions, so the design intent survives without the maintenance surface.

**Keep** `lsp` (imported by `composition.py`) and **build** `orchestrator` (§4.4).

## 6.3 Reconsider — `aoi/` and `runtime/` exist only because import contracts name them

`m-13` was correctly withdrawn (L-1): both carry good docstrings, and `.importlinter` names
`sagiha.runtime` in three contracts and `sagiha.aoi` in one, so deleting them breaks 4 of 5
contracts. But that reasoning is worth examining rather than accepting — **the packages are being
kept alive by the rules that reference them**, which is the tail wagging the dog.

`runtime/` earns its keep: it is a named CAR stratum and the `agency-not-runtime` contract is a
real invariant. `aoi/` does not — it is an empty package guarding against imports of code that
does not exist. **Proposal:** in S8, rewrite the `tcb-isolation` contract to name only real
modules and delete `aoi/`; re-create it when the first AOI adapter is written. Cost: one contract
edit. Benefit: the import contracts describe the architecture instead of preserving it.

## 6.4 Reconsider — docs mass is still 146,039 words

The budget gate is green at 14,899 normative words, and `retrieval: excluded` now covers **71
files / 146,039 words**. As `concept_review.md §2.2` argued, the mechanism manages the *label*,
not the mass: 146 k words still exist, still drift, still break links when moved, and still get
read by humans. The 101-word margin (**N-m3**) shows the ratchet is at its limit.

**Proposal (S8.4):** generated docs. `gen_event_catalog.py --check` is the only docs gate that has
never gone red, and that is not a coincidence — a generated doc cannot drift, cannot break its
own links, and costs zero budget. Extend the pattern to the port surface, tool schemas, config
schema, and CLI reference. Target: hand-written normative prose under 10,000 words, with ADRs
carrying the durable decisions.

## 6.5 Keep, unchanged — the parts that earned it

Re-verified this pass and **not** to be touched by any sprint above:

- **The CAR choke point** (`kernel/dispatch.py`) — unconditional `verify_grant`, `try/finally`
  lease, broad exception capture. One answer site for "can the agent do X."
- **`bool | None` gates where `None` never passes** — still the best single idea in the tree.
- **Refuse-at-load config** — `domain/config.py` rejects insecure states at construction.
- **Seed-only Layer 6, enforced by constructor shape.** No discipline required.
- **The dual `prefix_digest` / `stable_prefix_digest` instrument.**
- **PURE-argv allowlist placed in `kernel/policy/`** so the existing TCB import contract makes it
  agent-unwritable for free — still the best example of getting a security property by placement.
- **`e0/statistics.py`** — real McNemar, seeded bootstrap, Holm, pure stdlib.

## 6.6 Add — one small mechanism, high leverage

**A "no plausible fabrication" lint** (`concept_review.md §2.3`). C-1 was H5 recurring five
sprints after H1–H4 were fixed, because those were enumerated instances with no generalizing rule.
An AST check banning `except X: return <literal>` in `adapters/`, `outer_loop/evaluator/` and
`e0/` would have caught C-1 the day it was written, costs ~40 lines in `scripts/`, and belongs in
S8 alongside `check_port_rent.py`.

---

# §7 — Consolidated Action List

## Immediate — before any commit or push

1. **N-C1** — gitignore + ruff-exclude `.sagiha/`; make `repo_cache` cache dir test-local; delete leaked `__tmp__pytest-*` dirs
2. **N-C2** — fix the 2 failing benchmark-runner tests via an explicit `origin` discriminator
3. **N-m2** — wrap `repo_cache.py:76`; `ruff format` the importer
4. **N-C3** — run `verify.sh`; reconcile fix-plan §3/§4/§5 with what W9 actually landed
5. **M-2** — human authors the Podman CI job from `docs/implementation/ci-podman-perimeter.md`

## Sprint order

`S7a` → (`S7b` ∥ `S7c` ∥ `S8`) → (`S7d` after S7b.4, `S7e` after S7a, `S9`, `S10`) → `Conductor C0`

## Standing rules to add

1. **`verify.sh` before every commit, no exceptions.** It exists because memory-reported gate
   state is a defect class this project has now hit twice.
2. **A rule without a mechanism is not a rule.** ADR-0023 sat unenforced for two blocks. Every
   future governance ADR ships with the script that enforces it, or does not ship.
3. **A sprint has one theme and one falsifiable gate.** S7's bundling was the same shape as the
   Block 5 mega-scope two audits already flagged.
4. **An honest negative closes a sprint.** Applies with full force to S7a's ablations, including
   the outcome where retrieval is shelved.

---

# §8 — Appendix: Verification Commands

```bash
bash scripts/verify.sh                     # exit 1 today — pytest/ruff/format red
uv run pytest -q                           # 356 passed, 2 failed
uv run ruff check .                         # 344 errors (343 in .sagiha/repo-cache)
uv run ruff check src/sagiha                # 1 error (repo_cache.py:76 E501)
uv run ruff format --check .                # 37 files
uv run pyright src/sagiha                   # 0 errors  ✅
uv run lint-imports                         # 5/5 kept  ✅
python3 scripts/docs_budget.py --max 15000  # 14,899    ✅
python3 scripts/check_links.py              # 0 dead    ✅
python3 scripts/gen_event_catalog.py --check # in sync  ✅

# Where the lint errors actually live
uv run ruff check . 2>&1 | grep -oE "^\s+--> [^:]+" | sed 's|.*--> ||' | cut -d/ -f1-2 | sort | uniq -c | sort -rn

# Ports with zero importers (ADR-0023 rent check)
for p in advisory lsp meta_improver toolchain evaluator orchestrator memory; do
  echo "$p: $(grep -rln "ports.$p import" src/sagiha --include=*.py | grep -v '^src/sagiha/ports/' | tr '\n' ' ')"
done
```

**C-1 regression check** (should return hits on all three):

```bash
uv run python - <<'PY'
import asyncio, tempfile, os
from sagiha.adapters.indexer.fts5 import FTS5Indexer
ix = FTS5Indexer(db_path=os.path.join(tempfile.mkdtemp(), "i.db"))
ix.reindex_file("pkg/util.py", "def greet(name):\n    return 1\n")
async def m():
    for q in ["greet", "Fix the bug in greet() so it returns a name", "pkg.util.greet"]:
        print(repr(q), "->", len(await ix.search(q, limit=5)), "hits")
asyncio.run(m())
PY
```

---

*End of `Harness_LLM_orchestrator_aether_project_review_v210.md`. Immediate next step: §7's
five-item pre-commit list, then v2-S7a. The measurement track is the critical path — every
ablation-gated sprint downstream is waiting on a noise floor that does not exist yet.*
