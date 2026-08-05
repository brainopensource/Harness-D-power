---
status: rationale
retrieval: excluded
updated: 2026-08-05
---

# Competitor research → rewrite plan: proposed amendments

> [!NOTE]
> **LLM / AI AGENT NOTICE**: Phase-0 rationale. Not binding, defines no contract, **decides nothing**.
> Contracts live in `src/`.

**What this is.** The four teardowns in this directory produced **78 numbered proposals (P1–P78)**
from Grok Build, Hermes (agent + self-evolution), and the Claude Code reference corpus. This document
does the next step: it reads those 78 against the **twelve documents of the rewrite plan** in
[`docs/rationale/rewrite/`](../../rationale/rewrite/README.md) and says, for each, whether the plan
already has it, nearly has it, or does not have it — and where the missing ones would go.

**Suggestions only.** Every item below is phrased as an amendment for Tech Lead A to accept, defer or
decline. Several would change decisions already recorded in
[the ADR set](../../rationale/rewrite/rewrite_v300_decisoes_adr.md); those are marked. Nothing here is
adopted, and per RFP §1.1 anything that changes a mechanism needs an ablation before production, not
an argument.

---

## 1. The scoreboard

| Verdict | Count | Meaning |
| :--- | ---: | :--- |
| **Already in the plan** | 19 | The plan has it, sometimes better-stated than the reference |
| **Nearly there — sharpen** | 17 | The plan has the idea; the reference adds a mechanism, a bound, or a name |
| **Genuine gap** | 34 | Not in the plan in any form |
| **Decline / already declined** | 8 | Recorded so it is not rediscovered |

The 19 "already there" are worth naming, because independent convergence is the strongest evidence we
have that a decision is right and it should not be quietly re-litigated:

sub-agent depth 1 and never-inherited context (A-019 ≡ P-Claude/Grok/Hermes) · fan-out sized by
context pressure (autonomy §7.2 ≡ P71) · cache-sharing auxiliary forks (A-023 ≡ P51) · code-mode
orchestration (autonomy §3 ≡ P70) · offline skill consolidation (autonomy §2.1 ≡ P29/P74) · egress
domain-fronting caveat (security §2.1 ≡ P76) · self-DoS lifecycle class (security §3.4 ≡ P57) ·
judge context budget (context §5.1 ≡ P65) · anchored edits with `expected_occurrences` (A-013) ·
tri-state gates · pure controllers (A-022) · TaintGate provenance · hooks may veto never grant
(security §1.5 ≡ P14) · effect classes narrowed per call · retrieval-before-edit as a pipeline stage ·
context rot as structural · MECW and the 70% cliff · the reversal curse (autonomy §4) · standing
declines.

The rest of this document is the other 51.

---

## 2. The seven highest-leverage additions

Ordered by what I judge to be expected value, not by how interesting they are. Each is expanded in
§3 under its target document.

### 2.1 Completion verification is a single gate where three references have a ladder

**Gap.** [`rewrite_v300_mecanismo_edicao.md`](../../rationale/rewrite/rewrite_v300_mecanismo_edicao.md)
has an excellent cost-ordered ladder — T0 anchor resolution → T1 tree-sitter → T2 linters → T3 test
suite — but that ladder validates **edits**. The question *"is this task actually done?"* is answered
by one `Evaluator.evaluate()` call producing a tri-state `GateReport`.

All three references layer this, and each layer sits at a different price point:

| | Cost per check | What it establishes | Source |
| :--- | :--- | :--- | :--- |
| Regex stop detector | zero | the model is bailing out prematurely | Grok Build, 9 anchored patterns (P21) |
| Evidence ledger | ~zero (SQLite) | the agent ran something relevant, and the tree has not changed since | Hermes (P48) |
| Cheap structured evaluator | one small call, 30 s cap | `continue \| candidate_complete \| blocked` | Grok Build (P18) |
| Adversarial panel | N sub-agent runs | an independent adversary could not refute the claim | Grok Build, N=3 majority (P19) |

And the single most important prompt-level rule any of them carries — **anti-ratchet** (P20): on a
re-verification round the gate's primary job is checking that *prior* gaps are fixed, and a new
objection counts only if it is a demonstrable defect or an unmet gating criterion, never a
test-construction preference the previous round accepted. Grok Build states plainly why: *"Raising a
fresh nitpick each round while the criteria hold is the failure mode that makes goals unfinishable."*

**Why this is first.** Our repair loop's termination is currently a progress signature plus a step
cap. Neither prevents an evaluator that gets stricter as the run proceeds. On an 8-hour unattended
target that is not a quality issue, it is a non-termination bug.

### 2.2 Tool semantics can drift under a paired measurement

**Gap.** Our entire defensible claim is **scaffold-attributable lift** — a paired delta on a *fixed*
model. That holds everything constant except the intervention. It does not currently hold the **tool
contract** constant.

Grok Build maintains a `TOOL_VERSION_REGISTRY`: every version-managed tool has named contract versions
(`current`, `legacy-0.4.10`), each with an independent lifecycle (`Active` / `Deprecated` /
`RemovalCandidate`), a replacement, and a one-line summary of what that version's behaviour *is*. Its
`search_replace` really does carry two behaviours — for instance whether an empty `old_string` may
overwrite an existing non-empty file.

