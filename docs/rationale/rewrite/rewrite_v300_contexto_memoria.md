---
status: rationale
retrieval: excluded
updated: 2026-08-05
---

# AETHER v3.0.0 — Context Window, Cache Engineering, Retrieval and Memory

> [!NOTE]
> **LLM / AI AGENT NOTICE**: This file is Phase-0 rationale for the AETHER rewrite. It is not
> binding and defines no contract. Contracts live in `src/`. Read it for *why*, not *what*.

Answers RFP [§4-C](../reviews/review_project_rewrite_v300.md).

---

## 0. The two theses

**Retrieval precision over context stuffing.** A 1M-token window is a capability, not a strategy.
Filling it costs money per turn, degrades attention on the middle of the context, and destroys cache
economics. `planning_future_sprints.md` §2 records the number that settles the argument: **Agentless
resolves ~45% of SWE-bench Verified with no agent loop at all**, at roughly a tenth of the cost, and
AutoCodeRover ~52%. Their entire edge is picking the right five files. An agent that edits the wrong
file perfectly scores zero.

**Cache stability is an architectural property, not an optimization.** Prompt caching is a **prefix
match**: any byte change anywhere in the prefix invalidates everything after it. That single fact
determines the layout of the entire prompt, where dynamic data may live, and what the run loop is
allowed to do mid-run. It cannot be retrofitted onto a prompt assembled the convenient way.

---

## 1. Cache engineering

### 1.1 The mechanics that constrain the design

Render order is **`tools` → `system` → `messages`**. Consequences, each of which becomes a rule:

| Mechanic | Consequence for AETHER |
| :--- | :--- |
| Prefix match — one byte invalidates everything after it | No timestamp, run id, UUID, or per-task string may appear before the last breakpoint |
| Tools render at position 0 | **Changing the tool set mid-run invalidates the entire cache.** Tool schemas must be serialized deterministically (sorted, stable key order) |
| Max **4** `cache_control` breakpoints per request | Breakpoint placement is a budget to be spent deliberately, not a marker to sprinkle |
| Minimum cacheable prefix is **model-dependent and not monotonic** — 512 tokens on Opus 5, 1024 on Opus 4.8 / Sonnet 5 / Sonnet 4.6, 2048 on Opus 4.7, 4096 on Opus 4.6 / Haiku 4.5 | A short prefix silently does not cache — no error, just `cache_creation_input_tokens: 0`. The minimum is a **per-model property in config**, not a constant |
| Write costs 1.25× base input (5-min TTL) or 2× (1-hour TTL); read costs ~0.1× | Break-even is 2 requests at 5-min TTL, 3 at 1-hour. The cost model must carry both multipliers |
| A cache entry is readable only once the first response **begins streaming** | See §1.4 — this is the Best-of-N trap |
| Each breakpoint walks back at most **20 content blocks** to find a prior entry | See §1.3 — this is the agentic-loop trap |
| Caches are model-scoped | A model swap mid-run is a full cache rebuild. Role→tier binding is resolved at composition, frozen for the run |

### 1.2 The prefix layout

Five layers, ordered by mutation frequency, with three of the four breakpoints spent:

```
┌─ tools               (frozen for the run; deterministic serialization)  ── breakpoint 1
├─ system prompt       (frozen; no dates, no run ids, no task text)       ── breakpoint 2
├─ memory / skills     (resolved at composition; frozen for the run)
├─ static repo context (repo map, retrieval seed — construction-time only) ── breakpoint 3
└─ dynamic turns       (append-only; exchanges, tool results, gate feedback) ── breakpoint 4, rolling
```

SAGIHA already has the shape — an 8-layer assembler with a `stable_prefix_digest` recorded on every
`TrajectoryStep`, and a retrieval seed deliberately construction-time-only so it can never invalidate
the prefix mid-run. **What it does not have is any `cache_control` emission at all.** Grep finds one
hit across the tree: `cache_read_tokens=_tokens(details, "cached_tokens")` at
`adapters/model/openai.py:326`, which only reads back what the provider cached automatically. Caching
in SAGIHA is positional and implicit; in AETHER it is explicit and measured.

Hermes' `agent/prompt_caching.py` is the closest published reference: 4 breakpoints — static system
prefix, end of system prompt, and the **last 2 non-system messages** — falling back to one system
breakpoint plus the last 3 messages when no static prefix exists, all at a uniform TTL, implemented as
pure functions with no agent dependency. AETHER adopts the same shape and the same purity constraint:
breakpoint placement is a function of the assembled prompt, not a method on the run loop.

### 1.3 The 20-block lookback — the trap specific to coding agents

