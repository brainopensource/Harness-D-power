---
status: advisory
date: 2026-07-30
audience: SAGIHA maintainers · contributors · reviewers
purpose: Translate the external foundation audit into a resequenced development plan
basis: final_review_sagiha_concept_and_plan.md · docs/reviews/doing/2026-07-29-foundation-review.md · docs/STATUS.md · docs/sprints/sprint-3.md
---

# 📐 Development Plan Improvements — Same Destination, Better Route

> **The one-line summary.** Nothing about *what* SAGIHA is meant to become changes. What changes is
> the **order** we build it in, the **size** of each step, and a small number of **data shapes we must
> fix before we start recording anything**. This is a plan for spending time well, not a reduction in
> ambition.

---

## 1. What Is *Not* Changing

It is worth being explicit about this first, because a critical audit can read like a retreat. It is
not one. Every one of these survives the review intact:

| Unchanged | Status |
| :--- | :--- |
| **The four properties** — containment, deterministic replay, measurement, honest grading | Reaffirmed as the reason the project exists |
| **The L0 → L4 destination** — harness → loop → meta-loop → multi-agent | Reaffirmed, including L3/L4 as parallel branches above L2 |
| **The Loop Meta-Harness Agent as the L3 target** | Reaffirmed as a thesis; the review's argument is about *when*, not *whether* |
| **Hexagonal ports + capability-gated dispatch choke point** | Called "a good substrate." Keep |
| **Gates admit / scores rank / absence is never a pass** | Called "the project's best idea" |
| **Framework rejections** (LangChain, LiteLLM, LangGraph, vector daemons) | No ADR reversal condition has fired |
| **Sprint 3's one-sentence exit test** | Confirmed as the correct definition of done |
| **`STATUS.md` as implementation truth, ADR discipline, import-linter contracts** | Explicitly on the do-not-delete list |
| **Best-of-N over MCTS (ADR-0005)** | "Sufficient for v1; do not reopen" |

**The destination is the same. The route is what we are correcting.**

---

## 2. What Is Changing — Three Categories

### Category A — Sequencing (the bulk of it)

Build the boring layer that makes claims falsifiable *before* the interesting layer that makes claims.
Concretely: measurement before self-improvement, a measured single agent before a swarm, and one
closed loop before a workflow DAG above it.

### Category B — Step size

Sprint 3 as currently written is 2–3 sprints wearing one label: eighteen kernel defect fixes plus a
run loop plus five tools plus a provider adapter plus an evaluator plus a CLI plus resume plus a bus
rewrite plus CI coverage. The risk is not that it is hard — it is that we "close" it with a green
cassette that never exercised the deny path, and then believe the loop is closed.

### Category C — Three data shapes to fix *before* recording anything

**This is the part that is not about ordering, and the reason the plan cannot simply be "do the same
things in a different sequence."** Three shapes are wrong today, and every cassette, trajectory, and
end-to-end test we record against them teaches a wrong invariant that gets expensive to unteach:

| Finding | The shape | Why it must precede recording |
| :--- | :--- | :--- |
| **D20** | `GateReport.admitted` computes `all(g is not False …)` — an **unset** gate counts as a pass | Directly contradicts our own rule that absence of a verdict must never be representable as a pass. An evaluator that forgets `tests_unmodified` admits a candidate that edited its own grader. This is a correctness bug in any sequence |
| **D21** | `ToolCallCompleted` / `ToolCallFailed` carry no `call_id`; neither does `ToolResult` | Multi-tool steps cannot be correlated. Every trajectory recorded now is structurally unmineable — which silently removes the substrate L3 depends on |
| **D10 → D2** | `ModelRequest` cannot describe a real request; cassettes embed its shape | Already correctly ordered in Sprint 3. Reaffirmed here because it is the steepest contract cliff: fixing it after a cassette corpus exists means rebuilding the corpus |