If our edit tool's occurrence semantics or our grep's default scope changes between the M1b baseline
and an M2 ablation, the delta measures two things at once and no one will notice.

**Cost:** a version field on the tool descriptor, a registry, and the preset recorded in the run
manifest. Free at M0. Impossible to retrofit onto historical results.

### 2.3 Three M0 domain types that are free now and breaking later

- **P3 · `RunOutcome` as a sum type.** Five pause reasons already exist across three of our documents
  — the disposition ladder's rungs, the API taxonomy's `abort`, the `ask` permission state,
  `BudgetExhausted`, and `RepairAbandoned(no_progress)` — and **none of them share a type.** Grok
  Build's `Completed | Paused{kind} | BudgetExceeded | Cancelled | Failed`, with
  `PauseKind = User | BackOff | NoProgress | Verification | Infra`, maps onto ours almost exactly.
  An operator watching an 8-hour run needs "paused, waiting on you" and "paused, backing off" to be
  visibly different things.
- **P4 · `replayed: bool` on effect-carrying events.** T8 determinism is about *model calls*. A
  resumed run replays its journal, and every non-model effect in that replay fires twice — duplicate
  telemetry, duplicate notifications, duplicate scratch writes. Marking the replay lets each consumer
  decide.
- **P17 · Fail-closed drive state on resume.** Grok Build's `GoalStatus` deserializes **any** unknown
  or forward-version wire value to `UserPaused`, never `Active`, with the invariant stated: a status
  this build cannot interpret must restore as a resumable paused run, never a self-driving one. We
  already re-mint grants rather than restoring them; this is the same posture applied to the run's own
  *autonomy*, and it is one enum plus one deserializer.

### 2.4 There is no seam that answers "what kind of run is this?"

**Gap.** Hermes' `coding_context.py` is *"the single place that decides whether we're in that posture
and what it implies, so the rest of the codebase never re-derives 'are we coding?' on its own."* A
frozen `RuntimeMode` selected from a small `ContextProfile` registry, where **a profile is data** — it
declares the toolset, the operating brief, and hints for model routing, memory policy and sub-agent
behaviour. Five consumers read the same resolved object.

AETHER will face the same question in at least four forms: benchmark run vs interactive; container vs
host; Tier 0 local model vs Tier 2 frontier; single-language vs polyglot repository. The alternative
to a profile object is that question re-answered in eight places with eight slightly different
answers — and a benchmark run that cannot pin its profile in the manifest.

Attached to it, two cheap context-budget mechanisms we lack the mechanism for:

- **P67 · Rules vs skills as a structural split.** A constraint on any output is a *rule* and is
  always on; a procedure for a task type is a *skill* and loads on invocation. Context §5.3 asks for a
  rule budget; this is the test that decides what counts against it.
- **P66 · Path-scoped instruction modules.** Context §5.3 point 3 says path-scoping beats a global
  rule set and stops there. The Claude Code corpus gives the mechanism and a claimed **40–50%
  reduction in always-on context with no loss of coverage.**
- **P47 · Disclosed staleness.** Rather than refreshing a repo snapshot per turn (cache-hostile) or
  letting it silently rot (wrong), the brief tells the model the snapshot is point-in-time and to
  re-derive before acting. Elegant, and it costs one sentence.

### 2.5 Budget is not correct under fan-out

**P2 · Two-phase reservation.** Our `ResourceGovernor` leases concurrency but records spend *after the
fact*. Under Best-of-N, N candidates each check `remaining_budget() > 0`, all pass, all spend. Bounded
by N — which is exactly the knob M4 increases. Grok Build reserves before spawning and releases the
remainder after.

**P54 · Per-agent budgets are independent, and the plan should say so.** A-019 gives a sub-agent "its
own budget". Hermes states the consequence its design creates: *"total iterations across parent +
subagents can exceed the parent's cap."* If our governor issues per-child budgets, the run manifest
needs the **tree total** and there should be a separate global ceiling.

**P63 · Turn caps keyed to task class, with an explicit incomplete terminal state.** Claude Code's
ranges: 5 for simple retrieval, 20–30 for multi-step coding, 50 for extended autonomous work — set
per task type *"so a single slow task does not starve others in a multi-agent pipeline."* And check
the terminal `stop_reason`: hitting the cap is not the same outcome as failing.

**P55 · Refund non-model iterations.** Hermes refunds `execute_code` iterations because they consume
no model call. Charging a non-model step against a model-call budget makes the budget mean two things.

### 2.6 Compaction latency and one cache rule we do not state

**P24 · Prefire two-pass compaction.** Our compactor is preflight-and-idle, which is good, but it
still runs synchronously at the threshold. Grok Build splits it: **pass 1** summarizes ~95% of history
by estimated-token weight into `NOTE₁`, fired **in the background 10 percentage points below the
trigger**; **pass 2** rewrites `NOTE₁` plus the ~5% tail synchronously at compaction time — and pass-2
latency is dominated by tail prefill, which is small by construction. Validity is a **cheap prefix
fingerprint**: pass 2 applies `NOTE₁` only if the live conversation still has that exact prefix. An
edit, rewind or model switch invalidates it and pass 1 is wasted, never wrong. The split index snaps
to tool boundaries. Seven distinct prefire outcomes are recorded as stable telemetry keys so the
optimization's hit rate is observable rather than assumed.