A breakpoint searches backward at most **20 content blocks** for a prior cache entry. A coding agent
turn routinely appends more than 20 blocks — every `tool_use` and its `tool_result` is a block, and a
step with six parallel tool calls contributes twelve. When a turn overruns the window, the next
request's breakpoint finds nothing and **silently misses**; the failure mode is a cost spike with no
error.

**Rule:** the assembler places an intermediate breakpoint at least every ~15 blocks within a long
turn. Because the total breakpoint budget is 4, this competes directly with the static layers — the
allocation is a config-level policy, and cache hit rate is the measurement that arbitrates it.

### 1.4 Concurrent requests — the Best-of-N trap

A cache entry becomes readable only after the first response **begins streaming**. N parallel requests
sharing a prefix therefore all pay full write price; none can read what the others are still writing.

This lands directly on AETHER's System-2 design: Best-of-N across isolated worktrees is *by
construction* N concurrent requests over an identical prefix. Naively fanned out, the mechanism most
expected to improve resolve rate also multiplies prefix cost by N.

**Rule:** BoN fan-out sends one request, awaits its **first streamed token** (not its completion),
then fires the remaining N−1. This costs one round-trip of latency and converts N−1 cache writes into
N−1 cache reads — roughly a 12× cost difference on the shared prefix. It also makes streaming a hard
requirement rather than a UX nicety, which resolves the `stream()` gap noted in
[the audit §3.2](./rewrite_v300_auditoria_sagiha.md).

### 1.5 Mutating state without invalidating the prefix

Two mechanisms exist for changing what the model knows mid-run without paying a full rebuild:

- **Mid-conversation system messages.** Appending `{"role": "system", ...}` to `messages[]` — rather
  than editing the top-level `system` field — carries operator authority while leaving the cached
  history intact. Available on Opus 5, Opus 4.8, Fable 5 and Mythos 5; **not** on Sonnet 5, which
  returns a 400. It is also the injection-safe channel: text inside a user turn can be forged by
  anything that writes to user-visible input, a `role: "system"` message cannot. This is the correct
  transport for anything the harness learns mid-run — a mode change, an approval outcome, a
  budget state. Model support is a **capability flag on the provider adapter**, with a
  `<system-reminder>`-in-user-turn fallback where unsupported.
- **Mid-conversation tool changes** (beta, Opus 5 onward). `tool_addition` / `tool_removal` blocks on
  a system message surface tools declared up front with `defer_loading`, changing the tool set without
  the position-0 invalidation. This is what makes a *dynamic* tool registry compatible with caching at
  all. Adopt behind a capability flag; the static registry remains the default.

**What is safe to vary per request:** `tool_choice`, thinking enable/disable, and images invalidate
only the messages tier — tools and system survive. Do not over-engineer around these.

### 1.6 Cache economics as a first-class metric

`usage.input_tokens` is the **uncached remainder only**. Total prompt size is
`input_tokens + cache_creation_input_tokens + cache_read_input_tokens` — a harness that logs only
`input_tokens` will report a 4K prompt for an hour-long run and quietly mislead its own cost model.

The cost model therefore carries three rates, not one: full input, write (1.25× or 2×), read (~0.1×).
**Cache hit rate is a tracked metric with an alerting threshold**, and `cache_read_input_tokens`
staying at zero across repeated same-prefix requests is a *test failure*, not a performance note — it
means a silent invalidator is in the prefix. The regression suite asserts a floor on hit rate over a
fixed replay, which turns a whole class of invisible cost regressions into red CI.

**Pre-warming** (`max_tokens: 0` against the stable prefix) is worth it only when first-request
latency is user-visible and there is a quiet moment before traffic. For benchmark runs — continuous
traffic, no human waiting — it is a pure extra write. Documented so nobody adds it reflexively.

---

## 2. Compaction

Port SAGIHA's `ExchangeCompactor` (235 LOC) with its granularity rule intact: compaction operates on
**whole exchanges**, never inside one. A truncation that lands between a `tool_use` and its
`tool_result` produces a transcript the provider rejects on the next request.

| Property | Decision |
| :--- | :--- |
| Trigger | Context-utilization threshold, not overflow. OpenCode's auto-compact-at-threshold shape |
| Granularity | Whole exchange; token-budgeted; `keep_last_tokens` preserved verbatim |
| Head and tail | Both preserved — the head is the cached prefix, the tail is what the model is working on |
| Where the summary goes | Appended as a turn, never spliced into the frozen prefix |
| Observability | `CompactionApplied` event with before/after exchange and tail-token counts (SAGIHA emits this; keep it) |

### 2.1 The summary is an instruction source — treat it as one

**A compaction summary re-enters the context as text the model reads, and it competes with the live
task for authority.** A summary carrying a `## Next Steps` or `## Remaining Work` heading gets read as
*current* directives: the agent starts "wrapping up" work already finished, or revives a historical
to-do as live. The compactor silently becomes a second instruction channel.