Plus one operational bug worth fixing this week: **D19** — the event-catalog generator stamps
`updated:` with today's date, so `--check` fails on a clean tree the day after the catalog is
committed. CI will redden daily and the drift gate will lose its signal.

---

## 3. The Resequenced Plan

```
BEFORE
  Block 1 (loop) → Block 2 (measure) → Block 3 (authority) → Block 4 (retrieval) → Block 5 (sandbox)

AFTER
  Block 1a  closed loop + grant verification + path scope for built-in tools
     ∥      harvest scaffolding (needs no working agent)
  Block 1b  hardening: resume, bus anyio + observer timeout, required ports, deny-path tests
  Block 2   E0-lite, local-first so the noise floor is affordable
  Block 3   remaining authority
  Block 5   sandbox — before autonomy leaves interactive, not after
  Block 4   retrieval, only with an ablation showing it pays
  L3-min    one mutable prompt template + A/A on ≤15 local tasks
  L4        never before a measured L2
```

### What moves **earlier**

| Item | Why |
| :--- | :--- |
| Grant verification at the point of effect | Sprint 3 rewrites `dispatch.py` anyway. Deferring means touching the most security-sensitive code twice |
| Schema-declared path scoping for the five built-in tools | Block 1 ships `apply_edit`. Shipping writes before the capability model can constrain them inverts the project's premise |
| Harvest scaffolding | Commit-replay task extraction needs no working agent, and doing it early forces honesty about `TaskSpec` and acceptance shapes |
| `call_id` correlation + typed event round-trip | The mining substrate must exist before anything is recorded |
| SQLite journal-mode probe | Sprint 3 puts SQLite on every developer machine; on an NFS home directory WAL fails as a `SIGBUS` panic, not an error |
| Container sandbox (Block 5) | Load-bearing the moment autonomy leaves `interactive` |

### What moves **later**

| Item | Why deferral is cheap |
| :--- | :--- |
| Workflow DAG / PRD → StoryBoard | ADR-0018 already gates this on an E0 ablation. A planner above a loop that cannot dispatch a tool is how Sprint 2 happened |
| MCP, OTel, LSP, `watchfiles` in the default install | Move to optional extras. Dependency gravity pulls implementation toward the periphery |
| AOI / MetaImprover as implementation targets | The ports stay; only the implementation waits. No measured lift is possible yet |
| Dense retrieval | ADR-0014's recall trigger has not fired |
| Execution profiles beyond `coding` | Four profiles multiply unbound-port combinations before one profile works |
| Multi-agent / A2A | Swarming an unmeasured error rate multiplies an unknown |

---

## 4. Why This Produces a *More* Flexible Foundation, Not a Smaller One

This is the heart of it, and it is the reason deferral costs us almost nothing.

**A port is the seam; the adapter is the commitment.** A `Protocol` is ~25 lines. Declaring
`EmbeddingProvider` and not implementing it is not debt — it is a shaped socket. *Deleting* it would
convert a deferred component into a future refactor. So the rule is **freeze the compatibility
promise, not the declaration**: keep every port, but revoke the `stable` markings on ports whose
first adapter cannot exist yet, so nobody builds against a promise we cannot keep.

**Config is the strategy.** Because stages, profiles, and tool sets are declared rather than coded,
reshaping the process later is a config change, not a fork. That is what makes waiting cheap — we are
not deferring a rewrite, we are deferring a file.

**Generated artifacts keep the docs true.** The event catalog is generated from the source and checked
in CI. Applying the same pattern to the port stability table and the config schema turns doc/code
drift into a build failure instead of a review burden — which is what lets the specification stay
large without becoming fiction.

**Small steps are what make contributions possible.** A community can replace an indexer, an edit
strategy, or a model provider behind its port with a blast radius of one adapter. That property is
only real once the loop it plugs into actually runs — which is the strongest argument for closing the
loop first. **Nobody can contribute to a foundation that has never executed a step.**

---

## 5. What "Smart Use of Time" Means Concretely