**P50 · A rule we should state explicitly: rewriting sent history is cache-hostile until measured.**
Hermes' micro-compaction amortizes compaction per turn and its own documentation argues against it —
*"each pass rewrites already-sent history, which breaks the provider prompt-cache prefix every turn"* —
and it ships **off by default**. Two teams, same problem, opposite answers, one of them documented as
a mistake. Our cost model carries the 1.25×/0.1× asymmetry; the rule that follows is that any feature
rewriting the prefix per turn converts every cached read into a write, and that multiplier belongs in
its ablation before it can ship.

**P5 · One token estimator.** Grok Build's is 255 lines with no dependencies and is documented as the
single source of truth for the context display, the auto-compact gate, the preflight overflow check
and every renderer. If our compaction trigger and our TUI meter disagree about how full the window is,
an operator cannot tell whether a surprising compaction was correct. Estimators drift silently.

### 2.7 Durability primitives for T5 and for benchmark scale

**P56 · One content-addressed checkpoint store across all worktrees.** Hermes' v1 kept a full shadow
git repo per working directory: *"A single user with a dozen worktrees of the same repo burned ~40 MB
each (~500 MB total) storing the same blobs over and over."* v2 is a single shared store with
`refs/hermes/<hash16>` per project, letting git's object DB deduplicate. **Our benchmark harness will
create many worktrees of the same upstream repository at higher multiplicity than any user ever
would** — this is the pathological case, and the store layout costs nothing to decide at M0.

**P58 · Hard deadlines on every read that can block in native code.** Hermes' `bounded_response.py`
documents the subtlety precisely: `httpx.iter_bytes()` blocks *inside* the socket read, so a deadline
checked between chunks cannot interrupt a server that opens a body and stalls. The fix runs the read
on a daemon thread and the caller waits with a hard deadline. An agent hung indefinitely reading an
error message is exactly the failure that kills an 8-hour unattended run.

**P16 · The checkpoint is a composite, not a git ref.** Grok Build's rewind checkpoint bundles
per-domain state — filesystem, hunk delta, git HEAD/index — with an atomic restore across all enabled
domains. Our checkpoint is `git checkpoint/restore`. The moment we add an index, a memory store or a
scratch dir to run state, a git-only checkpoint silently stops being a complete rollback. Deciding
whether the type is `GitRef` or `dict[domain, DomainCheckpoint]` is nearly free at M0.

**P40 · Content-hashed sidecars for durable queues.** Payload plus a `.meta.json` sidecar with a
`sha256`; recover by scanning and verifying at startup, before admitting new work; count losses by
reason (`missing_tmp` / `sha_mismatch` / `io_error` / `parse_error`). Applicable to the trajectory
store and any telemetry upload path.

---

## 3. Per-document amendments

Organized by target document so each can be actioned independently.

### 3.1 → [`rewrite_v300_blueprint_arquitetura.md`](../../rationale/rewrite/rewrite_v300_blueprint_arquitetura.md)

| # | Proposed addition | Where | Cost |
| :--- | :--- | :--- | :--- |
| **P3** | `RunOutcome` sum type with a typed `PauseKind` in `domain/`; surfaced on the event stream; rendered distinctly by the TUI | §7 event stream, §8 package layout | M0, near zero |
| **P4** | `replayed: bool` on effect-carrying events; an idempotency classification for each effect family | §7 | M0, near zero |
| **P2** | `ResourceGovernor` gains `reserve` / `commit` / `release` alongside the existing lease | §3.1 port catalog | M1a, small |
| **P16** | Checkpoint as a composite of independently-enabled domains with atomic restore | §3.1 `Workspace` | M0 decision, M2 build |
| **P48** | A `VerificationLedger` seam — decide at M0 whether it is a port, a `TrajectoryStore` table, or an `Evaluator` internal | §3.1 / §3.2 | M0 decision |
| **P30** | Tool descriptors carry a `contract_version`; a registry maps tool → supported versions with lifecycle | §3.1 `ToolRegistry` | M0, small |
| **P46** | A resolved, immutable `RunProfile` (data, not code) declaring toolset, brief, model hint, memory policy | §4 loop, §8 | M0/M1a |
| **P63** | Turn cap keyed to task class; `MaxTurnsReached` as a distinct terminal outcome, not a failure | §4, feeds P3 | M1a |
| **P5** | One token estimator module, imported by the gate, the assembler and every renderer | §5 context assembly | M1a, trivial |
| **P41** | Every enum reaching telemetry declares a stable wire string, pinned by a test | §7 | M0, trivial |

**On §6 (Workflow DAG).** No change proposed to A-024. Two notes for the record: Grok Build's
workflow-as-Rhai-script (**P6**) is the only reference with a comparable abstraction and it went the
other way, while Claude Code states *"no DAG orchestrator"* as a design principle. That makes us the
outlier among four designs — which A-024's M2 reversal condition already anticipates. See **P62** in
§3.4 for a suggestion that turns this from a standing disagreement into a measurement.

