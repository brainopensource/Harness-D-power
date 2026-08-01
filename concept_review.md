---
status: rationale
updated: 2026-08-01
retrieval: excluded
---

# SAGIHA — Concept & Architecture Review, Looking Toward v3

| Field | Value |
| :--- | :--- |
| **Document ID** | `concept_review` |
| **Companion to** | `Harness_LLM_orchestrator_project_review.md` (defect-level audit of v2-S0…S6) |
| **Purpose** | What we would do *differently in concept* — architecture, tech stack, design decisions, workflow — for a v3, once v2 lands |
| **Inputs** | `docs/rationale/reference/harness_research_2026_briefing.md`, `docs/rationale/reviews/agi_evolution_path.md`, `docs/rationale/reviews/next_gen_architecture_specs.md`, plus first-hand reading of `src/sagiha/` at `eae4c22` |
| **Status** | Thinking document. **Nothing here is a v2 work item.** Nothing here should be started before `Harness_LLM_orchestrator_project_review.md §7 P0` is green |

> **Framing.** This is not a list of features v2 lacks — the roadmap already covers those. It is a
> critique of *choices*, including several that were correct at the time and are worth revisiting
> only because v2 taught us what they cost. Where v2 got something right, this document says so
> and argues for keeping it, because the most expensive v3 mistake would be rewriting the parts
> that work.

---

# Chapter 1 — What v2 Got Right and v3 Must Not Relitigate

Before criticizing anything, it is worth being precise about what this codebase does better than
most harnesses I have read, because these are the load-bearing bets and they paid off.

### 1.1 The capability-grant choke point

One function — `kernel/dispatch.py:dispatch()` — is the only path from agent intent to real
effect, and it does authorization, unconditional point-of-effect grant verification, lease
acquisition, and outcome recording in a fixed order. Most harnesses scatter permission checks
across tool handlers, where they rot. This design makes "can the agent do X" a question with
exactly one answer site. **Keep it, unchanged, in v3.**

### 1.2 `None` is not `False`, and `None` never passes

The `GateReport` tri-state (`True` / `False` / `None` = could-not-evaluate, never a pass) is the
single best idea in the tree. It converts "we didn't measure this" from an invisible default into
a visible, propagating fact that fails runs closed. The same discipline shows up in
`e0/statistics.py` (`beats_noise_floor=None` when no floor was supplied) and in
`export/eligibility.py` (`admitted is True`, not truthiness). **This should be a stated invariant
of v3, not an emergent habit** — see §3.1, where its *absence* in one place caused the audit's
worst defect.

### 1.3 Refuse-at-load configuration

`domain/config.py` refuses to construct an insecure system: `subprocess` + `autonomous` is
rejected, `autonomous` without a container is rejected, `search.enabled` with judge == executor is
rejected. Security properties enforced by a Pydantic validator at composition time cannot drift,
cannot be forgotten by a caller, and cost nothing at runtime. **Keep and extend** — every
"you must not do X" in the docs should become a `model_validator`.

### 1.4 Boring storage

SQLite (+ FTS5) for everything, Tree-sitter for parsing, no daemons, no Redis, no Neo4j, no vector
store. The `harness_research_2026_briefing.md` stack table recommends LanceDB, Neo4j, DuckDB, Ray,
Temporal, and LangGraph. v2 chose against nearly all of it and was right: every one of those is a
process to supervise, a version to pin, and a failure mode to debug, in exchange for capability
this system has not yet earned the right to need. **v3 should keep the "boring components until a
measured trigger fires" rule and should keep resisting the briefing's stack.**

### 1.5 Deliberate, documented deviations

The 18-line comment at `dispatch.py:127-144` explaining why the `<untrusted-data>` envelope lives
in the assembler rather than at the choke point — because wrapping at dispatch corrupted
`GateEvaluator`'s `git diff --numstat` parse and silently re-broke three gates — is exemplary. The
codebase repeatedly explains *why* rather than *what*. **This is a cultural asset. Protect it.**

---

# Chapter 2 — Concept-Level Critiques

These are the things I would genuinely do differently, ordered by how much they cost.

## 2.1 The measurement infrastructure was sequenced last, and it inverted the doctrine