This is not speculative — it is the design that `agent/context_compressor.py` in
`src/hermes_agent` converged on after hitting the failure, and AETHER adopts it:

| Rule | Mechanism |
| :--- | :--- |
| **No forward-looking headings in a summary** | Rename to historical: `## Historical Task Snapshot`, `## Historical In-Progress State`, `## Historical Pending User Asks`, `## Historical Remaining Work` |
| **Mark the block as reference, not instruction** | Wrap in an explicit `[CONTEXT COMPACTION — REFERENCE ONLY]` envelope |
| **Ship a precedence rule inside the summary** | Where the historical block diverges from the latest message, *the latest message wins* — discard the historical section, do not wrap up |
| **Filter-safe summarizer preamble** | The turns being summarized are framed to the summarizer as **source material to preserve**, never as instructions to follow |
| **Redact secrets during summarization** | By explicit instruction in the summarizer prompt, not by hoping they do not appear |

**The compaction boundary is a trust boundary.** The fourth row is the one most designs miss: the
summarizer is a model reading a transcript that may contain repository content, tool output, and web
results — all `trusted=False` by [our own provenance rules](./rewrite_v300_seguranca_sandbox.md). An
injection that survives into the summary is *laundered into the frozen part of the context*, where it
looks like our own text. The summarizer preamble is the control, and it belongs in the TaintGate's
threat model rather than in the compactor's.

**One recorded regression, carried as a warning:** the same codebase records that the
`REFERENCE ONLY` framing once bled into general tool-use suppression — the model read it as "do not
act" and stopped calling tools. Strengthening the envelope has a cost, and the wording is an ablation
parameter like any other, not a constant to copy blindly.

### 2.2 Mechanics adopted with the strategy

| Mechanic | Rationale |
| :--- | :--- |
| **Tool-output pruning as a cheap pre-pass**, before the summarizer runs | Do not pay a model to read output that was going to be discarded |
| **Token-budget tail protection**, not a fixed message count | "Keep the last N" retains twenty trivial turns or truncates two large ones |
| **Scaled summary budget**, proportional to the compressed region | A fixed summary size over-summarizes small regions and under-summarizes large ones |
| **Iterative summary updates** across successive compactions | The direct counter to §5.2's "repeated compression loses nuance": each compaction updates the prior summary rather than re-summarizing its own output |
| **Auxiliary (cheap) model for summarization** | Summarization is not the task; it should not be priced like the task |
| **Startup feasibility probe on the aux model** | Check the aux context window against the compaction threshold, auto-lower the threshold where possible, hard-reject an aux that is too small. A summarizer that cannot fit what it must summarize fails at the worst possible moment |
| **Strip historical media** | Images in compacted history are pure cost |
| **Preflight and idle compaction** | Compact *before* the call that would overflow, and opportunistically while idle — not as an overflow handler |

**Server-side compaction is available** (beta, `compact-2026-01-12`) and is deliberately **not**
adopted in Phase 1. Reason: it moves a mechanism we need to ablate onto the provider's side of the
port, where we can neither measure nor vary it. Revisit when our own compactor has a measured
baseline to compare against — that is the only condition under which the comparison means anything.

Related and distinct: **context editing** (`clear_tool_uses_20250919`, `clear_thinking_20251015`)
*clears* stale blocks rather than summarizing them. Cheaper and lossier. Worth an ablation against
compaction on long agentic runs; the two are complementary, not alternatives.

---

## 3. Retrieval and repo mapping

The highest-leverage subsystem in the document, per §0.

### 3.1 The tiers

| Tier | Mechanism | Status |
| :--- | :--- | :--- |
| **Structural** | Tree-sitter AST skeleton: signatures, class and function names, imports — never whole files at task start | `core` |
| **Lexical** | FTS5 / BM25 over AST-bounded chunks, disk-backed | `core` — SAGIHA's `adapters/indexer/` ports directly |
| **Graph** | Imports, calls, co-change edges; `impacted_by`, `callers_of` | `core` — `code_graph/treesitter.py` ports directly |
| **Dense** | Embedding tier over the lexical tier | `research` — gated on ADR-0014's trigger: recall@10 misses traced to vocabulary mismatch. Not a date |

The ordering is deliberate: each tier is added only when the tier below it demonstrably fails on
labeled queries. Dense retrieval added before that evidence exists is a component whose value cannot
be measured.

### 3.2 Retrieval-before-edit

Localization is a **pipeline stage**, not a tool the agent may forget to call:

1. Repo map (skeletons) enters the static-context layer at construction time.
2. Symbol search and graph expansion produce a candidate file set.
3. Only those files are read in full.
4. Edits are confined to the localized set unless the agent explicitly widens it, which is an event.

