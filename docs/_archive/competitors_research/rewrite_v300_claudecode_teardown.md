---
status: rationale
retrieval: excluded
updated: 2026-08-05
---

# Claude Code — teardown of the reference corpus, and the "less scaffolding" thesis

**Reference under study:** `src/claude_refs/` — two independent third-party documentation corpora:

| Corpus | Provenance | Licence | Currency |
| :--- | :--- | :--- | :--- |
| `claude-code-analysis/` | **Unofficial reverse-engineering of the Claude Code source tree**, 3,811 words | MIT | dated **2025-03-31** |
| `claude-code-ultimate-guide/` | Community guide, 628 files, ~1,256,000 words, with explicit source tiering and an official-docs tracker | CC BY-SA 4.0 | **v3.41.1, Jul 29 2026** |

**Reader:** Tech Lead A, ahead of the AETHER v3.0.0 architecture review.

---

## 0. What this document is, and a provenance warning that comes first

Same posture as the Grok Build and Hermes teardowns: an **audit followed by suggestions**. Nothing
decides anything, nothing overrides [`rewrite_v300_decisoes_adr.md`](../../rationale/rewrite/rewrite_v300_decisoes_adr.md),
and where a finding contradicts a decision we already made this document says so and leaves it open.

But this reference needs a caveat the other two did not, and it should be settled before the
material is used.

**`claude-code-analysis/DOCUMENTATION.md` is a reverse-engineering of a de-obfuscated bundle.** Its
own README says so: *"all reverse-engineered from the source code"*, *"This is an unofficial,
independent analysis."* Claude Code does not publish CLI source. Our standing policy **L2**
explicitly deferred exactly this class of artifact — de-obfuscated bundles are *"deferred, not
permanently excluded"*, and any future move toward a competitor's design *"requires a rationale
grounded in our own KPIs and measurements."* A structural description derived from such a bundle
is closer to that line than official documentation is.

My advice, offered for the Tech Lead to accept or override:

- Treat `claude-code-analysis` as usable for **shape only** — which subsystems exist, their relative
  proportions, the fact that a thing is a separate module. Shape is inference-safe and mostly
  re-derivable from observable behaviour.
- Do **not** treat it as a source for implementation detail, algorithm, or naming. Nothing in
  AETHER should trace to it.
- Note that it is **dated 2025-03-31** while the guide tracks **v3.41.1 (Jul 2026)** — roughly
  sixteen months and several major versions stale. Several things it describes have demonstrably
  changed since.
- Everything load-bearing in this teardown is therefore sourced from `claude-code-ultimate-guide`,
  which documents *observable behaviour, official Anthropic documentation, and published
  engineering posts*. Where I use the analysis at all, it is marked.

Proposals continue the shared numbering at **P61**, after
[`rewrite_v300_grokbuild_proposals.md`](rewrite_v300_grokbuild_proposals.md) (P1–P15),
[`rewrite_v300_grokbuild_teardown.md`](rewrite_v300_grokbuild_teardown.md) (P16–P41) and
[`rewrite_v300_hermes_teardown.md`](rewrite_v300_hermes_teardown.md) (P42–P60).

---

## 1. Method, and a discipline worth stealing before anything else

The guide opens with a **Source Transparency** table, and every substantive claim in it carries a
confidence marker:

| Tier | Description | Confidence | Example |
| :--- | :--- | :--- | :--- |
| **Tier 1** | Official Anthropic documentation | 100% | anthropic.com/engineering/* |
| **Tier 2** | Verified reverse-engineering | 70–90% | observed CLI behaviour |
| **Tier 3** | Community inference | 40–70% | observed but not officially confirmed |

Sections then declare, for example, *"Confidence: 75% (Tier 2 — Community-verified with research
backing)"* before making a claim about the auto-compaction threshold — and then give **five
conflicting reported values** from five sources rather than picking one.

> **P61 · Per-claim source tiering in our own reference documents.** Grade A, near-zero cost, and
> the most immediately useful thing in this corpus. Our teardowns currently mix "the code says X"
> with "this is a reasonable inference" without marking the difference. A three-tier marker on
> every non-obvious claim makes the documents auditable by someone who was not in the room, and it
> makes it visible when a design decision is resting on a 40%-confidence inference. It also
> generalizes to AETHER's own run manifests: a measured number and an estimated number should not
> look alike.

Coverage in this teardown: `claude-code-analysis/DOCUMENTATION.md` in full (with the caveat above);
in the guide, `guide/core/architecture.md`, `guide/core/context-engineering.md`,
`guide/core/memory-systems.md`, `guide/workflows/agent-teams.md`, and the security and
example directories. The two `ultimate-guide.{md,fr.md}` monoliths (159k + 142k words) and the 95k
word CHANGELOG were sampled rather than read whole.

---

## 2. The thesis: "Less scaffolding, more model"

This is the design philosophy of Claude Code, it is stated as Tier 1, and it is a **direct
challenge to a substantial part of the AETHER plan.** It deserves to be put in front of the review
without softening.

The guide's table (§10 of `architecture.md`):

| Traditional approach | Claude Code approach |
| :--- | :--- |
| Intent classifier → Router → Specialist | Single model decides everything |
| RAG with embeddings | Grep + Glob (regex search) |
| **DAG task orchestration** | **Simple while loop** |
| Tool-specific planners | Model-driven tool selection |
| Complex state machines | Conversation as state |
| Prompt engineering frameworks | Trust the model |

And the master loop itself, stated as 100% Tier 1:

```
while (claude_response.has_tool_call):
    result = execute_tool(tool_call)
    claude_response = send_to_claude(result)
return claude_response.text
```

> **There is no:** intent classifier · task router · RAG/embedding pipeline · DAG orchestrator ·
> planner/executor split.

Eight core tools carry the whole product: **Bash, Read, Edit, Write, Grep, Glob, Task, TodoWrite.**

### 2.1 The search decision, which is the sharpest data point

From the guide's TL;DR, sourced to the Latent Space podcast (May 2025):

> "Early Claude Code versions experimented with RAG using Voyage embeddings for semantic code
> search. Anthropic switched to grep-based (ripgrep) agentic search after internal benchmarks
> showed superior performance with lower operational complexity — no index sync required, no
> security liabilities from external embedding providers."

This is not a team that never tried retrieval. It is a team that **built it, benchmarked it, and
removed it.** The stated trade is explicit: "Search, Don't Index" trades latency and tokens for
simplicity and security.

### 2.2 What this does and does not mean for us

Three observations, offered as framing rather than as a recommendation.

**First, the philosophy is inseparable from the model tier.** The guide's own stated reason is
*"Claude 4+ is capable enough to handle routing decisions."* Our Tier 0 benchmark ladder runs free
local models, and the whole point of that ladder is to establish a floor before we can afford
frontier models. A scaffold-light design that works on Opus may not work on a 7B local model — and
the *scaffold-attributable lift* we are measuring in
[`rewrite_v300_measurement_strategy.md`](../../rationale/rewrite/rewrite_v300_measurement_strategy.md) is precisely the
quantity that "less scaffolding" argues should be small. If our lift is real on a fixed model,
that is evidence against the thesis *for that model tier*. If it is not, we have learned something
important cheaply.

**Second, we are not building the same product.** Claude Code is an interactive assistant with a
human in the loop who can `/clear`, re-scope, and intervene. AETHER targets ≥8 hours unattended
(T5). Several of the things Claude Code omits — a DAG, memoization, a resume protocol — exist to
survive the absence of that human. Both Grok Build (a full goal-mode state machine with six pause
reasons) and Hermes (a verification ledger and a stop guard) added machinery of exactly this kind,
and both are closer to our autonomy target than Claude Code's default loop is.

**Third, and most usefully: the thesis is a falsifiable claim we can test almost for free.** Our
roadmap already puts the workflow DAG types at M0 and a four-node linear graph at M1a, deliberately
small. That is close to a natural experiment. The honest version of the question is not "DAG or no
DAG" but *"at our model tier, on our task distribution, does the DAG's memoization and resumability
buy more than its complexity costs?"* — and that is an ablation, not an argument.

> **P62 · Run the scaffolding thesis as a named ablation, not a debate.** Grade A. Suggestion:
> designate the linear-graph-versus-plain-loop comparison as a first-class M1b/M2 ablation with a
> pre-registered metric, so that ADR-0018 and A-024 are either confirmed by our own numbers or
> reversed by them. This costs one extra arm in an experiment we are already running, and it
> converts the single largest architectural disagreement between us and the market leader into a
> measurement.

---

## 3. The loop's API vocabulary, and turn budgets

The guide is precise about how the loop maps onto the Anthropic API, which matters because our
`ModelProvider` port has to expose exactly this:

| `stop_reason` | Meaning | Loop action |
| :--- | :--- | :--- |
| `tool_use` | Claude wants to call one or more tools | execute, feed results back, continue |
| `end_turn` | finished | exit, return text |
| `max_tokens` | context limit reached before finishing | rethink context strategy; likely need summarization |

Two details worth carrying:

**`max_turns` should be per task type, not global.** The guide's ranges: simple retrieval 5;
research or multi-step coding 20–30; extended autonomous workflows 50. With the stated reason:
*"Setting `max_turns` per task type rather than globally prevents a single slow task from starving
others in a multi-agent pipeline."* And the discipline that follows — check the terminal
`stop_reason` and implement an explicit incomplete path, because "the task may be incomplete."

**`fork_session`** creates an independent branch of a conversation sharing history up to the fork
point — *"like `git branch` but for agent sessions"* — used to compare approaches under different
tool configurations or prompt variants without re-running from scratch.

> **P63 · Task-typed turn budgets with an explicit incomplete path.** Grade A, small. Our
> `ResourceGovernor` currently reasons about tokens and wall-clock. A turn cap keyed to task class,
> plus a distinct terminal state for "hit the cap" that is *not* the same as "failed", is what
> makes a cap safe to set aggressively. This connects to Grok Build's `BudgetLimited` pause
> variant, which is the same idea given a name in the state machine.
>
> **P64 · Session forking as a first-class primitive for ablations.** Grade B. Our benchmark
> harness will want to compare two prompt variants from the same point in a trajectory. If the
> `TrajectoryStore` supports a fork with shared history rather than a full replay, ablations get
> cheaper by roughly the cost of the shared prefix — and with prompt caching, the shared prefix is
> the part that was already paid for.

---

## 4. Context engineering — the most transferable section

This is where the corpus is strongest, because most of it is measured or widely corroborated
rather than inferred. Several figures here already appear in
[`rewrite_v300_contexto_memoria.md`](../../rationale/rewrite/rewrite_v300_contexto_memoria.md); this pass adds the ones we
do not yet have and firms up the provenance of the ones we do.

### 4.1 Context rot is structural

> "Transformer models attend to all tokens pairwise… the number of attention relationships grows as
> n², not n… **This is not a bug that future models will eliminate.** It is a consequence of the
> architecture itself."

Already our position. What is new is the 2026 refinement: NIAH benchmarks measure *lexical*
retrieval, and once question and needle stop sharing vocabulary, degradation is worse than NIAH
suggests. The cited data point — Opus 4.6 as a trajectory monitor on MonitorBench dropping from
98.6% to 88% recall with 800K tokens of benign prior actions prepended — is offered with an
unusually careful caveat: *"specific to its setup and not a general constant… read it as evidence
that the failure mode also hits monitor and classifier models, not just generation."*

That last clause is the one we should absorb. **Our gates are classifier models.** A tri-state gate
or an LLM judge running over a long trajectory is subject to the same degradation as the generator
it is judging, and our measurement design does not currently account for that.

> **P65 · Treat gate and judge context as a budgeted resource, separately from generator context.**
> Grade A. If an evaluator's recall degrades with the length of what it is evaluating, then a gate
> that reads the whole trajectory becomes less reliable exactly when the run is longest — which is
> when we need it most. Both Grok Build (evaluator transcript capped at 32 KB; skeptics read the
> diff from a file) and Hermes (evidence summary capped at 1,200 chars) cap their judges' inputs.
> Ours should declare a budget too, and the A/A noise floor should be established at a
> representative trajectory length rather than a short one.

### 4.2 The budget numbers

| Source | Typical tokens |
| :--- | :--- |
| Global `CLAUDE.md` | 1,000–3,000 |
| Project `CLAUDE.md` | 2,000–8,000 |
| Path-scoped modules (all active) | 1,000–5,000 |
| Imported skills / commands | 500–3,000 |
| **Total always-on** | **~5,000–20,000** |

With the rule: **always-on context should stay below 5% of the context window.** "Beyond that you
are displacing actual task content, which matters more per token than standing instructions."

**Adherence degrades with instruction-file size**, on estimated baselines:

| Lines in `CLAUDE.md` | Adherence |
| ---: | ---: |
| 1–100 | ~95% |
| 100–200 | ~88% |
| 200–400 | ~75% |
| 400–600 | ~60% |
| 600+ | ~45% and falling |

And the **150-instruction ceiling**: beyond ~150 distinct rules, models begin selectively ignoring
some. HumanLayer production data cited: structured context — fewer, more specific rules, organized
hierarchically — shows **15–25% better adherence** than undifferentiated long rule lists.
*"Rule quality beats rule quantity. Twenty specific, actionable rules outperform 200 generic
aspirational ones."*

**MECW ~92%** of the advertised window, with a **sharp non-linear quality drop around 70% of budget
used** — the guide notes nine speakers at one meetup independently reporting the same threshold and
reads that as a notably strong signal for a claim usually offered as a hunch.

### 4.3 Path-scoping — the single highest-leverage technique

Rules load only when files in their scope are in context:

```
Without: root CLAUDE.md with backend + frontend + database + API rules = 8,000 tokens always on

With:    root CLAUDE.md, shared rules              = 2,000 always on
         src/api/      module                      = +1,500 when active
         src/components/ module                    = +1,200 when active
         prisma/       module                      =   +800 when active
```

Claimed result: **40–50% reduction in always-on context with no loss of coverage.**

> **P66 · Path-scoped instruction modules.** Grade A. This is directly applicable to our repo-map
> and operating-brief design and it is cheap: a directory convention plus a resolver that walks
> from the touched paths upward. It is also the mechanism that makes the adherence table above
> survivable on a large repo — you do not fix a 600-line instruction file by writing better rules,
> you fix it by not loading 500 of them.

### 4.4 Rules versus skills — a distinction we have not drawn

| Dimension | Rules | Skills |
| :--- | :--- | :--- |
| Nature | constraints, standards, conventions | capabilities, procedures, workflows |
| When active | always enforced | invoked on demand |
| Example | "Never use `any` in TypeScript" | "How to add a new API endpoint" |
| Token cost | always-on | loaded only when invoked |

*"Putting the endpoint creation procedure in a rule would mean loading 40 lines of procedural
instructions for every session, even when you're not creating endpoints."*

> **P67 · Split always-on constraints from on-demand procedures, structurally.** Grade A. Our
> design currently has "skills" and "the operating brief" but does not draw this line explicitly.
> The test is mechanical and worth encoding: *if it is a constraint on any output, it is a rule and
> it is always on; if it is a procedure for a specific task type, it is a skill and it is loaded on
> invocation.* Anything that fails both tests probably should not exist.

### 4.5 Chain-of-thought hurts in long agentic tasks

> "Anthropic's engineering data shows it can hurt performance in long agentic tasks. The mechanism:
> CoT generates additional tokens, which extend context length, which accelerates context rot for
> subsequent steps. On tasks spanning 20+ tool calls, this effect is measurable."
>
> "Use CoT for complex isolated reasoning steps, not as a blanket strategy for agentic workflows.
> In long runs, prefer compressed intermediate outputs over extended reasoning traces."

This is counter-intuitive and directly relevant to an 8-hour unattended target. It also suggests a
concrete ablation arm: reasoning-effort as a *per-step* setting rather than a session-wide one.

### 4.6 Retrieval beats fine-tuning for teaching new facts

> "A model fine-tuned on 'A is B' frequently cannot answer 'what is B'… Retrieval keeps the fact as
> text in context rather than asking the model to generalize from a weight update, which sidesteps
> the problem entirely."

Cited to two independent Stanford courses. Worth recording because our M5 meta-loop scope
(prompts, routing, skills — never weights) is sometimes questioned as insufficiently ambitious;
this is an argument that it is the *right* scope for knowledge, independent of cost.

---

## 5. Tool economics — the numbers that matter most

### 5.1 Tool Search (lazy loading) — Tier 1, with measurements

Since v2.1.7 (January 2026), tool definitions are loaded lazily via Anthropic's Advanced Tool Use
feature. The problem it solves is quantified: *"GitHub MCP alone: ~46K tokens for 93 tools"*; a
developer documented *"66,000+ tokens consumed before typing a single prompt."*

The flow: only a search tool loaded (~500 tokens) → Claude determines the needed capability → search
finds matching tools by regex/BM25 → only matched tools loaded (~600 tokens each) → invoke normally.

**Measured improvements (Anthropic benchmarks):**

| Metric | Before | After | Change |
| :--- | ---: | ---: | :--- |
| Token overhead (5-server setup) | ~55K | ~8.7K | **−85%** |
| Opus 4 tool-selection accuracy | 49% | 74% | **+25 pts** |
| Opus 4.5 tool-selection accuracy | 79.5% | 88.1% | **+8.6 pts** |

Configurable by context-share threshold: `ENABLE_TOOL_SEARCH=auto` defaults to 10%, `auto:5` for
100+ tools, `auto:20` for lightweight setups.

The accuracy result is the one to notice, and it is not the one people expect. Lazy loading is
usually argued as a cost optimization. Here it **improved tool selection by 25 points on Opus 4** —
which says the eager-loading baseline was not merely expensive, it was actively confusing the
model. And the smaller gain on the stronger model (+8.6 on 4.5) says the effect shrinks as models
improve, which is exactly the shape of a scaffolding benefit.

> **P68 · Tool Search, upgraded from "measure later" to "measure early".** Grade A. In
> [`rewrite_v300_grokbuild_teardown.md`](rewrite_v300_grokbuild_teardown.md) P31 I graded deferred
> tool schemas "B for MVP" on the argument that eight tools do not need it. These numbers change
> the calculus in one specific way: if the benefit is partly *accuracy* and not only *cost*, then
> it may matter at our tool count too, and it may matter **more** on the weaker models our Tier 0
> ladder uses. Suggestion: keep it out of the MVP, but add it as an early ablation arm rather than
> an M3 feature, and design the `ToolRegistry` port so a search-and-load path is a substitution
> rather than a rewrite.
>
> **P69 · A declared ceiling on always-on tool schema share.** Grade A. The guide's threshold
> mechanism is the good idea underneath: tool loading switches strategy at a *percentage of context
> window*, not at a fixed tool count. Anthropic's own guidance cited alongside it — fewer than 10
> MCP servers, fewer than 80 total tools, with 15–20K tokens burned on schemas at 80+ tools — is a
> useful sanity bound. Our budget accounting should treat tool schemas as a named line item with a
> ceiling, the same way we treat the repo map.

### 5.2 Programmatic Tool Calling

> "Instead of calling tools one at a time with a full model round trip each, Claude writes Python
> code that orchestrates all tool calls internally. Only the final `stdout` enters the context
> window."
>
> Traditional: 3 tools = 3 inference passes, 3× intermediate results in context.
> PTC: 3 tools = 1 inference pass, only final output in context.

This is the same mechanism as Hermes' `execute_code` (which is also why Hermes *refunds* its
iterations — see P55). Three references now converge on it, which makes it worth a slot in the
plan even though it is not on any current milestone.

> **P70 · Code-mode tool orchestration as a token lever.** Grade B, and the ablation is clean.
> The gain is largest exactly where our workload is heaviest — multi-step tool sequences whose
> intermediate results are large and mostly uninteresting (grep hits, test output, file listings).
> The risk is equally clear: it is arbitrary code execution inside the loop, so it lands squarely
> on the sandbox perimeter and the CAR grant model, and it should not be considered before those
> are solid.

### 5.3 The eight-tool arsenal

Bash, Read, Edit, Write, Grep, Glob, Task, TodoWrite. Our blueprint starts at ~8 core *ports*,
which is a different unit, but the convergence on a small tool count across all three references
(Claude Code 8 core; Hermes' Footprint Ladder pushing capability *out* of the tool schema; Grok
Build's behaviour-versioned managed tools) is consistent enough to treat as settled: **tool count
is a scarce resource, and the scarcity is about model attention, not about cost alone.**

---

## 6. Sub-agents, and then agent teams

### 6.1 Sub-agents: depth = 1

The `Task` tool spawns a sub-agent with its own fresh context that receives *only the task
description*, has the same tools *except* `Task`, and returns *summary text only*. The stated
reasons for depth = 1: recursive explosion, context pollution, debugging difficulty, unpredictable
costs.

Types: `Explore` (read-only tools), `Plan` (all except Edit/Write), `Bash` (Bash only),
`general-purpose` (all tools). This is capability-mode-by-role, the same shape as Grok Build's
`SubagentCapabilityMode` and consistent with our CAR model.

**The rule the guide calls the most common mistake in multi-agent design:**

> "**Context is never inherited automatically.** When the coordinator spawns Worker A to analyze
> file X, Worker B gets no knowledge of that analysis unless the coordinator explicitly passes it
> in the task description."
>
> "Workers should never need to communicate with each other. If they do, that's a sign the
> decomposition is wrong and the task belongs in the coordinator."

That last sentence is a design *test*, not just advice, and it is a sharper formulation of the
Conductor constraint we already adopted in
[`rewrite_v300_autonomia_agi.md`](../../rationale/rewrite/rewrite_v300_autonomia_agi.md).

### 6.2 Agent Teams — and the fact that they lifted their own constraint

Introduced v2.1.32 (2026-02-05) as a research preview behind
`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, requiring Opus 5:

- **Lead + teammates**, each an independent instance with its own 1M-token context.
- **Git-based task claiming** — lock files in `.claude/tasks/` (`task-1.lock`, `task-3.pending`).
- **Continuous merge** — agents pull/push to the shared repo with automatic conflict resolution.
- **A mailbox**, enabling **true peer-to-peer messaging**: teammate ↔ teammate, not only
  hierarchical reporting. *"Agents actively challenge each other's approaches"* and *"debate
  solutions without human intervention."*
- **Context stays isolated; messages are shared.** "Agent 1's full 1M token context is invisible to
  Agent 2."

This is worth dwelling on. The same product that documents depth = 1 with four good reasons ships a
separate mechanism that gives you a lead coordinating N peers who message each other — which is
functionally a second level of delegation reached by a different route. The constraint was on
*nesting the Task tool*, not on multi-agent structure as such.

**The adoption and anti-pattern data is the useful part** (Anthropic's 2026 Agentic Coding Trends
Report, 5000+ organizations):

| Anti-pattern | Symptom | Fix |
| :--- | :--- | :--- |
| Too many agents | >5 agents ⇒ coordination overhead > productivity | start 2–3, scale progressively |
| Over-delegation | context-switching cost exceeds gains | human oversight on critical decisions |
| Premature automation | automating a workflow not mastered manually | manual → semi-auto → full-auto |

And the sizing heuristic, which reframes the question well:

> "The real question is not 'how many agents?' but **'is the coordination overhead less costly than
> the context overflow?'**"

| Codebase | Single agent | 3-agent team | 5-agent team |
| :--- | :--- | :--- | :--- |
| 10K lines | ~30% context, comfortable | overkill | overkill |
| 50K lines | 80–90% context, degraded reasoning | ideal split | justified if truly parallel |
| 100K+ lines | context overflow, agent misses files | may still overflow | justified, consider more |

Critical success factors named: modular architecture, comprehensive tests, clear task decomposition.
**Named blocker: monolithic codebase, weak test coverage.**

> **P71 · Fan-out sized by context pressure, not by task count.** Grade A as a design principle.
> This is a genuinely better decision rule than "parallelize when tasks are independent", and it is
> measurable: if a single agent would exceed some fraction of its window just loading the relevant
> files, split; otherwise do not. Our `ResourceGovernor` has the inputs to compute this.
>
> **P72 · A mailbox as the inter-agent channel, with context isolation preserved.** Grade B, and
> it belongs at M3+ if at all. The property that makes it safe is the one stated explicitly:
> messages are shared, context is not. That keeps each agent's prefix cacheable and keeps the
> information flow auditable — every fact that crossed between agents exists as a discrete message
> we can log, rather than as an implicit context inheritance we cannot reconstruct.
>
> **P73 · Git-based task claiming for parallel work.** Grade B. Lock files in a shared directory,
> claimed by write, with continuous merge. Simple, inspectable, and it survives process death,
> which matters for T5. Worth comparing against a database-backed queue when we get there; the git
> version has the advantage that the coordination state is in the same artifact as the work.

Note also, from the guide: as of March 2026 **all agents in a team run the same model**, and
role-based model selection (Opus lead, Sonnet implementers, Haiku testers) is an open community
request. That is a gap we could occupy deliberately rather than inherit.

---

## 7. Memory — three tracks, and a third independent "dream"

### 7.1 The native stack

| System | Written by | Read by | Scope | Persists |
| :--- | :--- | :--- | :--- | :--- |
| `CLAUDE.md` | human, manually | main agent + all sub-agents | project or global | git-tracked |
| Auto-memory (v2.1.59+) | main agent, automatically | main agent only | per-project, per-user | gitignored |
| Agent memory (v2.1.33+) | the agent itself | that agent only | `user` / `project` / `local` | depends on scope |

Auto-memory has **hard enforced limits**: `MEMORY.md` capped at 200 lines and 25 KB (line
truncation first, then byte truncation, each appending a warning comment), memory directory capped
at 200 files with oldest pruned. Agent memory injects **the first 200 lines** of the agent's
`MEMORY.md` into its system prompt at start.

Five limits the guide names honestly: local per machine; **no semantic retrieval** (memory is read
linearly from the top of the file); no cross-project aggregation; slow consolidation trigger; and
sub-agents in dispatch mode share no session history — `CLAUDE.md` is the only shared layer.

### 7.2 Auto Dream

Community-discovered, gated behind a server-side flag, rolling out from v2.1.83+. Trigger
conditions: **≥24 hours since last consolidation AND ≥5 sessions**, with a lock file preventing
concurrent runs. Four phases:

| Phase | Name | What happens |
| ---: | :--- | :--- |
| 1 | Orient | list memory dir, read index, skim topic files |
| 2 | Gather Signal | **targeted grep** of session transcripts, not exhaustive reads — *"look only for things you already suspect matter"* |
| 3 | Consolidate | merge new signal, **convert relative dates to absolute**, remove contradicted facts, deduplicate |
| 4 | Prune & Index | rebuild `MEMORY.md` under the 200-line cap, remove stale pointers |

Theoretical grounding cited: *Sleep-time Compute* (UC Berkeley + Letta, April 2025) — pre-computing
during idle reduces test-time compute by ~5×. Safety: **read-only on project source; write access
limited to memory files.** One documented run consolidated 913 sessions in ~9 minutes, taking
`MEMORY.md` from 280+ lines to ~140.

And the guide reports its known quality gaps rather than hiding them (issue #38493, March 2026):
identity (names memory files from session content, not project path, so a renamed project orphans
files), accuracy (*"writes unverified facts without reading source files"* — the cited example,
"18 of 21 items resolved", written without checking), and transparency (no audit trail).

**This is now the third independent implementation of the same mechanism.** Grok Build's `dream`
(config → hours → sessions → lock), Hermes' curator (idle-triggered, `interval_hours`, archive
never delete), and Claude Code's Auto Dream (≥24h AND ≥5 sessions, lock, read-only on source). Two
of the three are literally named "dream". All three gate cheapest-first, all three are
single-flighted by a lock, all three restrict write scope to memory.

> **P74 · Offline memory consolidation, now with a specified phase structure.** Grade A — upgraded
> from P29's Grade B on the strength of three independent convergences. The four-phase decomposition
> is the addition: *targeted* signal gathering rather than exhaustive reads is what keeps the pass
> affordable, and **converting relative dates to absolute** is a small, concrete rule that prevents
> the most common form of memory rot. The known gaps are equally instructive: an accuracy gap
> caused by writing unverified facts is exactly what an evidence-ledger discipline (P48) would
> prevent, and the missing audit trail is what our trajectory store gives us for free.
>
> **P75 · Hard, enforced caps on memory artifacts, with visible truncation.** Grade A, trivial.
> 200 lines, 25 KB, 200 files, with a warning comment appended at the truncation point so the model
> can see that it is reading a truncated file. Silent truncation is worse than either keeping or
> dropping the content, because the model reasons over a fragment as if it were whole.

---

## 8. Editing, permissions, and hooks

### 8.1 The Edit tool (Tier 2, ~90%)

Exact match first; on failure, a fuzzy pass (whitespace normalization, line-ending normalization,
context expansion); on failure of that, an error asking the model to verify `old_string`.
Validations before applying: file exists; `old_string` found; **single match unless `replace_all`**;
new content differs (no-op edits rejected).

This matches SAGIHA's `apply_edit` with `expected_occurrences`, which our
[`rewrite_v300_mecanismo_edicao.md`](../../rationale/rewrite/rewrite_v300_mecanismo_edicao.md) already carries forward. The
addition worth noting is the *fuzzy tier with a warning* — a middle outcome between "applied" and
"failed" that Grok Build also has (`ShiftResult::Found | Ambiguous | NotFound`). Three-valued edit
results appear to be the shape everyone converges on.

### 8.2 Four permission layers

1. **Interactive prompts** — allow once / allow always / deny / edit command.
2. **Allow/deny rules** in `settings.json` — `"allow": ["Bash(npm *)", "Read"]`,
   `"deny": ["Bash(rm -rf *)"]`.
3. **Hooks** — `PreToolUse` (validate before), `PostToolUse` (audit after), `PermissionRequest`
   (override prompts).
4. **Sandbox mode** — filesystem isolation plus network restrictions.

Native sandbox since v2.1.0: **Seatbelt** on macOS, **bubblewrap** (namespaces + seccomp) on
Linux/WSL2, not supported on WSL1, planned on Windows. Model: read the whole machine except denied
paths; **write CWD only**; credentials directories (`~/.ssh`, `~/.aws`) blocked; all network through
a **SOCKS5 proxy with domain allow/deny filtering**; private CIDRs and localhost blocked by default;
child processes inherit; escape hatch via a `dangerouslyDisableSandbox` parameter.

The guide is candid about the limits: shared kernel (vulnerable to kernel exploits, unlike a
microVM), **domain fronting via CDNs can bypass domain filtering**, misconfigured
`allowUnixSockets` grants privilege escalation, and overly broad write permissions enable attacks on
`$PATH` directories. Overhead is stated as ~1–3% CPU for the native sandbox versus ~5–10% for Docker
microVMs.

On dangerous-pattern detection (`rm -rf`, `sudo`, `curl | sh`, `chmod 777`, `git push --force`,
`DROP TABLE`), the guide adds a caveat we should keep: *"This is not a complete blocklist — patterns
are likely detected through model training rather than explicit rules."* Which is to say: the market
leader's dangerous-command detection is substantially **the model's judgement**, not a rule table.

> **P76 · Egress through a filtering proxy, with the fronting caveat recorded.** Grade A, and it
> is already our design — [`rewrite_v300_seguranca_sandbox.md`](../../rationale/rewrite/rewrite_v300_seguranca_sandbox.md)
> specifies a rootless-Podman perimeter with an egress allowlist proxy. What this corpus adds is the
> **named limitation**: CDN domain fronting defeats hostname-based filtering, so an allowlist proxy
> is a cost-and-accident control, not an exfiltration control. That belongs in our threat model
> explicitly rather than being discovered later.
>
> **P77 · A structured hook payload as the extension contract.** Grade B. The payload shape is
> instructive: common fields on every event (`session_id`, `transcript_path`, `cwd`,
> `permission_mode`, `hook_event_name`) plus event-specific fields layered on top, delivered on
> stdin, with block-by-exit-code-2 and parameter modification by returned JSON. That is a
> wire-serializable contract in our sense (I3), and it is a plausible shape for how AETHER exposes
> extension points without granting in-process access. Note the standing decline on speculative
> hooks from Hermes' rubric (P42's neighbour) — a hook with no concrete consumer should not ship.

---

## 9. The claimed internal structure — read with the §0 caveat

Everything in this section comes from `claude-code-analysis` and is therefore **shape-only, Tier 3,
and ~16 months stale.** I include it because relative proportions are informative even when details
are not.

| Category | Claimed count |
| :--- | ---: |
| Total TypeScript files | 1,884 |
| Tool implementations | 41 |
| Command modules (slash commands) | 101 |
| UI components | 130+ |
| Utility files | 300+ |
| Service modules | 35+ |
| Subdirectories in `src/` | 37 |

Stack claimed: TypeScript on Bun, React + Ink for the terminal UI, `@anthropic-ai/sdk`,
`@modelcontextprotocol/sdk`, Commander.js, Zod v4, a Zustand-style store.

The one architectural pattern worth extracting, because it is a genuine technique rather than a
detail: **feature flags used for build-time dead-code elimination.**

```typescript
const assistantModule = feature('KAIROS')
  ? require('./assistant/index.js')
  : null;
```

Whole subsystems are tree-shaken out of the bundle at build time when their flag is off. That is a
different thing from a runtime feature flag, and it is how a product can carry many optional
subsystems without every user paying for them.

Two proportions worth noticing regardless of accuracy:

- **41 tools implemented, 8 described as core.** The gap between "tools that exist" and "tools that
  carry the product" is roughly 5×, which is consistent with the Footprint Ladder logic from Hermes:
  most tools are gated, conditional, or narrow.
- **300+ utility files against 41 tools.** As with Grok Build and Hermes, the mechanism is a small
  fraction of the mass.

> **P78 · Build-time feature elimination for optional subsystems.** Grade C for now — Python has no
> equivalent of Bun's `feature()` and the analogous techniques (extras, optional imports, plugin
> entry points) are weaker. Recorded so it is not rediscovered. It becomes relevant only if we ever
> ship a distributed binary, which is a decision
> [`rewrite_v300_decisoes_runtime.md`](../../rationale/rewrite/rewrite_v300_decisoes_runtime.md) has already deferred.

---

## 10. Three-way convergence

With three references now torn down, the agreements are worth consolidating. A mechanism that three
independent, well-resourced teams arrived at separately is close to settled; a place where they
diverge is a real decision.

### 10.1 Agreed across all three

| Mechanism | Claude Code | Grok Build | Hermes |
| :--- | :--- | :--- | :--- |
| Offline memory consolidation, gated cheapest-first, lock-protected, write-scoped to memory | Auto Dream (≥24h ∧ ≥5 sessions) | `dream` (config → hours → sessions → lock) | curator (idle-triggered, `interval_hours`) |
| Sub-agents receive a task string, return a summary; context never inherited | depth = 1, summary only | `SubagentOwner`, structured completion | `role="leaf"`, isolated context |
| Capability restriction by role, derived from a tool property | Explore / Plan / Bash / general-purpose | `SubagentCapabilityMode` × tool `kind` | leaf vs orchestrator, toolsets |
| Skills as on-demand `SKILL.md` with frontmatter, distinct from always-on rules | `.claude/skills/` | `.grok/skills/` + vendor dirs | `~/.hermes/skills/` + hub |
| Hard byte/line budgets on model-visible artifacts | 200 lines / 25 KB / 200 files | 60-char skill listing budget, 256 KB diff cap | 60-char descriptions, 15 KB skills |
| Anchored edit with a three-valued result | exact → fuzzy+warn → error | `Found` / `Ambiguous` / `NotFound` | `expected_occurrences` |
| Deferred activation of prompt-affecting changes | next session | `/coding` flip deferred | `--now` opt-in, default deferred |
| Cost-ordered gates | — | regex → evaluator → panel | pytest → subset → full → coherence |

### 10.2 Where they diverge — the live decisions

| Question | Claude Code | Grok Build | Hermes | Our current position |
| :--- | :--- | :--- | :--- | :--- |
| **Orchestration** | explicit **no DAG**, plain while-loop | Rhai **scripts** with phases and pauses | plain loop + delegation | **DAG** (A-024 / ADR-0018) — the outlier |
| **Retrieval** | grep/glob only; **built embeddings, removed them** | tree-sitter symbolic graph, no embeddings | hybrid FTS5 + sqlite-vec + MMR | index port, dense deferred behind ADR-0014 |
| **Completion verification** | model decides `end_turn` | adversarial skeptic panel | passive evidence ledger + nudge | tri-state gate |
| **Compaction** | auto at threshold + micro-compact | background prefire two-pass | micro-compaction, **off by default** | exchange-granular |
| **Perimeter** | OS sandbox + rules + hooks; dangerous patterns via **model judgement** | 20k lines of shell analysis + sandbox | command guards + approval | sandbox is the perimeter (ADR-0006) |
| **Self-improvement** | Auto Dream (memory only) | none | curator + DSPy/GEPA meta-loop | bounded RHI at M5 |

Two things stand out from that table.

**On retrieval, we are between two camps and should say which one we are in.** Claude Code and Grok
Build both run symbolic search only, and Claude Code actively removed embeddings after
benchmarking. Hermes runs hybrid. Our ADR-0014 recall@10 trigger is the right *shape* of answer —
a measurement that decides — but the evidence now leans harder toward "symbolic first" than it did
when that ADR was written, and the trigger threshold deserves a second look.

**On orchestration, we are the outlier.** That is not automatically wrong — none of the three
targets ≥8h unattended the way we do, and Grok Build's Rhai workflow scripts are arguably closer to
our DAG than to Claude Code's bare loop. But being the only one of four designs with a DAG is worth
either a strong justification or an ablation, which is what P62 proposes.

---

## 11. What not to copy, and where this corpus is weak

**The corpus is documentation, not code.** Everything here is at best a description of behaviour.
Nothing in it should be treated with the confidence of the Grok Build or Hermes teardowns, where I
was reading the implementation. The guide's own tiering is the appropriate lens, and the numbers
most useful to us — the Tool Search accuracy gains, the adoption data — are Anthropic marketing-
adjacent publications reported by a community author. They are probably directionally right and
they are not independently verified.

**`claude-code-analysis` is stale and provenance-tainted.** §0 covers this. The specific risk is
subtle: it is well-written and confident, which makes it easy to cite. Sixteen months in this field
is several architectures ago, and the artifact class is the one L2 deferred.

**The guide has a promotional layer.** It is a community project with a landing page, a quiz, a
paid-adjacent ecosystem, badges, and an "Ask Zread" widget. Sections like the adoption timeline
("Pilot 60–70% success, Production 85–90%") are cited to a vendor trends report and are not
measurements in any sense we would accept in our own documents. Read the mechanism sections; be
sceptical of the outcome sections.

**Do not import the auto-compaction threshold as a number.** The guide lists five sources reporting
~75%, 1–5% remaining, 92%, and 95%. That spread is the honest answer: nobody outside Anthropic
knows, and it has changed across versions. Our own threshold must come from our own measurement,
which is what the MECW and 70%-cliff findings actually support.

**Do not adopt "trust the model" as a default at Tier 0.** The philosophy is Tier 1 and it is
coherent — for frontier models with a human in the loop. Our first measurements will run on free
local models with no human, which is the regime where scaffolding pays most. The right reading is
that scaffolding value is inversely proportional to model capability, which means our scaffold
should be designed to be *removable* as the model tier rises — an argument for keeping every
mechanism behind an ablation flag rather than for not building it.

---

## 12. Open questions this teardown raises

1. **Does the Tech Lead accept `claude-code-analysis` as a usable reference at all?** §0 recommends
   shape-only. This is a policy call under L2 and I do not think it should be made implicitly by
   whoever next cites the document.
2. **Do we run the scaffolding thesis as an ablation (P62), and if so at which milestone?** It is
   cheap at M1b/M2 and expensive to retrofit once the DAG has consumers.
3. **Does ADR-0014's recall@10 trigger still sit at the right threshold**, given that two of three
   references run symbolic-only and one of them removed embeddings after benchmarking?
4. **Where does Tool Search land on the roadmap** — M3 feature, early ablation arm, or not at all?
   The +25-point accuracy result on the weaker model is the fact that should decide this, and it is
   testable on our own ladder.
5. **Do we occupy the role-based model selection gap?** Agent Teams runs one model for every agent
   and the community is asking for lead-Opus / worker-Sonnet / test-Haiku. Our `ModelProvider` port
   and Grok Build's per-skeptic model pool both make this natural. It is a differentiator that costs
   us little and that the market leader has not shipped.

---

## 13. Provenance

Everything in this document was derived by reading `src/claude_refs/`. Two corpora with different
licences and different reliability: `claude-code-analysis` (MIT, unofficial reverse-engineering,
2025-03-31) and `claude-code-ultimate-guide` (CC BY-SA 4.0, community documentation with source
tiering, v3.41.1, 2026-07-29). Neither is an Anthropic publication, though the guide cites and
tracks Anthropic's official documentation and engineering posts, and marks which claims come from
them.

No code was copied, adapted, or transcribed — the corpus contains almost none. Quoted fragments are
short excerpts reproduced to describe a mechanism, attributed inline. Where a mechanism is
recommended for consideration, the recommendation is of the *concept*.

Claude Code is a product of Anthropic; both corpora carry disclaimers that they are unaffiliated.
Our standing policy L2 — study concepts and published theory, never copy, and require a
KPI-grounded rationale before converging on a competitor's design — applies here more sharply than
to the other references, for the reason given in §0.

**Cross-references:** [`rewrite_v300_grokbuild_teardown.md`](rewrite_v300_grokbuild_teardown.md) ·
[`rewrite_v300_grokbuild_proposals.md`](rewrite_v300_grokbuild_proposals.md) ·
[`rewrite_v300_hermes_teardown.md`](rewrite_v300_hermes_teardown.md) ·
[`rewrite_v300_reference_teardowns.md`](../../rationale/rewrite/rewrite_v300_reference_teardowns.md) ·
[`rewrite_v300_contexto_memoria.md`](../../rationale/rewrite/rewrite_v300_contexto_memoria.md) ·
[`rewrite_v300_measurement_strategy.md`](../../rationale/rewrite/rewrite_v300_measurement_strategy.md) ·
[`rewrite_v300_autonomia_agi.md`](../../rationale/rewrite/rewrite_v300_autonomia_agi.md) ·
[`rewrite_v300_seguranca_sandbox.md`](../../rationale/rewrite/rewrite_v300_seguranca_sandbox.md) ·
[`rewrite_v300_mecanismo_edicao.md`](../../rationale/rewrite/rewrite_v300_mecanismo_edicao.md) ·
[`rewrite_v300_decisoes_adr.md`](../../rationale/rewrite/rewrite_v300_decisoes_adr.md) ·
[`rewrite_v300_decisoes_runtime.md`](../../rationale/rewrite/rewrite_v300_decisoes_runtime.md)