### 3.2 → [`rewrite_v300_mecanismo_edicao.md`](../../rationale/rewrite/rewrite_v300_mecanismo_edicao.md)

This document takes the largest share, because completion verification is where the plan is thinnest
relative to the references.

**A new §1.5 — the completion cascade.** Proposed shape, with the price points made explicit:

```
  turn ends
     │
     ├─ [free]      stop detector: anchored regexes over the last paragraph
     │                 → bail-specific continuation nudge, labelled event for
     │                   precision/recall audit  (P21)
     │
     ├─ [~free]     evidence ledger lookup: is there fresh proof for the
     │                 changed scope, under the current tree digest?  (P48)
     │
     ├─ [one call]  cheap structured evaluator, capped transcript, hard timeout:
     │                 continue | candidate_complete | blocked  (P18)
     │
     └─ [N calls]   adversarial panel, majority vote, only on candidate_complete
                       — audits the implementer's evidence, does not author its own  (P19)
```

Three properties to carry with it:

- **P20 · Anti-ratchet, structurally rather than by prompt.** Pass the prior round's findings into the
  current round and require each to be resolved; treat novel objections as a separate, lower-priority
  channel. A gate that can raise the bar between rounds does not terminate.
- **P28 · Cheapest-first as a stated house rule.** The same shape appears in at least four unrelated
  subsystems across the references (verification, memory consolidation, permission gates, benchmark
  tiering), which suggests convention rather than coincidence: *a gate sequence is ordered by cost
  ascending, and each stage's job is to make the next stage unnecessary.* Our T0–T3 edit ladder
  already follows it; making it a rule means the next ladder does too.
- **P49 · Policy-only guards.** The ledger *observes* and never decides; the guard *decides* and never
  observes. That is the same split as `PolicyEngine` versus `dispatch`, applied to verification, and
  it makes both halves testable in isolation.

**Sharpen §1.4 (loop guardrails)** with two things from the reference retry policies:

- **P39 · The retry table itself**, which contains two non-obvious entries: **429 gets *fewer*
  retries, not more** (*"rate-limit waits can be long and there is no point burning a long backoff
  just to be rate-limited again"*), and **413/image errors strip images and retry once, off-budget**.
  Plus a server hint channel (`x-should-retry: false`) letting a provider mark a failure non-retryable
  without a client change.
- **P25 · Key the taxonomy by clearing condition, not only by cause.** Grok Build's compaction
  suppression has five states distinguished by *what event would make retrying sensible*:
  self-heals next turn · needs the context budget to change · needs a successful call · needs
  re-auth (*not* a successful call, because waiting for one deadlocks when context is already over the
  window). That last row is a bug found in production, not in review. Suggestion: every degraded state
  in AETHER names its clearing condition as a required field.

**§2 — make the edit representation ablatable (P26).** A-013 fixes the primary mechanism as anchored
search/replace with anchor-sequence matching, which I still think is right. What the references add is
*method*: Grok Build implements **three** anchor schemes behind one trait (`ContentOnly` /
`ChunkFingerprint` / `CheckpointChain`), declares the metrics (read amplification, ambiguity rate),
names a starting favourite, and lets the harness decide. Claude Code's edit tool has a documented
three-valued result — exact → fuzzy-with-warning → error — matching Grok Build's
`Found | Ambiguous | NotFound`. Suggestion: keep A-013's choice, and design the edit port so a second
scheme is a substitution rather than a rewrite.

**§3 — add the ledger as a T-tier optimization.** With an evidence ledger, T3 can be *skipped* when
fresh evidence already covers the changed scope under the current tree digest. Hermes' scope rule is
the part that keeps it honest: **a narrow pass is never promoted to "repo green"**.

### 3.3 → [`rewrite_v300_contexto_memoria.md`](../../rationale/rewrite/rewrite_v300_contexto_memoria.md)

| # | Proposed addition | Where |
| :--- | :--- | :--- |
| **P24** | Prefire two-pass compaction with a prefix fingerprint and tool-boundary snapping; prefire outcome as a stable telemetry key | new §2.3 |
| **P50** | Explicit rule: any mechanism rewriting sent history is cache-hostile until measured; the read→write conversion enters its ablation | §1.6 |
| **P9** | Separate compaction *policy* from compaction *trigger*; note the intra- vs inter-compaction distinction we do not currently have | §2 |
| **P66** | Path-scoped instruction modules as a mechanism, with the claimed 40–50% always-on reduction as the hypothesis to test | §5.3 |
| **P67** | Rules vs skills as a structural split, with the membership test | §5.3 |
| **P45** | Per-artifact byte budgets enforced in CI, not merely "tracked" | §5.3 |
| **P75** | Hard caps on memory artifacts with **visible** truncation markers | §4 |
| **P27** | MMR diversity re-ranking using token-set Jaccard — no embeddings, ~20 lines, works on the FTS-only path | §3.1 |
| **P31/P68** | Tool Search / deferred schemas, as an early ablation arm rather than an M3 feature | §1.5 |
| **P69** | A declared ceiling on the always-on tool-schema share of the window | §1.6 |
| **P65** | Extend the judge-context rule to **gates and classifiers**, and set the noise floor at a representative trajectory length | §5.1 |

Two of these deserve their reasoning stated, because they change a priority.

**P68 — the Tool Search numbers change the calculus.** In the Grok Build teardown I graded deferred
tool schemas "B for MVP" on the argument that eight tools do not need it. The Claude Code corpus
reports Anthropic benchmarks: token overhead 55K → 8.7K (−85%), **and Opus 4 tool-selection accuracy
49% → 74% (+25 points)**, with a smaller +8.6 on Opus 4.5. Lazy loading is normally sold as cost; here
it *improved selection*, meaning the eager baseline was actively confusing the model — and the smaller
gain on the stronger model is exactly the shape of a scaffolding benefit, which implies it may matter
**more** on the weak models our Tier 0 ladder uses. Suggestion: not in the MVP, but an early ablation
arm, with the `ToolRegistry` designed so a search-and-load path is a substitution.

**P75 — visible truncation.** Claude Code's auto-memory caps `MEMORY.md` at 200 lines and 25 KB (line
truncation first, then byte truncation), the memory directory at 200 files, and **appends a warning
comment at the truncation point**. Silent truncation is worse than either keeping or dropping the
content, because the model reasons over a fragment as if it were whole.