**What happened.** The project's founding rule is *"no claim without a benchmark, no accept/reject
without an A/A noise floor."* Excellent rule. But the benchmark suite was scheduled into **v2-S4**,
attempted, yielded **0 valid tasks out of 23**, and was deferred. As of S6 closeout,
`benchmarks/definitions/` does not exist and `noise-floor.md` is a template. Two capabilities
(Best-of-N, retrieval) shipped mechanism-complete and default-off *because* they could not be
measured.

**Why this is a concept flaw, not a scheduling accident.** The doctrine was designed as a
forcing function — "you may not ship unmeasured capability." What it actually became was a
*permission structure for shipping unmeasured capability with the safety off*: `enabled=false` is
honest, but it means seven sprints produced no evidence that any of it helps. The honest-negative
default is the correct local decision and a bad global outcome. Worse, the C-1 defect
(silent FTS5 query failure) survived an entire sprint precisely because nothing ever *used*
retrieval for real — an unmeasured subsystem is also an unexercised one.

**What v3 should do.** Invert the order. **The evaluation suite is Sprint 0, before the first
adapter.** Concretely:

- A ≥30-task pinned suite with reproducible base commits and test suites is a *prerequisite for
  the repo existing*, not a deliverable. Import it (SWE-bench Lite subset, or a synthetic
  generator over the repo's own history) rather than harvesting — the 0/23 harvest result says
  harvesting from one local repo does not work and should not have been the plan.
- The A/A noise floor is computed on day one against a no-op harness. You cannot know what a
  delta means until you know what zero looks like.
- **Every capability PR reports its delta against the floor in the PR body, automatically.** Not
  "at the sprint exit gate" — per PR. A gate that fires once per sprint gets deferred; a gate that
  fires per PR cannot be.
- Corollary: if a capability cannot be measured, that is evidence the *suite* is inadequate, and
  fixing the suite becomes the work. v2 treated unmeasurability as a property of the capability.

## 2.2 The documentation strategy treated symptoms

**What happened.** The tree holds **178,742 words** of documentation against roughly 135 source
files. v2-S0 addressed this by inventing a word budget (≤15,000 "normative" words) and a
`status:` taxonomy that demotes everything else to `rationale`/`historical` and excludes it from
retrieval. The budget is currently exceeded by 183 words, 8 documents escape it entirely by
carrying no tag at all, and `check_links.py` reports **106 dead relative links** created by the
very reorganisation that the budget motivated.

**Why this is a concept flaw.** The budget does not reduce documentation mass — it reduces the
*labelled* mass. 163,000 words still exist, still drift, still get read by humans, and still break
links when moved. The mechanism treats an output metric (words tagged normative) rather than the
cause (prose is the default artifact for every decision, and prose has no compiler).

**What v3 should do.**

- **Make ADRs the only durable prose.** They are already exempt from the budget and they are
  already the highest-signal documents in the tree. Everything else is either (a) generated or
  (b) deleted.
- **Generate the reference layer from code.** The event catalog is already generated and checked
  (`gen_event_catalog.py --check` — the one docs gate that is green, which is not a coincidence).
  Extend that pattern: port surface, tool schemas, config schema, and the CLI reference should all
  be generated from `src/` and verified with `--check` in CI. A generated doc cannot drift, cannot
  break its own links, and costs zero words of budget.
- **Kill the `status:` taxonomy in favor of directory placement.** `docs/adr/` is normative,
  `docs/generated/` is generated, `docs/notes/` is excluded — enforced by path, not by a
  frontmatter field that 8 files simply omitted. Metadata that can be forgotten will be.
- **No absolute `file:///home/...` links, ever.** They are unresolvable for every reader but the
  author, and they make up a large share of the 106 broken links.

## 2.3 "Honest instruments" was applied as a checklist (H1–H4), not as an invariant

**What happened.** v2-S1 fixed four named findings and did it well. But C-1 — `FTS5Indexer.neighbors`
catching `sqlite3.OperationalError` and returning `[]` — is the *same class of defect* as H1
(a fabricated result that looks measured), introduced five sprints later, in new code, by the
same team, and caught by nobody. Two independent prior reviews also missed it.

**Why.** H1–H4 were enumerated instances. Nothing generalized them into a rule that new code is
checked against. The team fixed the four known lies and had no mechanism to prevent the fifth.

**What v3 should do.** Promote it to an enforced invariant with three teeth:

1. **A stated rule:** *"In any code path that produces a value a decision is made on, an exception
   is either propagated or converted to an explicit `None`/`Unknown` sentinel. It is never
   converted to a plausible-looking success value — no empty list, no zero, no empty string."*
2. **A lint rule:** ban bare `except X: return <literal>` in `adapters/`, `outer_loop/evaluator/`,
   and `e0/`. Ruff can express most of this; a small AST check in `scripts/` can express the rest.
   This is cheap and would have caught C-1 the day it was written.
3. **A type-level nudge:** make measurement-producing functions return
   `Result[T] = T | Unmeasured(reason)` rather than `T`, so the caller cannot silently treat
   "couldn't compute" as "computed nothing". `GateReport` already does this by convention with
   `bool | None`; v3 should do it with a type.

## 2.4 The hexagon had no automated conformance edge

**What happened.** 17 Protocols, 16 port modules, a `test_port_shape.py` that checks ports are
async / serializable / grant-free — and **nothing that asserts any adapter satisfies any port.**
`FTS5Indexer` diverged from `Indexer` and pytest stayed green; only pyright noticed, and STATUS
was reporting pyright from memory.

**Why this is conceptual.** The whole justification for ports-and-adapters is substitutability.
If substitutability is never tested, the ports are documentation with extra syntax. v2 paid the
full cost of the hexagon (17 Protocol definitions, indirection at every boundary,
`composition.py`) while collecting only part of the benefit.

**What v3 should do.**

- **Generate the conformance suite from the Protocol.** For each port, a parametrized test that
  takes every registered adapter and asserts (a) static assignability, (b) the behavioral
  contract — the `test_workspace_conformance.py` pattern, which v2 already got right for
  `Workspace` and then did not replicate to any other port. That one file is the model; the
  problem is that it is the only one of its kind.
- **Enforce port rent mechanically.** ADR-0019 says a port with no non-test adapter for two blocks
  is demoted and listed for deletion. That is a good rule with no enforcement. A CI check that
  maps ports → adapters and fails on unpaid rent would keep the surface honest — and would
  currently flag several ports (`advisory`, `lsp`, `meta_improver`, `toolchain`) that exist as
  contracts with no implementation.
- **Reconsider whether 17 ports is the right number at all.** A port earns its keep when there are
  two real implementations or a genuine remoting boundary. Several of these have neither and were
  created speculatively. v3 should start with perhaps six real ports and *promote* modules to
  ports when a second implementation actually appears — the opposite of v2's consolidate-downward
  approach, which still left contracts with zero adapters.

## 2.5 Seed-only Layer-6 retrieval solved the cache problem and skipped the quality problem

**What happened.** ADR-0021 rules retrieval seed-only: computed once at task start, frozen,
never refreshed. The reasoning is genuinely elegant — it makes mid-task cache invalidation a
single class of event (compaction), which makes cache hit rate a clean regression signal, and
it is what later makes interrupt-and-steer cheap (`agi_evolution_path.md §4.3`). The
implementation enforces it structurally: `retrieval_seed` is a constructor-only parameter with no
post-construction write surface. Good engineering.

**What was skipped.** *What goes in the seed.* The implementation is: take the raw natural-language
goal, hand it to SQLite FTS5 `MATCH`, take the top-k BM25 hits, paste the raw AST spans into
Layer 6. Every step of that is questionable:

- A natural-language goal is not a lexical query (this is C-1, and C-1 is a symptom, not the
  disease — even with escaping, BM25 over prose intent is a weak retriever).
- The chunks carry no path/symbol/signature envelope (M-5), so they lack standalone context.
- The code graph — the deterministic, high-precision structure the team *already built* — is not
  consulted for seeding at all.

**What v3 should do.** Separate the two questions the seed conflates:

1. **Seed from structure, not from prose.** If the goal mentions files or symbols, resolve them
   through the code graph and seed their definitions plus one hop of `impacted_by`. This is
   deterministic, cache-stable, high-precision, and needs no query understanding. It is also
   exactly what a human engineer opens first.
2. **Leave semantic search to the agent, in the tail.** The model is a far better query formulator
   than BM25-over-intent, and agentic retrieval is already the ruled-in mechanism for mid-task
   information. Then the seed's job shrinks to "the obvious files", which structure answers well.
3. **Consider seeding nothing by default.** Worth testing honestly: a seed of mediocre chunks costs
   real tokens on every turn of every run. The ablation "structure-seed vs prose-seed vs no seed"
   is a one-day experiment once the suite from §2.1 exists, and it may well retire a whole
   subsystem. v3 should *want* that outcome.

## 2.6 Everything is shaped around one task

**What happened.** `TaskSpec` → `RunLoop` → `GateReport` is the spine, and it is a single-task
spine. The multi-story layer (`StoryDAG`, `IntegrationStep`) is deferred to v2-S7; the
mission layer (`MissionSpec`, hibernation, `FleetGovernor`) is deferred to Conductor C0+ and
placed in a *separate package* above the engine.

**The critique is narrow, because the layering decision is right.** `agi_evolution_path.md §2.1`
argues the Conductor must own time/attention/knowledge and own no tools, no shell, no grants —
so it is structurally incapable of violating the security model. That is correct and should
survive to v3.

**What v3 should do differently is smaller and concrete:** make the *resumability and budget
primitives* mission-shaped from day one, even while only one task runs.

- `FrozenRunState` already survives `kill -9` — that is the hard part, and it is done. But
  budget is `budget_remaining_usd` on a single `RunContext`. A mission needs a budget *slice*
  minted from a parent envelope, and retrofitting hierarchical budgets into a flat field is
  exactly the kind of change that touches every call site.
- Similarly, `run_id` is flat. A `(mission_id, story_id, run_id)` triple costs nothing now and is
  painful to introduce later, because it changes every event, every trajectory row, and every
  index.
- Nothing else about the Conductor needs to exist in v3 core. Just the identifiers and the budget
  tree, so the seam is free when the layer arrives.

## 2.7 Sprint closeout was a human editing a markdown table

**What happened.** `docs/STATUS.md` is the declared SSOT for implementation truth. It claims
"Type check — 0 errors" (actual: 3), "Lint — clean" (actual: 34 + 17 format), and a test count
whose arithmetic is wrong. Meanwhile `development_plan_v2.md` holds 18 unchecked boxes for work
that was delivered. Two prior reviews disagreed with each other about the test count because they
ran on hosts with and without Podman and neither said so.

**Why this is conceptual.** This project's entire thesis is that instruments must not lie. It
built excellent instruments for the *agent's* work and then reported on its *own* work from
memory. The failure mode it spent a sprint eliminating in code is present in its dashboard.

**What v3 should do.**

- **`scripts/verify.sh` is the only way STATUS changes.** It runs all gates, captures host facts
  (Podman present? which Python?), and *writes* the regression table. A human editing that table
  is a process bug.
- **Sprint closeout is a script exit code**, not a judgment. "S0 closed" must be false while S0's
  own gates are red — which is exactly the state the tree has been in.
- **Report host-conditional numbers as such.** "332 passed (321 + 11 Podman-gated; Podman 5.8.4
  present)" is a fact. "321 passed" is a fact about a different machine. The ambiguity produced
  two contradictory audit reports and cost real review time.

