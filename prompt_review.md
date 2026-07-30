---
status: rationale
updated: 2026-07-30
audience: External Principal Engineer / Staff Architect / Tech Lead
purpose: Sprint 0 foundation audit — and the mandate to reshape this foundation into the Super Coder AGI
---

# 🔍 Request for Technical Review — SAGIHA Foundation Audit & Forward Mandate

> **Two jobs, one document.** First, audit what we have built and specified. Second — and this is the
> part that matters more — **use these documents as your starting point and change what you think
> should change.** You are not being asked to grade a finished artifact. You are being asked to
> inherit a foundation and tell us how you would build **The Loop Meta-Harness Agent** on top of it.
>
> If your honest answer is "keep 40% of this and rebuild the rest," that is a successful review.

---

## 0. Your Role and Your Authority

You are acting as an external **Principal Engineer / Staff Architect** brought in before a
foundational sprint is locked. Assume good faith and high competence in the authors — then look hard
for what competence and good faith do not protect against.

**Your authority is deliberately broad:**

| You may | Notes |
| :--- | :--- |
| Recommend rewriting any code in `src/sagiha/` from scratch | ~2,800 LOC. Cheap to discard. We are not attached to it |
| Recommend deleting documents, ports, events, packages, entire subsystems | We expect this list to be non-empty |
| Re-open any ADR | Each carries explicit *Reversal Conditions* — use them |
| Rewrite our contracts, schemas, and loop definitions | Propose the shape you would want to inherit |
| Reject the roadmap sequencing entirely | Blocks 1–5 are a proposal, not a commitment |
| Tell us the target itself is wrong | Including "the meta-harness is not reachable from here" |

**What we ask in return:** evidence, sequencing, and falsifiability. Details in §6.

---

## 1. What SAGIHA Is

SAGIHA (Super AGI Harness Agent) is an autonomous software-engineering harness that turns a frontier
LLM into a self-directed, verifiable coding agent.

**The core inversion.** The LLM is the brain and nothing else. It holds zero tool references, opens no
files, runs no commands. Everything it wants to do arrives as an *intent* that the harness decides
whether to execute. That inversion is the whole design, and it buys four properties a prompt wrapper
cannot have:

1. **Containment** — every effect requires a scoped, expiring capability `Grant`, verified at exactly
   one choke point (`kernel/dispatch.py`). Not a permission dialog someone disables on hour four of a
   six-hour run — a structural property.
2. **Deterministic replay** — every model call recorded to a cassette; CI reruns a full session
   byte-for-byte with zero network I/O and zero API cost.
3. **Measurement** — a standalone evaluation harness with an **A/A noise floor**, so *"this change
   helped"* becomes a number instead of a vibe.
4. **Honest grading** — tests injected read-only from the base commit, so a candidate physically
   cannot edit its own grader (`tests_unmodified`).

**Design constraints we have committed to:** <8,000 LOC target · pure Python 3.13 hexagonal
architecture (`typing.Protocol` + Pydantic + `anyio`) · no LangChain, no LiteLLM, no LangGraph · no
external graph or vector daemons · one SQLite file for persistence.

**Why those rejections.** Each trades breadth for a property we refuse to lose — universal model
wrappers break prompt-cache prefix locking and push calls outside the cassette; orchestration
frameworks relocate the dispatch choke point outside the trusted computing base; LLM-extracted
knowledge graphs are non-deterministic by construction. All are recorded as ADRs with reversal
conditions. **If our reasoning is wrong, these are the highest-leverage places to tell us.**

---

## 2. The Honest Baseline — Read Before Scoring Anything

**The specification runs far ahead of the code. A review that scores the design without holding it
against this baseline is worthless to us.**

| | Measured at time of writing |
| :--- | :--- |
| Documentation | **85** `.md` files (71 excluding `reference/` + `reviews/`) |
| Implementation | **~2,804 LOC** across 54 Python files |
| Typed ports | **22** `Protocol` classes, backed by ~4 real adapters |
| ADRs | **18**, all Accepted |
| Test files | **5** |
| Known defects | **18** (D1–D18), code-verified, all open |
| Working CLI | `sagiha version`. That is the entire surface |
| Empty packages | `agency/`, `aoi/`, `outer_loop/`, `runtime/` — docstring-only `__init__.py` |

**The four facts that should calibrate everything else you read:**

* **D1: the ReAct loop can never dispatch a tool.** The agent has never completed an autonomous
  tool-using step. Not once.
