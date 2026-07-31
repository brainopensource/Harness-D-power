---
status: rationale
updated: 2026-07-30
retrieval: excluded
---
# ⚡ SAGIHA — The Pitch

> **A meta-loop harness: infrastructure that turns a frontier LLM into an autonomous software
> engineer whose work you can contain, replay, and measure — built as swappable parts so a community
> can improve any one of them without forking the whole.**

---

## 1. What a Meta-Loop Harness Is

A state-of-the-art harness is not a smarter prompt. It is the infrastructure that turns a text
predictor into something whose work you can **verify**.

The LLM is the brain and nothing else. It holds no tool references, opens no files, and runs no
commands. Everything it wants to do arrives as an *intent* that the harness decides whether to
execute. That inversion is the whole idea, and it is what separates a harness from a prompt wrapper.

Being *meta-loop* means the system is built from nested loops, each one operating on the output of
the one below it:

| Loop | Operates on | Asks |
| :--- | :--- | :--- |
| **Inner loop** (DMARTIC) | One task | *Did this change work?* |
| **Process loop** (Workflow DAG) | One goal | *Were these the right tasks?* |
| **Outer loop** (RHI) | Thousands of past runs | *Is the harness itself getting better?* |

Most agent frameworks stop at the first. SAGIHA's thesis is that the second and third are where the
compounding lives — and that neither is buildable until you can *measure*, which is why measurement
is infrastructure here rather than an afterthought.

The inversion buys four properties no prompt wrapper can have:

* **Containment** — every effect requires a scoped, expiring capability grant, verified at exactly
  one choke point (`kernel/dispatch.py`). Not a permission dialog someone will disable on hour four
  of a six-hour run; a structural property.
* **Replay** — every model call is recorded to a cassette, so CI reruns an entire session
  byte-for-byte with zero network I/O and zero API cost.
* **Measurement** — a standalone evaluation harness with an **A/A noise floor**, so *"this change
  helped"* becomes a number instead of a vibe. Run the same config twice, measure the spread from
  pure stochasticity, and refuse to celebrate anything inside it.
* **Honest grading** — tests are injected read-only from the base commit, so a candidate physically
  cannot edit its own grader.

Take any one away and the others degrade. Without replay, a measurement isn't reproducible. Without
measurement, self-improvement optimizes into randomness. Without containment, none of it is safe to
run unattended — and unattended long-horizon work is the entire point.

---

## 2. The Environment — Giving the Brain a Body

Around the brain sits a deliberately unglamorous body:

* **Perception** — Tree-sitter AST queries (`callers_of`, `impacted_by`) plus LSP diagnostics.
  Deterministic structural facts, not embeddings guessing at relevance. Two runs produce the same
  graph, which is precisely what an LLM-extracted knowledge graph cannot promise.
* **Motor control** — a small set of bounded tools with paginated output and structured truncation,
  so nothing dumps 40,000 lines into the context window. The model always sees structure; large
  payloads go to a handle.
* **Workspace** — an ephemeral git worktree per attempt. Failed work is *discarded*, not cleaned up.
* **Memory, split in two** — code facts derived from the AST; *learned* facts in a linked
  Obsidian-style knowledge net with neighborhood and backlink traversal. The split matters: mixing
  them lets one hallucinated edge quietly poison a dependency graph.
* **Persistence** — one SQLite file. No Neo4j, no Qdrant, no vector daemon, nothing to operate.

The bar for adding anything here is that it earns its operational cost. Most of the machinery a
modern agent stack ships was rejected on exactly that test.

---

## 3. The Workflow — A Senior Engineer's Day, Not a Chatbot's Turn

A prompt becomes a spec. The spec decomposes into stories with **disjoint file sets**, so they can
run in parallel without colliding. Each story enters the inner loop:

```
[ Prompt ] ─► [ PRD Spec ] ─► [ Story Board ] ─► [ Pick Story ]
                                                       │
                                                       ▼
[ Land worktree ] ◄── [ Verify Gate ] ◄── [ DMARTIC Inner Loop ]
                             │                         ▲
                             └── fail: return to board ─┘
                                 (with diagnostics attached)
```

**DMARTIC** — understand, plan, act, verify, reflect — with a dual-process switch: fast ReAct for a
localized edit, deliberate **best-of-N across parallel worktrees** when the change is architectural.
Three candidates, all tested, ranked, repaired sequentially on failure. Not tree search: one node
expansion costs a full agent run plus a test suite, which makes deep search economically irrational.

The verifier then runs the pristine tests. Pass, and the worktree lands. Fail, and the story returns
to the board with diagnostics attached rather than a bare error.

One rule governs the whole thing: **gates admit, scores rank, and the two are never conflated.** A
gate is binary and blocking; a score orders candidates. The absence of a verdict must never be
representable as a pass — that single constraint is what keeps benchmark numbers from quietly
inflating over time.

---

## 4. Boxes and the DAG — Logic as Configuration

Every stage is a box: `WorkflowStep[In, Out]` — a Python class with a typed Pydantic input, a typed
output, and no knowledge of its neighbors.

The pipeline is a DAG declared in `config.toml`. Reordering stages, swapping the planner, or
A/B-testing two decomposition strategies is a **configuration change, not a code change**. Each step
boundary emits an event onto the bus and persists its output, which makes a pipeline resumable at
step granularity, replayable from a cassette, and — the part that matters most — *measurable*.