SAGIHA ships `retrieval.enabled = false` by default — not out of doubt about the mechanism, but
because [the noise floor was never produced](./rewrite_v300_measurement_strategy.md) and no
measurement ever justified turning it on. AETHER inherits the mechanism and the honesty: it ships on
only when an ablation says so.

**Performance targets** (PLANNING.md T7 / §7), which the indexer design must respect: cold index of a
≥1M-LOC repository under 10 min, index memory under 500 MB (forcing disk-backed structures, not
in-memory graphs), incremental single-file re-index under 200 ms. That last number is what keeps the
index usable by an agent that is actively editing.

### 3.3 Documentation retrieval

The same pipeline over prose, honoring `retrieval: excluded` frontmatter. This repository's own
convention exists because retrieving superseded reasoning as though it were current is how an agent
acquires contradictions — every file under `docs/rationale/`, including this one, is excluded for
exactly that reason.

---

## 4. Memory

| Tier | Definition | Tier |
| :--- | :--- | :--- |
| **Short-term** | Loop-local. The compacted transcript. **Not a port** — `next_gen_architecture_specs.md` §1.2 deleted `ShortTermMemory` as a port on the grounds that loop-local state is not a boundary | core |
| **Long-term** | Bi-temporal episodic store: FTS5 over past sessions with LLM re-summarization on recall, valid-time and transaction-time separated so a superseded memory is invalidated rather than deleted | growth |
| **Knowledge net** | Linked notes with backlinks over the episodic store | growth |

Hermes' `hermes_state_search.py` (2,229 LOC) is the reference implementation for the long-term tier.
SAGIHA's `InMemoryMemory` (61 LOC, in-process) is not memory in any durable sense and does not carry
over.

**The bi-temporal requirement is the non-obvious part.** A coding agent's memories go stale in a
specific way: "the auth module lives in `src/auth/`" was true when written and is false after a
refactor. Deleting it loses the record that the belief was held; keeping it un-timestamped poisons
future recall. Two time axes — when the fact was true, and when we recorded it — let recall filter to
currently-valid memories while the audit trail survives.

**Never store credentials in memory.** Memories are replayed verbatim into future contexts; a secret
written once is re-injected into every later session that reads the store.

---

## 5. The degradation curve — field evidence, and what it constrains

Everything above assumes lean context is worth engineering for. This section is the evidence, drawn from
the community field guide in `src/claude_refs/claude-code-ultimate-guide`.

**These are other people's numbers.** They are practitioner estimates and community observations, not
our measurements, and several carry explicit confidence caveats in the source. They enter this
document as **design constraints and hypotheses to re-measure**, never as results — see
[measurement strategy §1](./rewrite_v300_measurement_strategy.md).

### 5.1 Context rot is structural

Transformers attend to all tokens pairwise, so attention relationships grow as **n², not n**. Double
the context and you quadruple the relationships the model must weigh; attention becomes diffuse and
mid-window positions receive diminishing effective weight.

**This is a property of the architecture, not a defect future models remove.** It is the mechanism
behind §0's thesis, and it is why "use the 1M window" is not an answer: a larger window that
accumulates tool-output noise and stale turns is not more capable, only more expensive and slower.

Two refinements worth carrying:

- Needle-in-a-haystack benchmarks measure *lexical* retrieval. Once query and target stop sharing
  obvious vocabulary, degradation with length is worse than NIAH numbers suggest.
- **The degradation hits monitor and classifier models too, not just generation.** One 2026 data
  point: Opus 4.6 used as a trajectory monitor dropped from 98.6% to 88% recall once 800K tokens of
  *benign* prior actions were prepended. This lands directly on Best-of-N: our judge is a model
  reading long candidate transcripts, and it degrades the same way the generator does. **The judge
  gets its own context budget and its own hygiene**, not the generator's leftovers.

### 5.2 Two thresholds, and why we must measure our own

| Figure | Reported | Use |
| :--- | :--- | :--- |
| **MECW** — effective vs. advertised window | ~92% of the advertised limit before measurable degradation | Plan against the effective number, not the sticker |
| **Sharp quality drop** | A **non-linear** drop around **~70% of context budget used** — abrupt, not a smooth decline. Reported independently by multiple practitioners at one 2026 event | The compaction trigger is set *below* the cliff, not at overflow |
| Observed auto-compaction triggers in shipped tools | 75% · 92% · 95% · "1–5% remaining", depending on surface | **The spread is the finding.** No single number is authoritative — ours is an ablation parameter |
| Session degradation | 15–25 turns; 80–100K tokens accumulated | Bounds on a single run before a checkpoint or reset earns its cost |

The third row is the one that matters procedurally. Four credible sources report four different
thresholds for the same mechanism, which means **copying any one of them is guessing with extra
steps**. AETHER's compaction trigger ships as a config value with a default near the reported cliff
and is settled by ablation.