* **Capability grants are minted, stored, and never verified at the point of effect.** `dispatch.py`
  checks only that a `grant_id` is non-null; the expiry logic in `kernel/policy/engine.py` is dead
  code. Path scoping iterates a literal key list `("path", "file_path", "target_file", "dir")` that
  cannot reach `EditRequest.path` — so the primary mutation tool gets an empty scope.
* **The evaluation harness — the thing we call our moat — does not exist.** Zero lines.
* **The `import-linter` CAR contract is presently inert.** `.importlinter` says so in its own comment:
  *"`agency/` is an empty stub until S3 — the ignore above legitimately matches nothing yet."*

Treat every claimed advantage as an advantage **on paper**. A pristine test gate that has never
rejected a candidate has rejected nothing. Meanwhile, every weakness you find in a *shipping*
reference harness (see `docs/reference/harness_examples/`) was discovered by real users on real
deadlines — we have not earned that kind of scar yet, and our first-principles confidence should be
read in that light.

---

## 3. The Forward Mandate — The Loop Meta-Harness Agent

This is the part of the review we care about most, and it is why we are handing you the whole tree
rather than a diff.

**Where we intend to go**, in strict dependency order:

```
L0  Raw LLM call ─────────► string in, string out. No perception, no verification.
L1  Harness ──────────────► the body: tools, AST perception, LSP, worktrees, capability gates.
L2  Loop engineering ─────► the senior-engineer process: PRD → StoryBoard → DMARTIC → gate.
        │
        ├──► L3  Meta-loop (RHI) ──► vertical: one harness, better over time. Self-tuning against
        │                            a measured noise floor. Nobody has this.
        └──► L4  Multi-agent ──────► horizontal: many harnesses, same quality. Architect harness
                                     delegating to developer + QA harnesses over A2A / MCP.
```

L3 and L4 are **parallel branches above L2, not sequential rungs** — both need L2, neither needs the
other. We currently sit at roughly **L0.3**: below the first rung, with L1–L4 specified.

**The Loop Meta-Harness Agent** is the L3 target: a harness that reads thousands of its own
trajectories, proposes changes to its prompts, tool descriptions, and model-tier routing, and is only
permitted to ratchet on changes that clear a measured A/A noise floor — while never touching the
immutable kernel that enforces its own security.

### The questions we need you to answer about this trajectory

1. **Is L3 reachable from this foundation, or is it a different system wearing this vocabulary?**
   Be blunt. If the RHI outer loop as specified is fantasy at this maturity, say so and tell us what
   the credible version is.
2. **What must be true at L1/L2 for L3 to be possible at all?** We believe the answers are: total
   replay, a trajectory store rich enough to mine, and a noise floor. If we are missing a
   precondition, that omission is the most expensive thing in this review.
3. **Is our sequencing right?** We assert measurement must precede self-improvement, and that L4
   before L3 is a trap — swarming a harness whose error rate you have never measured multiplies an
   unknown across more agents, and without a noise floor you cannot distinguish a coordination bug
   from ordinary stochasticity. **Argue with this if you disagree.**
4. **What is the smallest system that demonstrates the meta-loop is real?** We would rather ship a
   narrow honest L3 than a broad speculative one.
5. **What would you throw away** to get there faster without sacrificing the four properties in §1?

**If our docs are the wrong starting point for this, say so and tell us what the right one is.** We
would rather rewrite 60 documents in Sprint 0 than discover the shape was wrong in Sprint 8.

---

## 4. Full Scope — Every File Is In Play

### Root
| File | What it claims |
| :--- | :--- |
| `README.md` | Executive summary, five levels of agency, mermaid architecture diagrams |
| `AGENTS.md` | Architectural invariants, TCB rules, codebase conventions (agent-facing) |
| `pitch.md` | High-level narrative of the meta-loop harness thesis |
| `pyproject.toml` · `.importlinter` · `.github/workflows/ci.yml` | **Cross-check the docs against these — several contradictions surface only here** |