Because the strategy is **data**, the outer loop can propose a different one and the benchmark can
adjudicate. **Planning quality stops being a matter of taste.** That is the payoff of treating agent
logic the way dbt treats data transformation: declarative stages, typed edges, each independently
testable, the whole graph reconfigurable without touching the engine.

And the discipline that keeps it honest: a planning stage ships only if it beats *no planning* on the
benchmark. A bad story board wastes every downstream step, and unlike a bad edit, nothing tests it.

---

## 5. The Outer Loop — Improving the Harness Itself

RHI (Reflexive Harness Improvement) reads thousands of past trajectories offline and tunes prompt
templates, tool descriptions, and model-tier routing — send spec generation to a cheap model, coding
to a frontier one, and cut cost substantially without touching quality.

Two constraints make it safe rather than reckless:

1. **It may only modify a declared mutable surface.** The kernel — dispatch, policy, the capability
   model — is a trusted computing base the agent can never write. Self-improvement that can rewrite
   its own security boundary is not self-improvement.
2. **It may only ratchet on a change that clears the measured noise floor.** This is the discipline
   that separates learning from drift, and it is why the evaluation harness is built *before* the
   thing it evaluates.

---

## 6. Decoupling — Why This Is a Community Project, Not a Fork-and-Abandon Codebase

Everything crossing a boundary is an `async` method with a JSON-serializable Pydantic payload. A port
is a **contract**, not a class hierarchy.

Want a Rust indexer? A Go search service? A different edit strategy? A local Ollama model instead of a
frontier API? Write an adapter, pass the conformance suite, bind it at the composition root. Nothing
else moves — no kernel changes, no fork of the loop, no patch to rebase forever.

`import-linter` enforces the layering in CI, so the boundaries hold against a contributor in a hurry
— which in Python is the only way they hold at all. Rust and Go get encapsulation from the compiler;
Python gets it from a build gate or not at all.

Improvement therefore happens at two scales, and both are cheap:

* **Micro** — replace one part behind its port. Better retrieval, a faster indexer, a smarter edit
  primitive. The blast radius is one adapter.
* **Macro** — reshape the entire process in config. Add a review stage, split decomposition in two,
  route a step to a different model tier. The blast radius is one file.

Two generated-and-checked artifacts keep the documentation from drifting away from the code: the
event catalog and the port stability table are both produced *from* the source and verified in CI, so
divergence is a build failure rather than a review burden.

---

## 7. Scaling to a Multi-Agent System

Complex software is not built by one engineer in one sitting, and the endpoint here is a team.

Because ports already work over a wire, an **architect harness** delegating stories to **developer**
and **QA verifier** harnesses over A2A or MCP is an adapter swap rather than a new architecture. Each
agent works in its own git worktree — no lock collisions — and verified work merges back through the
same gate a single agent passes.

**The sequencing is not negotiable, and it is the opposite of what's fashionable.** Swarming a
harness whose error rate you have never measured just multiplies an unknown across more agents, and
without a noise floor you cannot distinguish a coordination bug from ordinary stochasticity. The path
runs:

```
one closed loop  ──►  measurement  ──►  process layer  ──►  swarm
```

A single agent that closes one loop end to end — one failing test fixed, gated, logged, replayable —
then the evaluation harness, then the workflow DAG, then multiple agents. Each rung is load-bearing
for the next.

---

## 8. Where the Project Actually Stands

Honesty is part of the pitch, because a harness that overstates itself cannot be trusted to measure
itself.

**The specification still runs ahead of the code, but the first rung is now closed.** Sprint 3a's
exit test — a single sentence with no room to negotiate — is green in CI, not merely on a branch:

> An end-to-end test in CI where the agent, driven by a committed cassette, fixes a failing test in a
> fixture repository through the dispatch choke point, the run is gate-evaluated, and
> `sagiha replay --verify` passes on the recording.

One task. Fixed, gated, logged, replayable. That sentence stopped being aspirational on 2026-07-30.

Two honest caveats keep this from overclaiming. First, it runs against a **committed cassette, not a
live model** — the OpenAI-compatible provider adapter doesn't exist yet, so nothing has been fixed by
a real frontier model end to end. Second, the evaluation harness (E0) — the "prove a change helped"
half of the pitch — still does not exist; measurement is Block 2, deliberately sequenced after this
rung and before anything self-improving. The workflow layer in §4 is a decision record
([ADR-0018](../08-decisions/0018-native-workflow-dag.md)), not a module, and is gated on Block 2
showing planning beats no-planning before it becomes one.

That gap is tracked deliberately rather than papered over: [`docs/STATUS.md`](../STATUS.md) is the
single source of implementation truth and outranks every architecture document. [Sprint 3a is
closed](../implementation/development_plan_v2.md); Sprint 3b (hardening — resumable runs, bus resilience, deny-path
coverage beyond grant expiry) is next, and Block 2 follows once 3b lands.

---

## Further Reading

* [`README.md`](../../README.md) — architecture diagrams, the five levels of agency, quickstart
* [`docs/STATUS.md`](../STATUS.md) — what works today, what does not, and when it lands
* [`docs/08-decisions/`](../08-decisions/) — every binding decision with its rationale **and its
  reversal conditions**, which is what keeps an engineering decision from hardening into dogma
* [`docs/reviews/`](../rationale/reviews/) — the audit trail, including findings that were rejected
