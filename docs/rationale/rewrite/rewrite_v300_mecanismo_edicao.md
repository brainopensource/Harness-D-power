---
status: rationale
retrieval: excluded
updated: 2026-08-05
---

# AETHER v3.0.0 — Code Editing Mechanism and Failure Resilience

> [!NOTE]
> **LLM / AI AGENT NOTICE**: This file is Phase-0 rationale for the AETHER rewrite. It is not
> binding and defines no contract. Contracts live in `src/`. Read it for *why*, not *what*.

Answers RFP [§4-B](../reviews/review_project_rewrite_v300.md).

---

## 0. The finding that orders everything else

`docs/implementation/planning_final_sprint_rev2.md` §1 records the defect that dominated SAGIHA's
score: `RunLoop.run()` called `self._evaluator.evaluate()` **after the step loop had already
exited**. The gate ran once, and *its verdict was returned to the caller and shown to nobody*. There
was no path from `GateReport.admitted == False` back into a model call.

A one-shot agent with a perfect sandbox and honest gates lands 20–40%. The difference between that
and 70–80% is not a better editor. **It is the feedback edge from a failing test back into the
model's context.** v2-S7f added it; AETHER inherits it as a founding property rather than a late
patch.

So this document is ordered by leverage, not by pipeline sequence:

1. The repair loop (§1) — the largest single lever.
2. Edit application (§2) — the mechanism that must not lose the gains.
3. Verification and rollback (§3) — the cost floor on a bad edit.
4. Architect/Editor split (§4) — deferred behind an ablation gate.

---

## 1. The repair loop

### 1.1 Three binding decisions carried forward

Restated from `planning_final_sprint_rev2.md` §3 (AD-1, AD-2, AD-3) because they are correct and
non-obvious:

| # | Decision | Why |
| :--- | :--- | :--- |
| **AD-1** | Repair lives **inside the run loop**, not in the benchmark runner or an orchestrator above it | Repair must share one transcript, one compaction budget and one `run_id` with the work being repaired. Hoisting it produces a second conversation that has to be told what the first one did |
| **AD-2** | The gate verdict re-enters as a **tool-result-shaped message**, appended to the existing exchange — never as a new system prompt | A second system prompt **forks the stable prefix**, invalidating every cached token from the breakpoint onward. On a long run this can cost more than the repair saves. See [context & cache](./rewrite_v300_contexto_memoria.md) |
| **AD-3** | Gate feedback is `trusted=True` | It originates from our own evaluator, not from repository or network content. It is one of the few inputs that legitimately carries instruction authority — see [security](./rewrite_v300_seguranca_sandbox.md) |

### 1.2 Termination — the part most implementations get wrong

An unbounded repair loop is a budget incinerator. SAGIHA's mechanism is sound and is kept:

- **Progress signature.** `sha256` over the set of failed gate criteria plus the tail of the failure
  output, **deliberately excluding the attempt number**. A repeated signature means the agent
  produced a different edit that failed in exactly the same way. Abort with
  `RepairAbandoned(reason="no_progress")` rather than spending another attempt.
- **Stuck detection.** Three identical tool-call signatures (`_STUCK_REPEAT_THRESHOLD = 3`) ends the
  run with `error_kind="stuck_loop"`.
- **Transcript integrity.** Every skipped `tool_use` block gets a synthetic error `ToolResult`. A
  dangling `tool_use` id is a provider-level protocol error on the *next* request, so a halted run
  must still leave a well-formed transcript. This is what makes a halted run resumable instead of
  dead.

**AETHER addition — a disposition ladder rather than a flat retry.** `next_gen_architecture_specs.md`
§2.1 proposes `rehydrate → replan → escalate (S1→S2) → checkpoint+abort`, each rung consuming
budget. A repair attempt that fails the same gate twice should not attempt a third identical repair;
it should change *strategy* — re-retrieve context, then re-plan, then escalate to Best-of-N across
worktrees, then checkpoint and stop. Which rung fires is a policy decision recorded in config, and
the ladder itself is an ablation target.

---

## 2. Edit application

### 2.1 Comparison

| Mechanism | Failure mode | Verdict |
| :--- | :--- | :--- |
| **Whole-file rewrite** | Token cost linear in file size; the model silently drops unrelated code it did not "see a reason" to keep | Rejected. Only survives as the fallback for new files |
| **Line-number diffs (unified diff with `@@` hunks)** | Line numbers go stale the instant any earlier edit lands. Models are unreliable at counting lines | Rejected as the primary path |
| **Anchored search/replace** (Aider blocks; SAGIHA `apply_edit`) | Anchor not found, or found more times than expected | **Primary.** Position-independent; failure is loud and locally recoverable |
| **AST-scoped edits** (replace a named function/class node) | Requires a parseable file — unusable for the partially-broken states that occur mid-repair, and for config, markdown, and unsupported languages | **Secondary**, for structural refactors where it is genuinely stronger |

### 2.2 The primary path

Anchored search/replace with three properties, two of which SAGIHA already has:

1. **`expected_occurrences`, explicit and required.** `apply_edit` already takes it. An anchor that
   matches a different number of times than stated is a **failure**, not a "replace the first one".
   This single parameter eliminates the most common silent corruption in agentic editing.
2. **Anchor-sequence matching, not string equality.** Codex's `apply-patch` crate implements this in
   `seek_sequence.rs`: locate a hunk by its sequence of surrounding context lines, tolerating
   whitespace normalization, rather than requiring a byte-exact match of the whole block. This is
   the difference between an editor that works on a real repository and one that works on the
   model's memory of a repository. **SAGIHA does not have this; AETHER needs it.**