### `docs/`
| Location | Contents |
| :--- | :--- |
| `STATUS.md` | **Single source of implementation truth.** Outranks architecture docs until Sprint 3 closes |
| `01-executive/` | `executive-summary` · `vision-and-philosophy` · `glossary` · `v0.1-user-guide` |
| `02-architecture/` | `car-model` · `microkernel-and-bus` · `event-bus-and-hooks` · `security-and-threat-model` · `prompt-architecture` · `context-and-cache-engineering` · `neural-symbolic-memory` · `remoteable-ports` · `execution-profiles` · `extension-model` · `entry-points-and-piloting` · `performance-sidecars` |
| `03-contracts-and-models/` | `hexagonal-ports` · `domain-schemas` · `tool-catalog` · `task-and-acceptance` · `error-taxonomy` · `lsp-interface` · `port-stability-and-versioning` · `protocols-mcp-a2a` |
| `04-workflows-and-loops/` | `dmartic-inner-loop` · `rhi-outer-loop` · `event-catalog` (generated) · `git-worktree-branching` |
| `05-tech-stack/` | `control-plane-python` · `composition-and-configuration` · `configuration-reference` · `indexing-and-retrieval` · `llm-providers-and-economics` · `observability-and-telemetry` · `dependencies-and-versions` · `aoi-coprocessors` |
| `06-guides-and-patterns/` | `getting-started` · `writing-adapters` · `port-conformance-testing` · `ci-and-quality-gates` · `benchmark-curation` · `running-benchmarks` · `metrics-analytics-and-self-improvement` · `ollama-qwen-coder-setup` · `sidecar-development` |
| `07-roadmap/` | `phased-migration-matrix` (Blocks 1–5) |
| `08-decisions/` | ADRs 0001–0018 + `README.md` (log + template) |
| `implementation/` | `contracts-to-code` · `development-plan-and-prompts` |
| `sprints/` | `sprint-2.md` (closed with known defects) · `sprint-3.md` (active plan, D1–D18) |
| `reviews/` | `done/` · `doing/2026-07-29-foundation-review.md` (**the current audit of record — D1–D18, G1–G10, U1–U5**) · `todo/` (comparative analysis vs. 4 shipping harnesses; Sprint 0 decision record) |
| `reference/` | `harness_research` · `conceptual-design` · `design-derivation` · `benchmarking-existing-harnesses` · `harness_examples/` (Claude Code, Grok Build, Hermes, OpenCode — vendored under `src/` and analyzed) |

### Code
`src/sagiha/{domain,ports,kernel,adapters,agency,aoi,outer_loop,runtime}/` · `tests/` · `scripts/gen_event_catalog.py`

---

## 5. The Eight Review Dimensions

For each: what is **GOOD** (and should be defended against future pressure), what is **BAD** (with
evidence), what should **CHANGE** (specific and sequenced).

### 5.1 Architecture & Decoupling
Hexagonal ports, CAR three-layer model (Control / Agency / Runtime), `import-linter` contracts, zero
framework lock-in.
> Is CAR earning its keep on top of hexagonal, or is it two vocabularies for one boundary? Is
> `agency/` a real layer or a naming convention? Does a five-ring import contract survive contact
> with a contributor in a hurry? Is ~500 LOC/file the right constraint, or cargo cult?

### 5.2 Capability Security & Threat Model
CAR isolation, unforgeable `Grant` tokens, fail-closed interceptors, rootless Podman, egress
allowlisting, the TCB boundary.
> Given §2 — the grant is never verified — is the *design* sound and only the implementation missing,
> or is the design itself insufficient? Can you break the model on paper? What does an unforgeable
> token mean in a language with no memory safety and full introspection? Is the sandbox perimeter in
> the right place?

### 5.3 Tech Stack & ADR Choices
ADRs 0001–0018. Python 3.13, SQLite-WAL, Tree-sitter, native SDKs + `base_url`, rootless Podman,
best-of-N over MCTS, deferred dense retrieval.
> Which ADR is most likely to be regretted, and what is its reversal condition — is it written so it
> can actually fire? Is <8,000 LOC achievable or a slogan? Is Python the right control plane for
> something that wants to run for six hours unattended?

### 5.4 Cross-Document Consistency
> Contradictions, stale contract definitions, terms that drifted, claims the code no longer supports.
> Note our convention: contracts live in `src/`, and docs referencing them must not re-declare them.
> Where docs and code disagree, tell us **which one is wrong** — do not assume the code is behind.

### 5.5 Workflow & Loop Mechanics
DMARTIC inner loop, RHI outer loop, `WorkflowStep[In, Out]` DAG
(Prompt → PRDSpec → StoryBoard → TaskSpec), System 1 / System 2 switching.
> Is DMARTIC's eight-stage cycle real engineering or an acronym? Is a declarative step DAG the right
> abstraction for agent logic, or does it impose false structure on something inherently
> non-deterministic? Where is the loop *underspecified* — termination, stuck detection, iteration
> budget, mid-turn steering?

### 5.6 Sprint Planning & Code Evolution
Blocks 1–5, `sprint-3.md` (D1–D18), `STATUS.md`.
> Is Sprint 3's exit test the right definition of done? Is the defect ordering correct — we believe
> `ModelRequest` v2 must land before any cassette fixture is committed, since cassettes embed the
> shape. **Is any D-fix actually a symptom of a design flaw that a fix will only entrench?**