**Note on §4 (memory) — three independent "dream" implementations.** Grok Build's `dream`, Hermes'
curator, and Claude Code's Auto Dream all gate cheapest-first, are single-flighted by a lock, and
restrict write scope to memory. Two are literally named "dream". Claude Code's four-phase
decomposition adds two rules worth having: **targeted grep** of transcripts rather than exhaustive
reads (*"look only for things you already suspect matter"*), and **converting relative dates to
absolute** during consolidation — which is the single most common form of memory rot in a corpus
written over weeks.

### 3.4 → [`rewrite_v300_measurement_strategy.md`](../../rationale/rewrite/rewrite_v300_measurement_strategy.md)

**P30 · Pin the tool contract in the run manifest.** §7's publication list holds model, effort, tool
budget, retry policy, max steps, suite id, pool, cost, noise floor and CI. It does not hold the **tool
contract version**. Given that lift is a paired delta, that omission is a live hole.

**P62 · Run the "less scaffolding, more model" thesis as a named ablation.** Claude Code's design
philosophy is Tier-1 documented and it is a direct challenge to a substantial part of our plan: no
intent classifier, no router, no RAG, **no DAG orchestrator**, no planner/executor split, eight tools,
a plain `while (tool_call)` loop — with the stated reason *"Claude 4+ is capable enough to handle
routing decisions."* And the sharpest single data point in the corpus: **Anthropic built semantic code
search with Voyage embeddings, benchmarked it internally, and removed it** in favour of ripgrep.

This is a falsifiable claim, and we are already positioned to test it nearly for free: A-024 puts a
four-node linear graph in M1a and memoization in M2. Suggestion: designate the
linear-graph-versus-plain-loop comparison as a first-class M1b/M2 ablation with a pre-registered
metric, so ADR-0018 and A-024 are confirmed or reversed by our own numbers. One extra arm in an
experiment we are running anyway, and it converts the largest architectural disagreement between us
and the market leader into a measurement.

Note the tier interaction, which cuts in our favour: scaffolding value appears to be inversely
proportional to model capability (the Tool Search gain shrank from +25 to +8.6 across one model
generation). Our Tier 0 ladder runs weak local models with no human in the loop, which is the regime
where scaffolding pays most. The right conclusion is probably not "build less" but **"design every
mechanism to be removable"**, which is what the ablation-flag discipline already gives us.

**P61 · Per-claim source tiering.** §1 already rules that third-party numbers are hypotheses, never
results — the strongest procedural rule in the document. The Claude Code corpus formalizes it into a
three-tier marker (official / verified reverse-engineering / community inference) attached to each
claim. Suggestion: adopt the markers in our own reference documents, and extend the principle to run
manifests, where a measured number and an estimated number should not look alike.

**P59 · For M5: benchmarks gate, a task-local metric drives.** Hermes' self-evolution plan states it
well — *"Benchmarks are GATES, not fitness functions… A variant that improves skill quality by 20% but
drops TBLite by 5% is REJECTED."* Using SWE-bench score as the meta-loop's *objective* invites
overfitting to the benchmark; using it as a *regression gate* with a task-local objective keeps both
honest.

**P64 · Session forking for ablations.** If the `TrajectoryStore` supports forking a run at a point
with shared history rather than full replay, comparing two prompt variants costs the tail instead of
the whole trajectory — and with prompt caching, the shared prefix is the part already paid for.

**P12 · One operational note.** SQLite WAL mode breaks on network filesystems (mmap'd `-shm`, POSIX
locks). Our `TrajectoryStore` is SQLite. Anyone running with an NFS-mounted home — common in
university and enterprise environments — would hit it. A filesystem probe selecting journal mode is
low effort, low probability, high embarrassment.

### 3.5 → [`rewrite_v300_autonomia_agi.md`](../../rationale/rewrite/rewrite_v300_autonomia_agi.md)

