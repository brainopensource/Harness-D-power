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
  run with `error_kind="stuck_loop"`. **This is too blunt, and §1.4 replaces it.**
- **Transcript integrity.** Every skipped `tool_use` block gets a synthetic error `ToolResult`. A
  dangling `tool_use` id is a provider-level protocol error on the *next* request, so a halted run
  must still leave a well-formed transcript. This is what makes a halted run resumable instead of
  dead.

### 1.3 Failure-triggered context drift — the degradation the repair loop causes

A repair loop feeds failures back into the context. That is the point, and it has a cost the
predecessor's design does not account for.

**Repeated tool failures degrade context *quality* independently of context *size*.** Stack traces,
retry noise, and error output accumulate; the original task intent is progressively diluted, and
subsequent attempts start following the **error narrative** rather than the goal. The window is not
full — the signal-to-noise ratio has collapsed inside a bounded window.

This is distinct from compaction drift, and the distinction is the useful part:

| | Addresses | Trigger | Fix |
| :--- | :--- | :--- | :--- |
| **Compaction drift** | Context *size* | Utilization threshold | Summarize whole exchanges |
| **Failure drift** | Context *quality* | Consecutive failures | **Re-inject task intent** |

**Mitigation: re-assert the task on failure, not only on compaction.** After a failed tool call or a
failed gate, the appended observation carries a condensed restatement of the task and its constraints
alongside the error — so the next attempt is anchored to the goal rather than to the last stack trace.

Three properties keep this from becoming its own problem:

- It is **appended, not prepended** — the frozen prefix is untouched, so the cache survives
  ([AD-2](#11-three-binding-decisions-carried-forward) applies unchanged).
- The restatement is **condensed and constant** — a varying restatement is just more noise.
- It is **bounded**: intent re-injection does not accumulate. One restatement per failure, replacing
  the previous one rather than stacking.

Credit: the pattern comes from field practice around hook-based intent re-injection on non-zero tool
exit; the framing of "size versus quality" degradation is what makes it a design rule rather than a
trick.

### 1.4 Loop guardrails — a typed policy, not one threshold

SAGIHA halts on three identical tool signatures. That single counter cannot distinguish *retrying a
read that returns the same bytes* from *re-running a command whose effect legitimately repeats*, and
it has exactly one response: kill the run. `agent/tool_guardrails.py` in `src/hermes_agent` models
this properly and AETHER adopts its shape.

**Three signals, each with its own thresholds** (illustrative defaults, all config values):

| Signal | Meaning | Warn | Block / halt |
| :--- | :--- | ---: | ---: |
| Exact repeated failure | Same tool, same args, same failure | 2 | 5 |
| Same-tool repeated failure | Same tool failing on varying args | 3 | 8 |
| Idempotent no-progress | An idempotent tool returning an unchanged result | 2 | 5 |

**`idempotent` and `mutating` are declared sets, and the distinction is load-bearing.** No-progress
detection is only meaningful for idempotent tools: re-reading a file and getting identical bytes is a
loop; re-running a mutating command and getting the same result may be correct. AETHER already
classifies tools by effect class for
[authorization](./rewrite_v300_seguranca_sandbox.md) — the guardrail reuses that classification rather
than inventing a second taxonomy.

Four properties of the design, all adopted:

1. **Two tiers: warn, then stop.** A warning becomes guidance appended to the transcript and never
   blocks execution. Halting is the second tier.
2. **Hard stops are opt-in.** Interactive sessions get a nudge; circuit-breaker behavior is a
   deliberate configuration choice. A harness that kills an interactive user's run on a heuristic is
   worse than one that warns them — and in autonomous mode the default flips.
3. **The controller is side-effect free.** It observes tool calls and *returns decisions*; the runtime
   decides whether a decision becomes guidance, a synthetic tool result, or a controlled halt. Pure
   policy, impure runtime — the same split as `PolicyEngine` versus `dispatch`, and it makes the
   thresholds unit-testable without a running agent.
4. **One failure classifier, shared with the UI.** Whatever decides "this tool call failed" for the
   guardrail is the same function that renders the user-visible error indicator. Divergence between
   what the system counts as a failure and what the operator sees is a debugging trap, and sharing the
   classifier closes it by construction.

**AETHER addition — a disposition ladder rather than a flat retry.** `next_gen_architecture_specs.md`
§2.1 proposes `rehydrate → replan → escalate (S1→S2) → checkpoint+abort`, each rung consuming
budget. A repair attempt that fails the same gate twice should not attempt a third identical repair;
it should change *strategy* — re-retrieve context, then re-plan, then escalate to Best-of-N across
worktrees, then checkpoint and stop. Which rung fires is a policy decision recorded in config, and
the ladder itself is an ablation target.

**The ladder needs a sibling for API failures.** The disposition ladder above handles *gate* failures.
Provider failures — rate limits, context-length errors, credential problems, transient upstream
errors — are a separate axis, and SAGIHA handles them with inline string matching (`_is_transient()`
in `adapters/model/fallback.py`). `agent/error_classifier.py` in `src/hermes_agent` replaces that with
a structured taxonomy and a **priority-ordered classification pipeline** mapping each failure to a
recovery action:

```
retry · rotate credential · fail over to another provider · compress context · abort
```

The non-obvious entry is the fourth. **"Compress context" is a recovery action**, not an error: a
context-length rejection is neither a retry nor an abort — it is a signal to compact and continue.
Treating it as transient burns the budget re-sending an over-long request; treating it as fatal
abandons a recoverable run. AETHER's `ModelProvider` port therefore surfaces a **typed classified
error**, not a raw exception, and the classification lives in one place rather than at each call site.
Refusals ([security §3.3](./rewrite_v300_seguranca_sandbox.md)) are one more disposition in the same
taxonomy.

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
edit mechanism, not a companion feature.

**Blast radius has a measured cost.** Practitioner data reported in the community field guide, useful
as a design constraint rather than as a result:

| Files touched simultaneously | Reported success rate |
| :--- | ---: |
| 1–3 | ~85% |
| 4–7 | ~60% |
| 8+ | ~40% |

Degradation also tracks session length — 15–25 conversation turns, or 80–100K accumulated tokens,
before earlier constraints start being dropped.

The design consequence is not "refuse large tasks". It is that **a task touching many files should be
decomposed into steps that each touch few**, with the localized set re-established per step rather
than carried as a growing working set. That is an argument for the disposition ladder (§1.2) and for
sub-agent delegation with explicit context passing
([autonomy §7.1](./rewrite_v300_autonomia_agi.md)) — and a caution against the intuition that a
bigger context window makes wide edits safe. It does not; it makes them affordable, which is a
different property. It is owned by
[context & memory](./rewrite_v300_contexto_memoria.md), and the roadmap sequences it **before** any
work on editor sophistication.

---

## 5b. Revision-A amendments from the competitor review

### 5b.1 Completion verification is a single gate where three references have a ladder

§3's T0–T3 ladder is cost-ordered and correct — but it validates **edits**. The question *"is this task
actually done?"* is answered by one `Evaluator.evaluate()` producing a tri-state `GateReport`. All
three references layer that question, at three price points:

```
  turn ends
     │
     ├─ [free]        stop detector — anchored regexes over the turn's last paragraph
     │                  detects premature bail-out; swaps the generic continuation nudge
     │                  for a bail-specific one; emits a labelled event so the panel's
     │                  precision/recall is auditable
     │
     ├─ [~free]       evidence ledger lookup — is there fresh proof covering the changed
     │                  scope, under the current tree digest?
     │
     ├─ [one call]    cheap structured evaluator — capped transcript, hard timeout,
     │                  fixed JSON: continue | candidate_complete | blocked
     │
     └─ [N calls]     adversarial panel — only on candidate_complete. N independent
                        skeptics, majority vote, auditing the implementer's evidence
                        rather than authoring their own
```

**The evidence ledger is the piece with no equivalent in our design and the cheapest to build.** A
table of `(run_id, root, canonical_command, kind, scope, status, exit_code, tree_digest)`, populated
deterministically from terminal results:

- Commands are split on `&&`, `||`, `;`, tokenized, and **canonicalized** — `pytest`,
  `python -m pytest` and `uv run pytest` collapse to one key.
- `kind` (test / build / lint / typecheck) derives from the canonical command; `scope` derives from
  whether arguments name targets.
- **A narrow pass is never promoted to "repo green."** `pytest tests/test_foo.py::test_bar` proves one
  thing; `pytest` proves another.
- Any workspace write **invalidates prior evidence.** Evidence is a claim about a tree state, not a
  property of the session.

It composes with §3 rather than competing: T3 can be *skipped* when fresh evidence already covers the
changed scope, which is a direct cost saving on the most expensive tier.

**Anti-ratchet is the property that matters most, and it is structural, not prompted.** Grok Build's
verifier prompt states the failure plainly: *"Raising a fresh nitpick each round while the criteria
hold is the failure mode that makes goals unfinishable."* The cheap implementation is to pass the
previous round's findings into the current round and require each to be resolved, treating novel
objections as a separate, lower-priority channel. **On an ≥8h unattended target a gate that can raise
its own bar between rounds is not a quality issue — it is a non-termination bug**, and neither the
progress signature nor the step cap in §1.2 prevents it.

Two supporting properties:

- **Policy-only guards.** The ledger *observes* and never decides; the guard *decides* and never
  observes. Same split as `PolicyEngine` versus `dispatch`, applied to verification, and it makes both
  halves testable in isolation.
- **Cheapest-first as a house rule.** The shape appears in at least four unrelated subsystems across
  the references — verification, memory consolidation, permission gating, benchmark tiering — which
  reads as convention rather than coincidence: *a gate sequence is ordered by ascending cost, and each
  stage's job is to make the next stage unnecessary.* §3 already follows it; naming it means the next
  ladder does too.

### 5b.2 Architect/Editor — the decision holds; one component of it separates out

A-016 ships the split **off** behind an ablation gate. Nothing in the review changes that, and one
finding sharpens it: the dominant failure mode in multi-agent coding pipelines is hand-off loss, and
the Claude Code corpus states the general rule for delegation — *"context is never inherited
automatically"*, a worker receives only its task string. An Architect/Editor split is that hand-off,
with prose as the channel.

What **does** separate cleanly from the split, and is worth taking regardless of how the ablation
lands:

**Syntactic pre-validation before persisting to disk.** §3's T1 tier parses *after* the write and rolls
back on failure. Validating the *candidate* content before the write is strictly cheaper — no write,
no checkpoint, no restore — and it turns a rollback into a rejected tool call whose error message the
model can act on immediately. The proposal is to move tree-sitter validation from post-write to
**pre-write on the candidate buffer**, keeping the post-write parse as a cross-check on batch
application.

On implementation: the review's suggestion of a Rust parser is a **performance** question, not a
correctness one, and it is premature. Tree-sitter's Python bindings already call into C; a parse is
~2 ms/file per §3. If pre-write validation ever shows up in a profile, that is an
[RT-1/RT-3](./rewrite_v300_decisoes_runtime.md) trigger behind an existing port, not an architectural
decision.

### 5b.3 Anchor-sequence matching is already the decision — and it should be ablatable

A-013 already specifies anchor-sequence matching and already cites Codex's `seek_sequence.rs` as the
reference. Recorded here so the review does not adopt it twice.

What the teardowns add is **method, not mechanism**. Grok Build implements **three** anchor schemes
behind one trait — content-only hash · chunk fingerprint · checkpoint chain — declares the metrics
(**read amplification**, ambiguity rate), names a starting favourite, and lets the harness decide. It
also returns a three-valued result — `Found | Ambiguous | NotFound` over a bounded search radius —
which matches Claude Code's documented exact → fuzzy-with-warning → error path.

Two proposals follow:

1. **Keep A-013's choice; make the edit representation a substitutable seam** so a second scheme is a
   swap rather than a rewrite. Cheap at M0, a rewrite at M2.
2. **Adopt the three-valued result explicitly.** `Ambiguous` is a distinct outcome from `NotFound` and
   deserves a distinct message: "your anchor matched in three places after normalization" is
   actionable; "not found" sends the model back to re-read the file.

### 5b.4 Hunk-level authorship attribution

Currently we have no answer to *"who changed this file"*. Three cases need one, and the third is the
one that matters for measurement:

- An operator edits a file in the TUI while a run is in flight.
- A formatter, watcher or build step mutates files under the agent.
- **`tests_unmodified` asks *whether* tests changed, not *by whom*.** Attribution turns "the diff is
  unexpected" into "the diff is unexpected **and it wasn't us**", which is a materially stronger
  statement for a hard gate that guards invariant I7.

The reference shape is an actor owning hunk state on a dedicated task — no locks — receiving commands
from both the edit tool and a filesystem-notify loop, tagging each hunk `Agent` or `External`, and
supporting per-hunk revert. In Python that is a single `asyncio` task owning state, which is natural.

**Grade B, M3.** It requires a filesystem watcher and an ownership discipline, and the container
perimeter already reduces the surface for external mutation. It becomes necessary the moment a human
can edit mid-run — which is exactly when the TUI grows a diff-review surface.

### 5b.5 Retry policy: two non-obvious rows, and a clearing-condition axis

§1.4's API taxonomy maps failures to `retry · rotate · failover · compress · abort`. Two entries from
the reference retry tables are worth adopting because neither is intuitive:

- **429 gets *fewer* retries, not more.** Grok Build caps rate-limit retries at 2 against a general
  budget of 15, with the reason stated: *"rate-limit waits can be long and there is no point burning a
  long backoff just to be rate-limited again."*
- **413 / image-processing errors strip images and retry once, off-budget.** A recoverable failure with
  a specific, cheap remedy should not consume the general retry budget.
- Plus a **server hint channel** (`x-should-retry: false`) letting a provider mark a specific failure
  non-retryable without a client release.

And a re-framing of the taxonomy itself: key each degraded state by **what event would clear it**, not
only by what caused it — self-heals next turn · needs the context budget to change · needs a successful
call · needs re-auth. The last is the load-bearing one: waiting for a successful call deadlocks when
context is already over the window, which is precisely the state where compaction most needs to run.

---

## 5c. Track B cross-check — fork F7, and two adoptions

### 5c.1 Fork F7 — Architect/Editor: ablation gate, or foundation

| | **Track A** (A-016) | **Track B** (ADR-01, Sprint 1) |
| :--- | :--- | :--- |
| Status | Seam built; **shipped off** | Built and **enabled** as a foundational mechanism |
| Architect | An `editor` role in the config-level role→tier binding | `agency/architect.py` — Opus 5, conceptual plan, **no write tools** |
| Editor | — | `agency/editor.py` — Sonnet/Haiku, surgical `SEARCH/REPLACE` blocks |
| Gate to enable | An ablation on the smoke suite showing a resolve-rate gain whose CI excludes the noise floor, at acceptable cost delta | None; it is the design |

**The argument for Track B's side, stated fairly and at its strongest.** Reasoning and formatting are
different skills, and the cost asymmetry is real: an Opus-tier plan followed by Haiku-tier diffs can be
*cheaper* than Opus doing both, not more expensive, if the plan is short and the diffs are many. The
architect's context also stays clean of tool-call noise, which §5.1's degradation curve says matters.
And B's coupling is the interesting part — the AST pre-validation loop returns syntax errors straight
to the **editor**, so the architect never sees formatting churn at all.

**The argument for keeping it off until measured.** It introduces a lossy hand-off, and hand-off loss
is the dominant failure mode in multi-agent coding pipelines — the editor sees prose, not the
architect's context ([autonomy §7.1](./rewrite_v300_autonomia_agi.md): context is never inherited).
Frontier models in 2026 emit correct anchored edits directly, which is the condition that made the
pattern valuable when it was proposed and has since weakened. And it is a **structural** commitment:
once `architect.py` and `editor.py` are peers in the run loop, turning the split off is a refactor
rather than a config flag.

**A reconciliation:** build it the way Track B specifies — as two modules with a clean seam — and bind
the *enablement* to config the way A-016 specifies. Then B gets the architecture and A gets the
ablation, and the first M2 sweep answers the question with a number instead of a preference. The cost
of this reconciliation is one config branch; the cost of getting it wrong in either direction is a
doubled per-task bill or a mechanism nobody can turn off.

### 5c.2 Adopt: the pre-validation loop returns to the editor, not the architect

Independent of F7, Track B's ADR-01 sequence has a detail worth taking. On a syntax rejection, the
error and its location are re-injected **to whichever component produced the diff**, and the file on
disk is left untouched. §5b.2 proposes moving validation pre-write; B's diagram adds the routing rule.

This matters even in a single-model design: a syntax error is a *formatting* failure, and routing it
back through a planning turn wastes an expensive round-trip re-deriving intent that never changed.

### 5c.3 Adopt: `SEARCH/REPLACE` block markers as the wire form

Track B specifies the Aider-style `<<<<<<< SEARCH ... ======= ... >>>>>>>` form explicitly. A-013
specifies anchored search/replace and never says what the model actually emits. The marker form is
worth pinning for two reasons that are not aesthetic: models have seen it heavily in training, and it
is **parseable from a partial stream**, which is what would make [§2.3's deferred streaming
application](#23-streaming-application) possible if wall-clock ever becomes the binding metric.

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
| Loop guardrails | Three typed signals with separate warn/stop thresholds; idempotent vs mutating sets; pure controller; hard stops opt-in interactively | Threshold ablation |
| API failures | Typed taxonomy → `retry · rotate · failover · compress · abort`, classified in one place | — |
| Failure drift | Condensed task intent re-injected on failure; appended, constant, bounded | Ablation |
| Blast radius per step | Prefer 1–3 files; decompose rather than widen the working set | Measurement on our own suites |
| Disposition ladder | `rehydrate → replan → escalate → checkpoint+abort` | Ablation per rung |
| Architect/Editor split | Seam built, **shipped off** (unchanged by the review; §5b.2) | Ablation clearing the noise floor at acceptable cost |
| Streaming patch application | Deferred | Wall-clock per resolved task becomes the binding metric |
| **Completion verification** | Proposed ladder: stop detector → evidence ledger → cheap evaluator → adversarial panel (§5b.1) | Per-tier ablation; the ledger is near-free and can precede the rest |
| **Anti-ratchet** | Prior-round findings passed forward and required to be resolved; novel objections are a lower-priority channel (§5b.1) | None — it is a termination property |
| **Evidence ledger** | `(run_id, root, canonical_command, kind, scope, status, tree_digest)`; narrow never promotes to repo-green; any write invalidates (§5b.1) | — |
| **Syntax validation timing** | Pre-write on the candidate buffer, with the post-write parse kept as a batch cross-check (§5b.2) | Profile, if it ever appears in one |
| **Anchor result** | Three-valued: `Found` / `Ambiguous` / `NotFound`, with distinct messages (§5b.3) | — |
| **Edit representation** | A substitutable seam, so a second anchor scheme is a swap not a rewrite (§5b.3) | Read-amplification / ambiguity-rate ablation |
| Hunk authorship attribution | `Agent` vs `External`, actor-owned, per-hunk revert (§5b.4) | Grade B; becomes necessary with a mid-run diff-review surface |
| Retry policy | 429 gets fewer retries; 413 strips images and retries once off-budget; server hint honoured (§5b.5) | — |
| Degraded-state taxonomy | Keyed by **clearing condition**, not only by cause (§5b.5) | — |