## 2.8 The self-improvement claim is louder than the mechanism

`next_gen_architecture_specs.md §2.3` already did the honest thing — it split the outer loop into
Tier A (prompt/config regression CI, cheap), Tier B (trace mining, near-free), and Tier C
(mutation search, dormant behind a funding trigger) — and correctly identified Tier A as "90% of
self-improvement's defensive value at CI cost." That is right.

But the tree still carries a `MetaImprover` port with no adapter, an `outer_loop/` package, and
prose across several documents about recursive harness improvement. Meanwhile **Tier A is not
implemented**: there is no prompt-regression CI job, because there is no suite (§2.1).

**What v3 should do:** ship Tier A and *only* Tier A, name it "prompt regression testing" rather
than "recursive harness improvement", delete the `MetaImprover` port until something implements
it, and move all RHI prose to a single ADR. The system will have a real, working, useful
self-improvement mechanism and a claim that exactly matches it. The current arrangement has the
claim without the mechanism, which is the thing this project says it does not do.

## 2.9 Missing from the concept entirely: subagents and skills

v2 has no subagent mechanism and no skill library. `agi_evolution_path.md §6` specifies skills
carefully — namespaced behind one `use_skill` tool to protect the 20-tool budget, gated like an
RHI mutation because auto-registered agent-authored code *is* self-modification, with expiry on
code-graph invalidation. That analysis is good and should survive.