| # | Proposed addition | Where |
| :--- | :--- | :--- |
| **P17** | Fail-closed drive state on resume: unknown or forward-version status restores as *paused*, never *active* | §1 |
| **P23** | Per-role private scratch (`0700`) under a per-run root, with a `{SCRATCH}` placeholder resolving per reader | §1, §7 |
| **P52** | Self-modification is provenance-scoped (only artifacts the loop authored), never destructive (archive, not delete), and human-pinnable (a pinned artifact is exempt from every automatic transition) | §2.1 |
| **P53** | A human-editable index over accumulated state: stable per-node ids for skills and memories, with edit and archive | §2.1 |
| **P54** | Sub-agent budgets are independent; the manifest records the tree total and a separate global ceiling exists | §7.1 |
| **P74** | The four-phase consolidation structure, with targeted grep and relative→absolute date conversion | §2.1 |
| **P60** | The meta-loop's constraint set as hard gates: test suite 100%, size ceiling, growth ceiling, structural validity, cache compatibility, PR-not-commit | §5 |
| **P59** | Objective metric ≠ acceptance metric | §5 |

**On P23 — the scratch rules are oddly specific, which usually means each is a scar.** Never shared
`/tmp` (*"skeptics and concurrent goals collide there"*); classifier artifact names are predictable
from a log-visible id, so a world-writable directory lets a local attacker pre-plant a symlink and
redirect the harness's writes; and — the one we would otherwise discover the hard way — **never point
`HOME`, `CARGO_HOME`, `RUSTUP_HOME`, a package-manager home, a virtualenv or a cache at scratch**,
because the scratch dir is reaped when the run ends and leaves a broken environment behind.

**On §5 — the self-evolution reference's methodology is a negative example worth citing.** Hermes'
DSPy+GEPA loop has a sound architecture (trace-based reflective mutation, hard constraint gates,
train/val/holdout splits, benchmarks as gates) and an evaluation layer with the same gap our own
predecessor had: **the metric passed to the optimizer is the same function used to score the holdout**,
and that function is keyword overlap; the default holdout is ~5 examples; there is no noise floor and
no significance test — the result is reported as `evolved − baseline` with a green arrow; and if the
baseline already violates a constraint the run prints *"proceeding anyway"* and continues.

None of that makes the architecture wrong. It means M5 should reuse the architecture and refuse the
evaluation — which is exactly the doctrine in §3.4 applied one level up, and being able to point at a
shipped competitor meta-loop as the counterexample makes the argument concrete rather than pedantic.

### 3.6 → [`rewrite_v300_seguranca_sandbox.md`](../../rationale/rewrite/rewrite_v300_seguranca_sandbox.md)

| # | Proposed addition | Where |
| :--- | :--- | :--- |
| **P36** | **Auto-denial limits** — bounded consecutive and total denials, with explicit anti-circumvention guidance in the denial message | §1.4 |
| **P35** | `ask` gains provenance: rule-matched vs **fail-closed** ("could not decide"), ranked so a rule match anywhere binds | §1.4 |
| **P37** | Trust and policy stores fail closed when their root cannot be located — trust nothing, never trust the working directory | §1.5 |
| **P57** | Two refinements to the lifecycle guard already there: enforce at **creation** time as well as execution, and make the pattern **command-shaped** rather than keyword-shaped | §3.4 |
| **P33** | Sub-agent capability mode derived from a declared property of the tool, not enumerated per role | §6 |
| **P77** | Hook payload as a wire contract: common fields on every event plus event-specific fields, block-by-exit-code, modify-by-returned-JSON | §1.5 |

**P36 is the one I would prioritize.** Grok Build caps auto-denials at 3 consecutive / 20 total and
tells the model *"take a safer approach that stays within what the user asked for; do not retry this
exact action or attempt to work around the denial."* Our design has no bound on this at all. An
autonomous agent that spends its budget grinding against a permission boundary — or worse, creatively
routing around it — is a real failure mode that the perimeter model does not address, because nothing
is being violated.

**P35** is the general form: whatever analysis we do, *"I could not decide"* must be a distinct,
ranked, escalating outcome and never silently fold into "allow".

**On the perimeter debate — no change proposed.** Grok Build runs 20,000+ lines of shell decomposition
*plus* an OS sandbox; Hermes runs command guards plus approval; Claude Code runs an OS sandbox with
dangerous-pattern detection that is substantially *the model's judgement* rather than a rule table
(its own documentation says so). ADR-0006 chose the container perimeter and I still read that as
correct for our threat model — a container, not the user's laptop with the user's credentials. P35,
P36 and P37 are portable regardless of which side that debate lands on and should not wait on it.

### 3.7 → [`rewrite_v300_roadmap_sprints.md`](../../rationale/rewrite/rewrite_v300_roadmap_sprints.md)

**M0 additions** (all near-free now, breaking later): `RunOutcome` + `PauseKind` (P3) · `replayed`
flag (P4) · tool `contract_version` + registry (P30) · `RunProfile` type (P46) · composite checkpoint
type decision (P16) · one token estimator (P5) · stable wire strings on telemetry enums (P41) ·
checkpoint store layout decision (P56) · **a CI ceiling on single-module line count** — both Grok
Build (372k-line crate) and Hermes (26.8k-line file) arrived at unfactored cores despite strong
discipline, which suggests a mechanical limit rather than an enforced one; our `docs_budget.py`
ratchet is the existing precedent.