3. **Read-before-write enforcement.** An edit to a file the agent has not read in this session is
   rejected by policy. The agent is editing its assumption, not the file.

The tool surface is deliberately larger than SAGIHA's six builtins: `apply_edit` (anchored, single),
`apply_edits` (batch, transactional — all or none), `write_file` (new files only), plus the
navigation tools. A batch edit that half-applies is a corrupt working tree; making the batch
transactional is cheaper than making the agent recover from one.

### 2.3 Streaming application

Codex's `streaming_parser.rs` applies patch hunks as the model emits them, rather than after the
message completes. Attractive for latency, and **deferred**: it makes rollback semantics
substantially harder, and latency inside a step is not the binding constraint on resolve rate.
Recorded as a known option with a trigger — revisit if wall-clock per resolved task, not resolve
rate, becomes the limiting metric.

---

## 3. Verification and rollback

Three tiers, ordered by cost, each gating the next. The principle: **never pay for an expensive
check when a cheap one would have caught it.**

| Tier | Check | Cost | On failure |
| :--- | :--- | ---: | :--- |
| **T0** | Anchor resolution and `expected_occurrences` | µs | Reject the edit; return the mismatch to the model. Nothing is written |
| **T1** | **Tree-sitter parse of every touched file** | ~2 ms/file | Roll back the edit, return the parse error with its location |
| **T2** | Linters, type checkers, LSP diagnostics | 0.1–5 s | Feed diagnostics back as a repair observation. Do **not** roll back — a type error is often a legitimate intermediate state mid-refactor |
| **T3** | Test suite in the sandbox | 5 s – 5 min | Repair loop, per §1 |

**Tree-sitter, not `ast.parse`.** The RFP suggests `ast.parse`. That is Python-only. AETHER is
measured on SWE-bench Pro, which spans multiple languages, and the project already depends on
`tree-sitter` and `tree-sitter-language-pack` for indexing. One parser serving both syntax
validation and the repo map is less code and more coverage.

**Rollback is git, not a copy.** Every candidate runs in its own worktree. `checkpoint(label)`
before an edit batch and `restore(sha)` on T1 failure — SAGIHA's `Workspace` port already carries
both. There is no separate undo stack to keep consistent, and the checkpoint is inspectable
afterward for trajectory analysis.

**Where the boundary sits.** T0/T1 are deterministic and must never consult a model. If a parse
fails, the answer is the parse error, not an LLM's opinion about the parse error.

---

## 4. Architect/Editor split — deferred behind an ablation gate

The proposal: one model proposes the change in prose with no tool access; a second applies it as a
surgical diff.

**Arguments for.** Reasoning and formatting are different skills; a cheaper model can often apply a
well-specified diff; the architect's context stays clean of tool-call noise.

**Arguments against.** It roughly doubles per-task cost. It introduces a lossy hand-off — the editor
sees prose, not the architect's full context — and hand-off loss is the dominant failure mode in
multi-agent coding pipelines. Frontier models in 2026 are markedly better at emitting correct
anchored edits directly than they were when the pattern was proposed.

**Decision: build the seam, do not enable the split.** The model-role binding already exists in
config (`next_gen_architecture_specs.md` §1.3 binds roles to tiers, requiring `scoring` to differ
from `execution`). Adding an `editor` role is configuration, not architecture. It ships **off**, and
turns on only if an ablation on the smoke suite shows a resolve-rate gain whose CI excludes the A/A
noise floor, at acceptable cost delta.

This is the standing pattern for every contested mechanism in AETHER: **make it a config-level
ablation, ship it off, let the number decide.** RFP §1.1 requires exactly this.

---

## 5. Localization — the lever that is not in the RFP

Worth stating because it likely outweighs everything in §2. `planning_future_sprints.md` §2 records
that **Agentless reaches ~45% on SWE-bench Verified with no agent loop at all**, at roughly a tenth
of the cost, and AutoCodeRover ~52%. Their entire edge is picking the right five files.

An agent that edits the wrong file perfectly scores zero. Retrieval-before-edit — tree-sitter
skeleton repo map, symbol search, code-graph impact analysis — is therefore a prerequisite for the
edit mechanism, not a companion feature. It is owned by
[context & memory](./rewrite_v300_contexto_memoria.md), and the roadmap sequences it **before** any
work on editor sophistication.

---

## 6. Summary

| Decision | Choice | Reversal condition |
| :--- | :--- | :--- |
| Primary edit mechanism | Anchored search/replace, required `expected_occurrences`, anchor-sequence matching | Ablation showing AST-scoped edits win on multi-file refactors |
| AST-scoped edits | Secondary, structural refactors only | — |
| Syntax validation | Tree-sitter parse of every touched file, pre-test | — |
| Rollback | Git worktree checkpoint/restore | — |
| Batch edits | Transactional — all or none | — |
| Read-before-write | Enforced by policy | — |
| Repair loop | Inside the run loop; tool-result-shaped feedback; trusted; progress-signature termination | — |
| Disposition ladder | `rehydrate → replan → escalate → checkpoint+abort` | Ablation per rung |
| Architect/Editor split | Seam built, **shipped off** | Ablation clearing the noise floor at acceptable cost |
| Streaming patch application | Deferred | Wall-clock per resolved task becomes the binding metric |