### 5.7 Quality of Results & Verifiability
Pristine gates, System 1 vs. System 2 best-of-N worktree search, post-edit LSP diagnostic deltas,
gates-admit / scores-rank.
> Will these produce measurably better code, or only measurable code? Is best-of-N at depth one
> sufficient? Is our A/A noise floor methodology statistically sound — and what sample size do we
> actually need for the lift claims we intend to make?

### 5.8 Extensibility & Protocol Universality
Wire-safe Pydantic ports across OpenAI-compatible APIs, MCP, REST/A2A, gRPC; the extension model.
> Is "every method async, every payload Pydantic" sufficient for genuine remoteability, or does it
> just make the violations subtler? We know of one live violation
> (`WorktreeManager.allocate() -> Workspace` returns a Protocol instance). **Are there others we
> have not found?**

---

## 6. How We Need You to Work

**Evidence or it does not count.** Every defect carries a verified `file:line` or
`doc.md#section`. A finding we cannot locate, we cannot fix. Label inferences as inferences.

**Two axes, never one number.** Rate *specification maturity* and *implementation completeness*
separately. A blended score on this codebase is exactly the over-claiming we are asking you to catch.

**Do not rediscover — challenge.** D1–D18, G1–G10, U1–U5, and the Tier A/B/C recommendations in
`docs/reviews/` already exist. We do not need them restated. We need (a) what those reviews
**missed**, and (b) where their verdicts are **wrong**. Several prior findings were rejected on
analysis, and the rejections are recorded rather than deleted. **If a rejection was itself a mistake,
that is among the most valuable things you can tell us.**

**Respect settled decisions — but not unconditionally.** Do not re-argue an ADR on general
preference. Do re-open one if its reversal condition is already met, or if the condition is written
so vaguely it can never fire.

**Prioritize by cost of delay.** We want to know what becomes 10× more expensive if we ship the next
sprint without it — not a ranked list of everything imperfect.

**Name our self-deceptions.** Two failure modes we cannot self-diagnose: **over-specification**
(mechanisms declared but never exercised) and **inverted sequencing** (building the interesting layer
before the layer that proves it works). Sprint 2 already made the second mistake once — it built
kernel plumbing while the evaluation harness was named the moat.

### Four traps that have caught previous reviewers

Not to steer your conclusions — to keep your effort on new ground. Each was filed by a prior review
and rejected on analysis:

| Looks like | Actually |
| :--- | :--- |
| Four empty packages, prune them | `agency/` and `runtime/` are the **A** and **R** of CAR. Deleting them voids the `import-linter` contracts that are our strongest implemented property. The emptiness is real; **amputation is the wrong fix — code is** |
| 32 event subclasses, collapse to 4 | The `ToolCallRequested`/`ToolCallAuthorized` split is what lets an audit separate *attempted* from *permitted*. Collapsing trades a doc problem for an architectural one. The catalog is already generated and CI-checked |
| 22 ports before one working loop = overengineering | A port is ~25 lines of `Protocol` and is the mechanism that makes every roadmap deferral safe. The real question is whether the **compatibility promise** is frozen, not whether the declaration exists |
| "Evaluator too rigid for unstructured tasks" | Existing normative policy, verbatim. Check `task-and-acceptance.md` before filing it |

**If you think any of these four rejections is wrong, say so explicitly** — we would rather re-open a
closed question than protect a bad decision.

---

## 7. Deliverable — Single Technical Review Report

> [!IMPORTANT]
> **DO NOT EDIT OR MODIFY ANY EXISTING FILES IN `docs/` OR `src/`.**
> Your deliverable is **EXCLUSIVELY ONE REPORT FILE** created at the root of the repository named:
> **`final_review_sagiha_concept_and_plan.md`**

Write your complete audit, analysis, and proposed changes into `final_review_sagiha_concept_and_plan.md` following this structure:

1. **Verdict** — 3–5 sentences. Would you stake your name on this foundation? If not, what single change would flip that?
2. **The eight dimensions** — GOOD / BAD / CHANGE, dual-rated (Specification Maturity vs. Implemented Code), evidence attached.
3. **New findings** — using our ID convention: `D` defect (must carry `file:line`) · `G` gap · `C` proposed change · `X` doc remediation.
4. **Challenges to prior verdicts** — where `docs/reviews/` got it wrong, and why.
5. **Delete list** — docs, ports, events, mechanisms, packages. **We expect this to be non-empty and we will act on it.**
6. **Sequencing critique** — is Block 1 → 5 correctly ordered? What is being built too early? What deferral will become load-bearing sooner than we think?
7. **The forward mandate (§3)** — answer all five questions. Is the Loop Meta-Harness Agent reachable from here? What is the smallest system that proves the meta-loop is real?
8. **Rewrite recommendations** — see §8.
9. **The documentation shape** — if 85 files is wrong, which 55 do we delete, and what is the right structure?
10. **What would change your mind** — for your top three recommendations, state the evidence that would prove you wrong.