**M1a additions:** `reserve/commit/release` on the governor (P2) · task-typed turn caps + terminal
`MaxTurnsReached` (P63) · instrument worktree creation time (P1 — decide only to *measure*) · hard
deadlines on blocking reads (P58).

**M1b additions:** the scaffolding-thesis ablation arm (P62) · tool contract version in the manifest
(P30) · noise floor established at a representative trajectory length (P65).

**M2 additions:** the completion cascade (P18/P19/P20/P21/P48) · prefire compaction (P24) · MMR
re-rank (P27) · path-scoped instruction modules (P66/P67) · Tool Search ablation arm (P68) ·
auto-denial limits (P36).

**M3 additions:** fail-closed resume (P17) · per-role scratch (P23) · shared checkpoint store (P56) ·
sidecar recovery (P40) · human-editable state index (P53).

**M5 additions:** objective ≠ acceptance metric (P59) · the constraint set as hard gates (P60).

**One new risk row:** *"Verification gate ratchets and the loop never terminates"* — mitigated by P20,
and it is a T5-blocking failure rather than a quality issue.

### 3.8 → [`rewrite_v300_decisoes_runtime.md`](../../rationale/rewrite/rewrite_v300_decisoes_runtime.md)

Two corroborations, no change proposed.

**On IP protection.** Grok Build ships a native binary and the only thing it obfuscates is the prompt
text — XOR-encrypted at build time by a Python script, trivially reversible, and everyone involved
knows it. A well-funded competitor shipping compiled code concluded that prompts were the only asset
worth a speed bump, and that a speed bump was enough. That is consistent with the position already
recorded here.

**On the monoglot decision.** The one place Rust clearly earns its keep across all the references is
the **incremental tree-sitter index over a large repository** (`xai-codebase-graph`: rayon-parallel
parsing, mmap'd zero-copy reads, a disk cache surviving restart, an actor answering queries in place
without cloning the index). That is exactly the shape I3 exists for, and it is exactly where
RT-1/RT-3 already point. Nothing else in three teardowns argues for a second toolchain.

### 3.9 → [`rewrite_v300_uiux_tui.md`](../../rationale/rewrite/rewrite_v300_uiux_tui.md)

Small, and it follows from P3: the TUI should render **why** a run is paused, not merely *that* it is.
"Waiting on you", "backing off", "no progress", "infrastructure error", "blocked — needs a decision"
are five different things an operator watching an 8-hour run needs to distinguish at a glance. Grok
Build's UI carries the pause reason for exactly this purpose, and the mechanism is already proposed
(P3) — this is just the consumer.

Also **P34**: background work that completes between turns is invisible until the agent thinks to
poll. Hermes attaches completion notices to the *next tool result* rather than as a separate message,
which keeps the message structure and the cache prefix undisturbed.

### 3.10 → [`rewrite_v300_reference_teardowns.md`](../../rationale/rewrite/rewrite_v300_reference_teardowns.md)

Three provenance items that belong in the study-policy section:

1. **`src/claude_refs/claude-code-analysis` is a reverse-engineering of a de-obfuscated bundle** — the
   exact artifact class **A-007(c)** defers — and it is dated **2025-03-31** while the companion guide
   tracks v3.41.1 (Jul 2026). The teardown recommends treating it as *shape only*. That is a policy
   call under A-007 and it should be made explicitly rather than implicitly by whoever cites it next.
2. **Grok Build carries in-tree ports of `openai/codex` and `sst/opencode`** tool implementations
   under Apache §4(b) change notices. `crates/codegen/xai-grok-tools/src/implementations/opencode/`
   and `codex/` are third-party code under their original licences and are outside what we study.
3. **DSPy and GEPA are MIT** and could be used directly if M5 chooses to; **Darwinian Evolver is
   AGPL v3**, and Hermes' own handling — external CLI only, never imported — is the pattern to follow
   if it is ever considered.

### 3.11 → [`rewrite_v300_decisoes_adr.md`](../../rationale/rewrite/rewrite_v300_decisoes_adr.md)

Candidate new records, if the review adopts the corresponding items:

| Proposed | Subject | Sources |
| :--- | :--- | :--- |
| **A-026** | Typed run outcome and pause taxonomy | P3 |
| **A-027** | Effect replay provenance and idempotency classification | P4 |
| **A-028** | Tool contract versioning; the version is a manifest field | P30 |
| **A-029** | The completion verification cascade, and anti-ratchet as a gate property | P18–P21, P48 |
| **A-030** | Budget reservation under fan-out; tree-total accounting | P2, P54, P63 |
| **A-031** | `RunProfile`: rules vs skills, path scoping, disclosed staleness | P46, P47, P66, P67 |
| **A-032** | Auto-denial limits and fail-closed authorization provenance | P35, P36, P37 |
| **A-033** | Prefire compaction; rewriting sent history is cache-hostile | P24, P50 |