Compaction also degrades what it preserves: repeated compression cycles lose nuance and break
references. That is an argument for compacting *less often but earlier* — one well-timed compaction
beats three late ones.

### 5.3 The instruction ceiling — a budget on our own prompt

Beyond roughly **150 distinct rules**, models begin selectively ignoring some of them. The mechanism
is attention diffusion: high-salience rules (recent, strongly worded, placed early) crowd out
lower-salience ones. Reported adherence against instruction-file size:

| Lines of always-on instruction | Estimated adherence |
| ---: | ---: |
| 1–100 | ~95% |
| 100–200 | ~88% |
| 200–400 | ~75% |
| 400–600 | ~60% |
| 600+ | ~45% and falling |

**This applies to AETHER's own frozen prefix**, not just to user-authored config. The system prompt,
the tool descriptions, and the skills corpus all live in layers 1–3 — the cached, always-on part —
and every one of them competes for the same attention budget. Three consequences:

1. **The frozen prefix carries a rule budget**, tracked like the token budget. Rule quality beats rule
   quantity; twenty specific actionable rules outperform two hundred aspirational ones.
2. **Skills must load progressively** — description always-on, body on demand. An agent-authored skill
   corpus that grows monotonically ([autonomy §2](./rewrite_v300_autonomia_agi.md)) will otherwise
   silently degrade adherence to everything else. This is a second, independent reason for the skill
   acceptance gate.
3. **Path-scoped and role-scoped instructions** beat one global rule set, because they keep only
   relevant rules in context — which is the same just-in-time principle as §3, applied to instructions
   rather than to code.

### 5.4 Chain-of-thought is not free in long runs

Extended reasoning generates tokens, tokens extend context, and context accelerates rot for every
subsequent step. On runs spanning 20+ tool calls the effect is measurable. The practical rule:
reasoning depth is a per-step decision, and in long agentic runs **compressed intermediate output
beats extended reasoning traces**. Cost control is `effort`, not disabling thinking — see
[security §3.3](./rewrite_v300_seguranca_sandbox.md) for why disabling thinking has its own failure
modes.

### 5.5 Retrieval as the answer, restated with the mechanism

The field guide frames the same split §3 arrives at: **pre-loading** (retrieve everything potentially
relevant up front) versus **just-in-time retrieval** (retrieve exactly what the current step needs).
Pre-loading works when requirements are known and stable; JIT is harder to build and better at scale.

AETHER is JIT by construction — the repo map is pre-loaded because it is small and always relevant,
and file contents arrive through search and graph expansion only when a step touches them. §5.1 is
why: pre-loading trades a fixed, growing attention cost for a saving that retrieval already provides.

---

## 5b. Revision-A amendments from the competitor and literature review

Added after the four teardowns in [`docs/competitors_research/tech_lead_A/`](../../competitors_research/tech_lead_A/rewrite_v300_synthesis_amendments.md).
Each item is a proposal with a stated cost and a phase, not a decision.

### 5b.1 Exchange parity is a wire invariant, not a compaction preference

§2 already states that compaction operates on whole exchanges. The amendment is to promote that from a
*compactor property* to a **system-wide invariant with a name**, because at least four subsystems can
violate it independently:

> **Parity.** The transcript is always a well-formed alternation
> `user → assistant → tool_use → tool_result`. No mechanism may leave a `tool_use` without its
> matching `tool_result`, and no truncation, compaction, rewind, fork or halt may split that pair.

Producers that can break it: the compactor (splitting mid-exchange), the repair loop (halting after a
`tool_use` — already handled by the synthetic-error `ToolResult` rule in
[edit mechanism §1.2](./rewrite_v300_mecanismo_edicao.md)), the rewind/checkpoint path, and any future
context-editing pass. Grok Build enforces it in its two-pass split by snapping the split index to tool
boundaries; the failure it prevents is a provider-level protocol error on the *next* request, which
surfaces far from its cause.

**Suggested enforcement:** a single `assert_parity(transcript)` invoked in the assembler and in the
replay path, plus a property test over the compactor. Cheap at M1a; the class of bug it catches is
expensive to diagnose.

### 5b.2 Prefire two-pass compaction

Compaction currently runs synchronously at the trigger. The alternative measured by Grok Build:

| | Pass 1 | Pass 2 |
| :--- | :--- | :--- |
| Covers | ~95% of history **by estimated-token weight** | `NOTE₁` + the ~5% tail |
| Runs | **in background, ~10 percentage points below the trigger** | synchronously, at compaction time |
| Latency | off the critical path when it finishes in time | dominated by tail prefill — small by construction |

Validity is a **cheap prefix fingerprint** — a hash over `(length, per-item tag, text)` of the items
pass 1 covered. Pass 2 applies `NOTE₁` only if the live conversation still carries that exact prefix; an
edit, rewind, branch or model switch invalidates it and pass 1 is simply wasted, never wrong. The split
index snaps to tool boundaries per §5b.1.