But the *scheduling* question deserves revisiting. Contemporary harnesses lean heavily on
subagents for context isolation — a subagent burns its own window on a search and returns a
paragraph — and this system has an unusually cheap path to that: `spawn_subagent` is the
degenerate local case of the `Orchestrator` port (`next_gen_architecture_specs.md §3.2`), and
kernels are already "a composition-root call over a worktree". v3 should consider subagents a
**core context-management primitive available early**, not a multi-agent feature deferred behind
A2A. Context window pressure is the binding constraint on long runs, and compaction is a lossy
answer to it; delegation is a lossless one.

Skills, by contrast, should stay deferred exactly as specified — they are a capability-surface
mutation and the gating analysis is correct.

## 2.10 Smaller design notes worth carrying forward

- **`bool | None` should be a type, not a convention.** See §2.3.
- **Two digests on `AssembledPrompt`** (`prefix_digest` vs `stable_prefix_digest`) is a genuinely
  clever instrument — the comment explaining why conflating them hides the signal is the kind of
  thinking v3 needs more of, applied to more metrics.
- **The PURE-argv allowlist placed in `kernel/policy/`** so that the existing TCB import contract
  makes it agent-unwritable *for free* — no new gate, no new CI job — is the best example in the
  tree of getting a security property by placement rather than by mechanism. Look for more of
  these.
