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

## 6. Summary

| Decision | Choice | Reversal / trigger |
| :--- | :--- | :--- |
| Prefix layout | `tools → system → memory → static repo context → dynamic turns` | — |
| Breakpoints | 4 max; static layers plus a rolling tail; intermediate every ~15 blocks in long turns | Hit-rate measurement |
| Minimum cacheable prefix | Per-model config value (512 / 1024 / 2048 / 4096) | New model in the table |
| BoN fan-out | One request, await first token, then N−1 | — |
| Mid-run state change | `role: "system"` message; never edit top-level `system` | Model capability flag |
| Dynamic tool set | `defer_loading` + `tool_addition`, behind a capability flag; static registry default | — |
| Cache hit rate | First-class metric with a CI floor | — |
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