Grok Build records **seven distinct prefire outcomes as stable telemetry keys** (`cached`, `disabled`,
`too_small`, `empty_split`, `sample_failed`, `empty_note1`, plus a debug arm), which makes the
optimization's hit rate observable rather than assumed. That instrumentation is the part worth copying
first — a speculative optimization with no hit-rate metric is a guess.

### 5b.3 Rewriting sent history is cache-hostile until measured

Hermes ships **micro-compaction** — folding the oldest un-absorbed exchange into a running summary
after every turn — and its own documentation argues against enabling it: *"each pass rewrites
already-sent history, which breaks the provider prompt-cache prefix every turn."* It is **off by
default**.

Two teams, one problem, opposite answers, one of them documented as a mistake by its own authors. The
rule that follows, stated so it is not rediscovered:

> Any mechanism that rewrites already-sent history converts every cached **read** on the rewritten
> span into a **write**. At the 1.25×/0.1× asymmetry in §1.1 that is a ~12× swing on the affected
> tokens. The multiplier must appear in the mechanism's ablation before it ships, and a per-turn
> rewrite is presumed cache-hostile until a number says otherwise.

**Context editing** (`clear_tool_uses_*`) is *not* covered by this rule when it clears a suffix rather
than rewriting a prefix — the distinction is whether the change lands before or after the last
breakpoint, and it is worth stating in the ablation design.

### 5b.4 A cache hit-rate target, stated as a target

§1.6 makes hit rate a first-class metric with a CI floor but never names a number. A **>92% hit rate on
the stable prefix over a repeated-prefix replay** is proposed as the M2 floor — chosen because it is
achievable when the five-layer prefix holds and is broken by exactly one class of defect (a silent
invalidator above the last breakpoint). It is a *target to calibrate against our own replay*, not a
figure taken from a reference, and the first measurement may move it.

Related and easy to miss: the denominator matters. Hit rate computed over *total* prompt tokens is
dominated by the dynamic tail and will never approach 92%; computed over the **stable prefix span**, it
is a direct test of whether the prefix is actually stable. The metric definition belongs with the
metric.

### 5b.5 Attention diffusion — a second hypothesis alongside the ~70% cliff

A figure circulating in 2026 places the sharpest attention diffusion in the **middle 40–60% of the
occupied window** rather than at a utilization threshold — the "lost in the middle" effect given a
range. **This is unverified** and, per [measurement §1c.2](./rewrite_v300_measurement_strategy.md), it
does not come from the ETH Zürich paper it is sometimes attributed to.

It is recorded here because it is *cheap to test alongside a sweep we are already running*, and because
it implies a different remedy: a utilization cliff argues for compacting earlier, whereas mid-window
diffusion argues for **placing high-salience content at the head and the tail** and treating the middle
as the region to compact first. Those are different designs, and one sweep can distinguish them if the
sweep records *where* in the window the retained content sat.

### 5b.6 The AGENTS.md result lands on layer 4

[Measurement §1c.1](./rewrite_v300_measurement_strategy.md) records the controlled finding that
repository context files do not improve resolve rate on average while costing >20% more — with
LLM-generated files *hurting* (~−3%) and human-written ones helping (~+4%).

Our static repo-context layer (breakpoint 3) is machine-generated. The honest reading is that it sits
on the wrong side of that split and **the burden of proof is on us**, not on the skeptic. The proposed
response is not to remove it on a paper's authority but to make it the **first ablation of M2**, with a
hand-authored brief of equal token budget as the second arm.

### 5b.7 Rules versus skills, and path-scoped instruction modules

§5.3 asks for a rule budget on the frozen prefix and notes that path-scoped instructions beat a global
set. Two mechanisms make that actionable:

**The membership test.** A constraint on any output is a **rule** — always on, counts against the rule
budget. A procedure for a task type is a **skill** — loaded on invocation, costs nothing until used.
Anything that fails both tests probably should not exist. *"Never expose raw database IDs"* is a rule;
*"here is how to add an endpoint in this project"* is a skill, and putting the second in the first
position pays 40 lines on every call.

**Path scoping.** Instruction modules are keyed to path prefixes and resolve from the touched paths
upward, so only the subsystem's rules are in context when working in that subsystem. The reported
effect is a **40–50% reduction in always-on context with no loss of coverage** — another third-party
number, another hypothesis, and one measured by the same ablation as §5b.6.

**Disclosed staleness** is the third piece and the cheapest. A repo fact baked into the stable prefix —
branch, dirty state, dependency versions — should carry an explicit *"this was true at prompt-build
time; re-check before acting"* rather than being refreshed per turn. Refreshing is cache-hostile per
§5b.3; letting it rot silently is wrong; disclosing it costs one sentence.