### If you have limited time

| Budget | Do this |
| :--- | :--- |
| **~2 hours** | `STATUS.md` → `docs/reviews/doing/2026-07-29-foundation-review.md` → `sprints/sprint-3.md` → `08-decisions/README.md`. Answer §7 items 1, 6, 7 only |
| **~1 day** | Add `02-architecture/` + `03-contracts-and-models/` + a `src/sagiha/` read. Full §7 minus item 9 |
| **~1 week** | Everything, including the reference harness analyses in `docs/reference/harness_examples/` — they are why several of our rejections exist |

---

## 8. Explicit Authorization to Recommend Rewrites

**Feel free to recommend refactoring or rewriting any existing Sprint 1 and Sprint 2 code in
`src/sagiha/` from scratch if your audit shows a cleaner or more SOTA approach. We are committed to a
world-class codebase and will gladly rewrite components to get it 100% right.**

Concretely: ~2,800 LOC is cheap to discard and we are not attached to it. If the honest
recommendation is *"delete the kernel and rebuild it around a corrected `ModelRequest`"* — say that.
Sunk cost is not an argument we will make at you, and "it already exists" is not a defense we will
offer.

The same applies to the documentation, the port set, the event taxonomy, the CAR model, the DMARTIC
acronym, and the roadmap. **The only things we ask you to treat as near-fixed are the four properties
in §1** — containment, replay, measurement, honest grading — because they are the reason the project
exists. Even there: if you can show one of them is unachievable, or achievable only at a cost that
makes the system useless, that is a finding we need more than any other.

---

## 9. Vocabulary

Enough to read the tree without the glossary. Full version: `docs/01-executive/glossary.md`.

| Term | Meaning |
| :--- | :--- |
| **CAR** | Control / Agency / Runtime. Control = kernel + policy (the TCB); Agency = planning, prompt assembly, candidate search (emits intents only); Runtime = actual I/O |
| **TCB** | Trusted Computing Base. Never agent-writable. Deploy requires human sign-off |
| **Grant** | Scoped, expiring capability token minted only by `PolicyEngine.authorize()` |
| **DMARTIC** | Inner loop: Design → Measure → Analyze → Review → Test → Improve → Control → Reflect |
| **RHI** | Reflexive Harness Improvement — the outer loop that tunes the harness itself |
| **E0** | The standalone evaluation harness. Does not exist yet |
| **A/A noise floor** | Run identical configs twice, measure the spread from pure stochasticity. Nothing inside it counts as improvement |
| **Cassette** | Recorded model interactions enabling byte-identical zero-network replay |
| **`tests_unmodified`** | Hard gate: tests injected read-only from the base commit so a candidate cannot edit its own grader |
| **Gates vs. scores** | Gates admit (binary, blocking); scores rank. Never conflated. Absence of a verdict must never be representable as a pass |
| **Profile** | Data declaring which optional ports bind (`coding`, `chat`, `analysis`, `review`) |
| **Block 1–5** | Roadmap phases: runnable loop → measurement → authority → retrieval → sandbox/MCP/OTel |
| **L0–L4** | Levels of agency (§3) |
| **D / G / C / X / U** | Finding IDs: Defect / Gap / Change / Doc-remediation / Unproven assumption |

---

## 10. Closing

We are in **Sprint 0** — the documentation sprint — and its entire purpose is to be told what is
wrong while changing our minds is still cheap. Nothing here is load-bearing yet. Everything is
negotiable except the reason the project exists.

Judge us by capabilities and outcomes, not by stack or pattern fashion. Cite concrete gaps over
general concerns. Where you disagree with a decision, engage the reasoning we recorded rather than
the conclusion.

**Prefer judgment over praise. If something is genuinely good, one line is enough — spend your effort
where we are wrong.**

---

### Related

* `docs/reviews/README.md` — how reviews work here: advisory until a finding lands in a normative doc,
  an ADR, or a sprint plan. Rejected findings are recorded, never deleted
* `docs/reviews/todo/prompt_reviewer.md` — an earlier, narrower Sprint 0 review request focused on
  ecosystem parity and pluggability. This document supersedes it in scope
* `docs/reviews/doing/2026-07-29-foundation-review.md` — the current audit of record. **Start here**