| Principle | Applied |
| :--- | :--- |
| Fix what gets more expensive later | The three data shapes (§2 Category C), before any recording |
| Do work that needs no dependencies in parallel | Harvest scaffolding alongside the loop |
| Do not build machinery for a measurement you cannot afford | E0-lite runs local-first, on cassettes or Ollama |
| Do not touch security-sensitive code twice | Grant verification lands with the dispatch rewrite |
| Prove the smallest version before the full version | L3-min: one prompt file, 10–15 tasks, a shell script for a MetaImprover |
| Refuse work whose definition of done is a count | No sprint closes on adapter count or doc count |

**The single test that governs everything:** *does this make Sprint 3's exit sentence true?* One
cassette-driven fix of a failing test, through a grant-verified choke point, gate-evaluated, with
`replay --verify` passing. Work that does not serve that sentence waits.

---

## 6. Immediate Actions

| # | Action | Type | Owner |
| :-- | :--- | :--- | :--- |
| 1 | Fix the event-catalog date stamp (**D19**) — derive from git or exclude `updated:` from `--check` | Bug | — |
| 2 | Tighten `GateReport.admitted` so a coding-profile gate cannot admit on `None` (**D20**) | Bug | — |
| 3 | Add `call_id` to `ToolResult` and the tool completion events (**D21**) | Shape | — |
| 4 | Split `sprint-3.md` into **3a** (closed loop) and **3b** (hardening) | Plan | — |
| 5 | Add grant verification + schema-declared path scoping to 3a | Plan | — |
| 6 | Move `mcp`, `opentelemetry-*`, `lsprotocol`, `watchfiles` to optional extras | Hygiene | — |
| 7 | Revoke `stable` markings on ports without a second adapter | Hygiene | — |
| 8 | Unify roadmap vocabulary — Blocks 1–5 *or* E0/S0–S4, with one mapping table | Docs | — |
| 9 | Soften absolute claims: "unforgeable" → reachability-enforced; "byte-for-byte" → graded L0/L1/L2 | Docs | — |
| 10 | Collapse public DMARTIC to ReAct + verify + reflect; keep eight stages as an internal checklist | Docs | — |

Items 1–3 are cheap and should not wait for a sprint boundary. Items 4–5 are the sprint replan.
Items 6–10 are hygiene that can ride along.

### Two audit recommendations we are *not* adopting as written

* **"Relabel all ports `draft`."** We already have a normative
  `Stable / Provisional / Experimental` scheme declared per module. Revoke the *stable* markings
  within that scheme rather than inventing a fourth tier.
* **"Demote ADR-0018 to gated."** It is already written that way — a non-goal until Sprint 3's exit
  test is green, and shipping only if E0 shows planning beats no-planning. No change needed.

We are also **deprioritizing** the documentation quarantine plan. It is the largest single
recommendation and the only one that consumes a sprint without moving the exit test. It happens after
Block 1a.

---

## 7. Closing

The audit's verdict was that the project will fail the way ambitious harnesses usually fail — by
building the interesting layer before the boring layer that makes claims falsifiable. That is a
sequencing critique, and sequencing is fixable at zero cost while the code is 2,800 lines.

So: same destination, same four properties, same L3 ambition. Smaller steps, a corrected order, three
data shapes fixed before we record anything, and every port left in place so the foundation can still
grow in whatever direction the measurements point.

**Make it work safely, prove it works, then make it smarter.**

---

### Related

* `final_review_sagiha_concept_and_plan.md` — the external audit this plan responds to
* `docs/STATUS.md` — implementation truth; outranks architecture docs until Sprint 3 closes
* `docs/sprints/sprint-3.md` — the plan to be split into 3a / 3b
* `docs/reviews/doing/2026-07-29-foundation-review.md` — D1–D18, G1–G10, U1–U5
* `docs/reviews/todo/proj_plan_design_and_docs_improvs.md` — the Sprint 0 decision record
* `docs/08-decisions/` — ADRs with reversal conditions