### 5b.8 Diversity re-ranking, and hard caps on memory artifacts

**MMR with token-set Jaccard.** Redundancy in retrieved context is a real cost: three near-identical
chunks occupy budget a fourth, different chunk needed.
`MMR(d) = λ·relevance(d) − (1−λ)·max_similarity(d, selected)`, with similarity computed as Jaccard over
tokenized snippets rather than embedding cosine. It needs no model, works on the FTS-only path, is
O(n²) over a candidate set of 6–18, and is roughly twenty lines. It is orthogonal to ADR-0014's dense
tier and improves whichever retriever is running.

**Hard caps with visible truncation.** Claude Code's auto-memory caps `MEMORY.md` at 200 lines and
25 KB — line truncation first, byte truncation after — and the memory directory at 200 files, **with a
warning comment appended at the truncation point**. The visible marker is the part that matters: silent
truncation is worse than either keeping or dropping the content, because the model reasons over a
fragment as though it were whole. The same rule applies to every injected block — repo map, skill
listing, tool schemas.

### 5b.9 A ceiling on the tool-schema share of the window

Tool definitions render at position 0 and are paid on every call. Anthropic's published guidance —
fewer than 10 MCP servers, fewer than 80 total tools, with 15–20K tokens on schemas alone past that —
is a useful bound. The measured result behind lazy loading is more interesting than the cost saving:
token overhead 55K → 8.7K (−85%) **and tool-selection accuracy 49% → 74% on Opus 4** (+25 points),
falling to +8.6 on Opus 4.5.

That accuracy gain says the eager baseline was not merely expensive, it was **confusing the model** —
and the shrinking gain across one model generation is the signature of a scaffolding benefit, which
implies it may matter *more* on the weak models Tier 0 uses. Proposed treatment: the always-on schema
share carries a declared ceiling as a budget line item, and deferred loading enters as an **early
ablation arm** rather than an M3 feature, with the `ToolRegistry` shaped so search-and-load is a
substitution rather than a rewrite.

---

## 5c. Track B cross-check

### 5c.1 Adopt: ephemeral chain-of-thought truncation

Track B's ADR-01 carries a mechanism this document does not have: **the context retains tool calls and
their results, and discards the verbose reasoning trace from past turns.** Its stated rationale is that
CoT from a completed turn consumes window without informing future ones.

That lands exactly on §5.4's finding — reasoning generates tokens, tokens extend context, context
accelerates rot for every subsequent step, measurably past ~20 tool calls. §5.4 states the problem and
offers no mechanism beyond "reasoning depth is a per-step decision". **Track B's is the mechanism**,
and it is cheap: reasoning blocks are already a distinct content type on the wire.

Two cautions before it is adopted as a default rather than an ablation arm:

- **It is a prefix rewrite** and therefore falls under §5b.3 — dropping blocks from already-sent
  history invalidates the cache from the drop point onward. The version that is cache-safe drops
  reasoning only from the region being compacted anyway, not from the live tail.
- **Anthropic's `clear_thinking_20251015` context-editing beta does this provider-side**, which is a
  cheaper implementation of the same idea and is already noted in §2.2 as an ablation target. Worth
  comparing the two rather than building ours first.

### 5c.2 Adopt: the three-track memory naming

§4 splits memory into short-term / long-term / knowledge-net. Track B's split is
**episodic · semantic · procedural**, mapped to concrete stores: episodic in SQLite WAL, semantic in a
workspace-scoped `MEMORY.md`, procedural in `SKILL.md` files.

B's version is better, for one specific reason: it makes **skills a memory tier** rather than a
separate subsystem. That connects [autonomy §2](./rewrite_v300_autonomia_agi.md)'s skill corpus to
§5.3's frozen-prefix rule budget — a skill *is* procedural memory competing for the same attention
budget — and it makes the curator's job legible as memory consolidation rather than as file
housekeeping. Suggested: adopt the naming and the store mapping; keep A's bi-temporal requirement on
the episodic tier, which B does not have.

### 5c.3 Adopt: a stated λ for MMR

§5b.8 specifies MMR with token-set Jaccard and does not name λ. Track B specifies **λ = 0.7**
(0.7 relevance / 0.3 diversity). That is a reasonable starting value and a stated default beats an
unstated one — as an ablation parameter, not a constant.

### 5c.4 Fork F10 — the prefix layout

| | **Track A** | **Track B** |
| :--- | :--- | :--- |
| Structure | 5 layers, **4** `cache_control` breakpoints, rolling tail | **3 fixed markers**: Identity → Tool Schemas → **AST Skeleton Map** |
| Repo context | Static repo layer at breakpoint 3, **flagged as the first M2 ablation** | AST Skeleton Map as a permanent marker |
| Target | >92% over the stable-prefix span (§5b.4) | >92% hit rate |