- **`del max_chunk_tokens  # reserved`** is an anti-pattern worth naming: a config field accepted
  and discarded. v3 rule — a config field either changes behavior or does not exist. The
  refuse-at-load validator can enforce it (`assert` every field is read by some consumer at
  composition).
- **`SKIP_DIRS` duplicated four times and `_module_name` implemented two incompatible ways** in a
  codebase this disciplined suggests the indexer/graph pair was built by parallel efforts without
  a shared vocabulary module. v3: a `walk.py` (or equivalent shared-vocabulary module) should
  exist *before* the second consumer, not after the fourth.

---

# Chapter 3 — Tech Stack Reassessment

The `harness_research_2026_briefing.md` stack table is ambitious. Having now read what v2 actually
needed, here is my assessment of each recommendation.

| Component | Briefing recommends | v2 chose | v3 recommendation | Reasoning |
| :--- | :--- | :--- | :--- | :--- |
| **Orchestration** | LangGraph | Native `RunLoop` | **Keep native** | ADR-0018 was right. LangGraph's state graph buys checkpointing that `FrozenRunState` already provides, at the cost of a framework between you and your own control flow. The loop is ~500 lines and fully owned |
| **Durability** | Temporal.io | `FrozenRunState` + SQLite | **Keep native; steal the vocabulary** | Temporal is a server to operate. But v2 has effectively reinvented a narrow event-sourced replay, and would benefit from Temporal's *concepts* — explicit determinism boundaries, replay-safety rules for side effects — without the deployment |
| **Cluster** | Ray | Nothing (worktrees + asyncio) | **Defer indefinitely** | Ray earns its keep for mass parallel eval. Until a suite exists (§2.1) there is nothing to parallelize. Worktrees + process pool covers Best-of-N |
| **Tool protocol** | MCP | Stub, S7 | **Adopt in v3 for *external* tools only** | MCP is the right ecosystem bet, but builtins should stay native — routing `read_file` through JSON-RPC buys nothing and costs latency and a trust boundary |
| **Agent protocol** | A2A | Contract fixed, unimplemented | **Keep deferred** | The trigger (a genuinely remote peer) has not fired. Fixing the contract shape early was the right call |
| **Workspace isolation** | Git worktrees | Git worktrees | **Keep** | Zero-copy, instant, no daemon. Best call in the stack |
| **Sandbox** | Docker/Podman | Rootless Podman + CONNECT proxy | **Keep** | The `--network=none` + unix-socket proxy design is stronger than a bridge network with rules, because there is no host stack to escape to |
| **Vector store** | LanceDB / sqlite-vec | None (ADR-0014 defers) | **Keep deferred — and reframe the trigger** | The trigger is "recall@10 misses". But per §2.5, lexical retrieval was never given a fair test (bad query construction, no chunk envelope, no graph seeding). Fix those *first*, or the dense tier gets adopted to paper over a chunking bug |
| **Knowledge graph** | Neo4j / NetworkX | SQLite + Tree-sitter | **Keep SQLite** | The graph is a rebuildable cache, not a system of record (ADR-0011). A cache does not need a graph database |
| **Telemetry OLAP** | DuckDB | SQLite trajectory store | **Add DuckDB, read-only, later** | The one briefing recommendation I would genuinely take — but as an *analysis* tool over exported trajectories, never in the write path. Zero operational cost, real analytical gain |
| **Eval framework** | Inspect AI / SWE-bench | Native E0 | **Keep native E0; import SWE-bench *data*** | `e0/statistics.py` (exact McNemar, seeded bootstrap, Holm) is better than what most teams get from a framework, and it is 300 lines of stdlib. But stop trying to *harvest* tasks (0/23) — import a proven dataset |
| **Local ML (AOI)** | XGBoost / ONNX | Empty `aoi/` package | **Keep empty until labels exist** | Cold-start doctrine. A surrogate reward model needs thousands of labeled trajectories; the tree has none. `aoi/` should carry a docstring saying exactly that |
| **Red-teaming** | Promptfoo | Injection canary tests | **Adopt Promptfoo** | The one clear gap. Prompt-injection resistance is currently tested by a handful of hand-written canaries. Declarative YAML red-teaming is cheap and this system's threat model (T1/T7) makes it directly relevant |
| **Language** | Python 3.12+ | Python 3.13 | **Keep** | Right ecosystem. The indexing walk will eventually need concurrency, but `anyio.to_thread` already covers it |