**Amendments to existing records** rather than new ones: A-013 (edit representation as an ablatable
seam, P26) · A-019 (capability mode derived from a tool property, P33; tree-total budget, P54) ·
A-022 (retry table, P39; clearing-condition axis, P25) · A-006/measurement §7 (tool contract version
in the manifest, P30).

Two records I would **not** touch: **A-024** (the DAG sequencing) — P62 proposes measuring it rather
than re-arguing it; and **A-007** (the study policy) — §3.10 item 1 asks for a scope ruling under it,
not a change to it.

---

## 4. What I propose we decline, and why

| # | Item | Reason |
| :--- | :--- | :--- |
| **P6** | Workflow-as-script instead of a DAG | Contradicts A-024. The reversal point at M2 is the right moment, with evidence. P62 is the better version of this question |
| **P11** | Process-level OS sandbox with per-subprocess network blocking | ADR-0006 stands. A second security mechanism is a second thing to get right. Recorded as an option for a future local-development profile |
| **P13** | Pure-data types package with zero runtime deps | We already have the property via I1 and import-linter |
| **P22** | The strategist (structural-restructure meta-agent) | Fires rarely, costs a full investigative sub-agent run. Its two *constraints* are worth writing down now even if we never build it: change the HOW never the WHAT, and investigate raw traces rather than a digest |
| **P72** | Peer-to-peer agent mailbox | Beyond A-019's depth-1 topology. Revisit at M3+ if collaborative decomposition is built at all; the safe property is that messages are shared and context is not |
| **P73** | Git-based task claiming via lock files | Same window as P72. Worth comparing against a database-backed queue when we get there |
| **P78** | Build-time feature elimination | No Python equivalent of Bun's `feature()`. Only relevant if we ship a distributed binary, which the runtime decisions doc already defers |
| **P10** | Hunk tracking with agent/external attribution | Growth-tier, answering a problem we have not hit. It becomes necessary the moment a human can edit a file mid-run in the TUI |

---

## 5. Suggested sequencing

Ordered so that cheap-now-expensive-later comes first, since deferring those is itself a decision.

| # | Decide | Why now |
| :--- | :--- | :--- |
| 1 | **P3 · P4 · P5 · P30 · P41 · P16 · P46 · P56** | All M0 domain-type or layout decisions. Near-free before the schema freeze; breaking changes after. P30 additionally cannot be retrofitted onto historical measurements |
| 2 | **P2 · P54 · P63 · P55** | Budget correctness. Cheap while the governor is three functions; a real race under the fan-out M4 depends on |
| 3 | **P20 · P48** | Anti-ratchet is a termination property, not a quality one. The ledger is close to free and makes both the gate and any future panel cheaper |
| 4 | **P62** | One extra arm in an M1b/M2 ablation we are already running. Settles the DAG question with our numbers instead of taste |
| 5 | **P36 · P35 · P37 · P58** | Small, self-contained, and each closes a named autonomy failure mode ahead of T5 |
| 6 | **P18 · P19 · P21 · P24 · P27 · P66 · P67 · P68** | M2 capability work, each with its ablation |
| 7 | **P17 · P23 · P40 · P53** | M3, with hibernation and the private suite |
| 8 | **P59 · P60** | M5. Worth recording now so the meta-loop is not designed against the metric it optimizes |
| 9 | **P12** | One line in the operational notes; costs nothing to record |

---

## 6. Open questions for the review

1. **Where does the verification evidence ledger live** — a new port, a `TrajectoryStore` table, or an
   `Evaluator` internal? It is a small mechanism with a large blast radius on the port catalog, and
   A-010's entry rule (a port arrives with its first adapter) argues against making it a port purely
   on principle.
2. **Do we build all three completion tiers, or two?** §2.1 argues they compose at three price points.
   Three verification mechanisms is also three places for a bug to hide the truth. My reading is that
   the ledger is nearly free and makes the other two better — but that is an argument, not a
   measurement.
3. **Is `claude-code-analysis` usable under A-007 at all?** §3.10. A policy call, not an engineering one.
4. **What is M5's acceptance metric, and how does it differ from its objective?** §3.5. Naming both is
   a real design task and it gates M5.
5. **Does ADR-0014's recall@10 trigger still sit at the right threshold**, given that two of three
   references run symbolic-only and one of them *removed* embeddings after benchmarking?
6. **Do we occupy the role-based model-selection gap?** Claude Code's Agent Teams runs one model for
   every agent and the community is asking for lead-Opus / worker-Sonnet / test-Haiku; Grok Build has
   a per-skeptic model pool. Our `ModelProvider` port makes this natural, it costs little, and the
   market leader has not shipped it.

---

**Cross-references:**
[`rewrite_v300_grokbuild_proposals.md`](./rewrite_v300_grokbuild_proposals.md) ·
[`rewrite_v300_grokbuild_teardown.md`](./rewrite_v300_grokbuild_teardown.md) ·
[`rewrite_v300_hermes_teardown.md`](./rewrite_v300_hermes_teardown.md) ·
[`rewrite_v300_claudecode_teardown.md`](./rewrite_v300_claudecode_teardown.md) ·
[rewrite plan index](../../rationale/rewrite/README.md)