The two layouts are close and mostly compatible — B's three markers are A's layers 1, 2 and 4 with
memory/skills folded in. **The contested element is the AST Skeleton Map as a permanent fixture.**

Track B cites arXiv 2602.11988 in support of its context design. That paper's actual finding is that
repository context files **do not improve resolve rate on average while costing >20% more**, and that
**LLM-generated** files reduced success ~3% while human-written ones improved it ~4%. A tree-sitter
skeleton is machine-generated repository context — the category the paper measured as negative-value.

This is not an argument that B is wrong: a skeleton and an `AGENTS.md` are different artifacts, the
paper did not test skeletons, and A carries the same exposure. It is an argument that **neither track
has evidence for this layer and both should treat it as an experiment.** §5b.6 already makes it the
first ablation of M2; the suggestion for the meeting is that both tracks adopt that ablation rather
than either defending its layout.

**One genuine advantage of B's three-marker form:** fewer markers leave more of the four-breakpoint
budget for the rolling tail, which is what §1.3's 20-block lookback problem consumes. If the skeleton
layer loses its ablation, A's layout collapses to something very close to B's — which suggests the
gap between them is one measurement wide.

---

## 6. Summary

| Decision | Choice | Reversal / trigger |
| :--- | :--- | :--- |
| Prefix layout | `tools → system → memory → static repo context → dynamic turns` | — |
| Breakpoints | 4 max; static layers plus a rolling tail; intermediate every ~15 blocks in long turns | Hit-rate measurement |
| Minimum cacheable prefix | Per-model config value (512 / 1024 / 2048 / 4096) | New model in the table |
| BoN fan-out | One request, await first token, then N−1 | — |
| Mid-run state change | `role: "system"` message; never edit top-level `system` | Model capability flag |
| Dynamic tool set | `defer_loading` + `tool_addition`, behind a capability flag; static registry default | — |
| Cache hit rate | First-class metric with a CI floor; **>92% over the stable-prefix span** proposed as the M2 floor (§5b.4) | First measurement may move it |
| Transcript parity | `user → assistant → tool_use → tool_result` is a system invariant, asserted in the assembler and the replay path (§5b.1) | — |
| Prefire compaction | Background pass 1 at trigger −10 pp, validated by prefix fingerprint; pass 2 synchronous (§5b.2) | Prefire hit rate, recorded as a stable telemetry key |
| Rewriting sent history | Presumed cache-hostile; the read→write multiplier enters the ablation (§5b.3) | A number |
| Static repo-context layer | **First ablation of M2**, against a hand-authored brief of equal budget (§5b.6) | arXiv 2602.11988 makes this the burden of proof |
| Rules vs skills | Membership test; path-scoped instruction modules; disclosed staleness (§5b.7) | Always-on reduction measured |
| Retrieval diversity | MMR with token-set Jaccard over the candidate set (§5b.8) | — |
| Injected-block caps | Hard byte/line caps with a **visible** truncation marker (§5b.8) | — |
| Tool-schema share | Declared ceiling as a budget line; deferred loading as an early ablation arm (§5b.9) | Accuracy gain, not only cost |
| Compaction trigger | Config value defaulted near the reported ~70% cliff, **not** at overflow | Ablation. Shipped tools report 75/92/95% — the spread is why ours is a parameter |
| Effective window | Plan against MECW (~92% of advertised), not the sticker number | Our own measurement |
| Frozen-prefix rule budget | Tracked alongside the token budget; skills load progressively | Adherence measurement |
| Judge context | Best-of-N judge gets its own budget and hygiene | — |
| Compaction | Own exchange-granular compactor | Ablation vs. server-side compaction, once a baseline exists |
| Summary framing | Historical headings, `REFERENCE ONLY` envelope, latest-message-wins precedence rule | Envelope strength is an ablation — over-strengthening suppresses tool use |
| Summarizer trust | Filter-safe preamble; the compaction boundary is in the TaintGate threat model | — |
| Summarizer model | Cheap auxiliary model with a startup feasibility probe | — |
| Compaction timing | Preflight and idle, never as an overflow handler | — |
| Context editing | Ablation target alongside compaction | — |
| Retrieval | Structural + lexical + graph on; dense deferred | ADR-0014 recall@10 trigger |
| Retrieval-before-edit | Pipeline stage, not an optional tool | — |
| STM | Loop-local, not a port | — |
| LTM | Bi-temporal, growth tier | — |

Downstream: [edit mechanism](./rewrite_v300_mecanismo_edicao.md) (the repair loop must not fork the
prefix), [blueprint](./rewrite_v300_blueprint_arquitetura.md), [measurement](./rewrite_v300_measurement_strategy.md).