**Net:** v2's stack choices were better than the briefing's on almost every axis, because the
briefing optimizes for a system operating at a scale this one has not reached. The two additions
worth making are **DuckDB for offline trajectory analysis** and **Promptfoo for injection CI**.
Everything else stays deferred behind its measured trigger.

---

# Chapter 4 — What a v3 Would Look Like

Not a rewrite. A resequencing, with roughly five structural changes.

### 4.1 Sequencing

```
v2 actual:   docs → honesty → ports → context → E0+search → sandbox → retrieval
                                                    ▲
                                    measurement arrives 5th, then fails, then defers

v3 proposed: suite+floor → perimeter → honesty-as-invariant → choke point → context
             → ONE capability, measured → next capability, measured → …
                ▲                            ▲
     nothing ships before there is       every capability arrives with its delta
     a number to compare against         in the PR body
```

The two moves: **evaluation first** (§2.1), and **the sandbox early** rather than at S5 — the
perimeter is the precondition for the autonomy the whole design targets, and running six sprints
of development against a `subprocess` runtime means the container path is the *less*-exercised one
at closeout, which is backwards.

### 4.2 The five structural changes

1. **`Measured[T]` as a first-class type.** Replaces the `bool | None` convention. Any value a
   decision is made on carries its provenance: computed, or unmeasured-with-reason. The type
   system then prevents the C-1 class of defect rather than a lint rule catching it. (§2.3)
2. **Generated documentation layer.** ADRs are the only hand-written durable prose; ports, events,
   tool schemas, config schema, and CLI reference are generated from `src/` and `--check`ed in CI.
   Target: normative hand-written prose under 5,000 words, and no budget mechanism needed because
   there is nothing to budget. (§2.2)
3. **Conformance-generated port tests + enforced port rent.** Every port gets a generated
   assignability + behavioral suite over its registered adapters; a port with no adapter fails CI.
   Start with ~6 ports and promote, rather than declaring 17 and hoping. (§2.4)
4. **Structure-first retrieval.** Seed Layer 6 from the code graph (resolved symbols + one hop),
   not from BM25-over-prose. Semantic search moves entirely to agentic tail calls. Test
   "no seed at all" as a serious baseline. (§2.5)
5. **Mission-shaped identifiers and budgets from day one.** `(mission_id, story_id, run_id)` and a
   budget tree, even while only one task ever runs. Costs nothing now; the retrofit is expensive.
   Nothing else of the Conductor moves into core. (§2.6)

### 4.3 Workflow changes

- **`scripts/verify.sh` writes STATUS.** Humans do not edit the regression table. (§2.7)
- **Sprint closeout is an exit code.** A sprint whose own gates are red is not closed.
- **Every capability PR posts its measured delta vs the A/A floor.** Per PR, not per sprint.
- **A "no plausible fabrication" lint** over `adapters/`, `outer_loop/evaluator/`, `e0/`. (§2.3)
- **Report host-conditional test counts with their host facts.** (§2.7)

---

# Chapter 5 — Open Questions for v3

These are genuine uncertainties, not rhetorical ones. Each would change the design.

1. **Does retrieval help at all in a repo with a good `AGENTS.md`?** The `sagiha init` cold-start
   generator and the retrieval subsystem may be substitutes rather than complements. If a
   well-generated Layer-4 orientation file captures most of the value, the entire indexer +
   code-graph + retrieval stack is a large, expensive subsystem earning very little. This is
   testable in a day once the suite exists, and the answer should be allowed to be "no".

2. **Is Best-of-N worth it versus one better model call?** ADR-0005 chose BoN over MCTS on cost
   grounds and was right. But the unexamined comparison is BoN-at-N=3-on-a-workhorse versus
   N=1-on-a-frontier-model at similar spend. Frontier model quality has moved a great deal since
   that ADR; the arithmetic may have inverted.

3. **Is compaction or delegation the right answer to context pressure?** v2 built an
   exchange-granular compactor (good). Subagents are lossless where compaction is lossy, and this
   architecture makes them unusually cheap (§2.9). Which one carries long runs is an empirical
   question nobody has asked.

4. **Should the taint model be binary?** It is currently monotonic and boolean, which is cheap and
   fail-closed — the right v1. But `run_command` is exempt by necessity (m-9), which means the
   binary model already needed an escape hatch on its first contact with reality. A
   per-capability taint (this run may not write, but may read) might be both stricter and more
   usable.

5. **Is the 17-port hexagon paying for itself?** Several ports have zero adapters. The indirection
   is real and constant; the substitutability benefit has not yet been collected once. v3 should be
   willing to conclude "fewer ports, more direct calls, promote on the second implementation."

6. **What is the actual unit of work?** v2 says "task." The Conductor says "mission → epic → story
   → task." Real engineering work arrives as a poorly-specified request that decomposes
   unpredictably and gets revised mid-flight. Whether a *static* DAG decomposition is the right
   model — versus a continuously-revised plan artifact — is the biggest open question above the
   execution loop, and `agi_evolution_path.md §4.2`'s "REPLAN revises the DAG, never restarts it"
   is a partial answer that has never been run.

---

## Closing position

v2 built the hard, unglamorous parts correctly: a real security choke point, real gates that
report `None` instead of lying, real statistics, and a real container perimeter. Those are the
parts that are difficult to retrofit and they are done.

What it did not build is the thing that tells anyone whether any of it works. Seven sprints
produced a mechanism-complete harness with **zero** measured capability claims, two flagship
features shipped switched off, and — in the one subsystem furthest from measurement — a retrieval
path that silently returns nothing and would have been caught in an hour by a single real query.

The one-sentence lesson for v3: **this project's founding rule was "no claim without a benchmark,"
and the way to honor it is to build the benchmark first, because a rule that only ever forbids
claims eventually stops producing evidence.**

---

*End of `concept_review.md`. Companion defect-level audit: `Harness_LLM_orchestrator_project_review.md`.*
