---
status: rationale
retrieval: excluded
updated: 2026-08-05
---

# AETHER v3.0.0 — Architecture Decision Records

> [!NOTE]
> **LLM / AI AGENT NOTICE**: This file is Phase-0 rationale for the AETHER rewrite. It is not
> binding and defines no contract. Contracts live in `src/`. Read it for *why*, not *what*.

Answers RFP [§5.3](../reviews/review_project_rewrite_v300.md) and satisfies **D-04** of the
[Phase-0 charter](../reference/PLANNING.md).

New records are numbered **A-0NN** to avoid colliding with the 27 accepted ADRs in
[`docs/08-decisions/`](../../08-decisions/README.md). They are `rationale` here and promote into that
normative tree, renumbered, when the rewrite branch merges. Each carries **Reversal Conditions** — a
decision without one is a belief.

---

## Part I — Closing the Phase-0 open decisions (Q1–Q8)

### A-001 — Project name

**Context.** PLANNING.md Q1: the working name appears in every path, package, and public artifact and
must be pinned before any document depends on it. Supersedes ADR-0001 (SAGIHA).

**Decision.** **AETHER.** Python package `aether`, source root `src/aether/`, version line v3.0.0.
`src/sagiha/` stays on disk, unmodified, as reference and fixture source until AETHER passes the same
conformance suite.

**Consequences.** Two package trees coexist during the rewrite. `pyproject.toml` gains `src/aether` to
pyright's include list; `src/sagiha` is excluded from new lint gates but keeps its existing ones.

**Reversal Conditions.** A trademark conflict, or a commercial naming decision before public release.

---

### A-002 — Control-plane language: Python 3.13, monoglot

**Context.** PLANNING.md Q2 and RFP §4-A. Options: Python / Go / Rust monoglot, or the three-plane
polyglot design in `../reference/go_rust_greenfield_harness.md`.

**Decision.** **Python 3.13, monoglot, no second language in Phase 1.** Full argument in
[runtime decisions](./rewrite_v300_decisoes_runtime.md): the workload is network-bound — the LLM call
is four to seven orders of magnitude more expensive than any in-process language boundary — and a
compiled control plane additionally puts a build step inside the L3 self-improvement loop. Invariant
I3 (wire-serializable ports) keeps the sidecar option free.

**Consequences.** Best LLM SDK ecosystem and fastest iteration. Higher resident footprint (T6's
<300 MB is achievable but not comfortable) and GIL-bound CPU parallelism for indexing.

**Reversal Conditions.** Per component, on a measured trigger recorded in
`docs/rationale/benchmarks/`: **RT-1** cold index >10 min on 1M LOC after worker-process parallelism;
**RT-2** RSS >300 MB or idle CPU >1% attributed to interpreter overhead; **RT-3** incremental
single-file re-index >200 ms. Response is a sidecar behind the existing port — PyO3 in-process by
default, socket/gRPC only for stateful or separately-supervised components.

---

### A-003 — Greenfield in `src/aether/`, same repository

**Context.** PLANNING.md Q7 recommended a new repository, mining SAGIHA. The RFP directs evolution
within this tree. Both aim at the same thing: a clean core without the predecessor's accumulated
compromises.

**Decision.** **Greenfield package in this repository.** New code in `src/aether/`; `src/sagiha/`
untouched. This preserves the documentation corpus, the ADR history, the CI gates, the replay
fixtures, and the honesty audit trail — all of which are assets — while giving the code a clean start.

**Consequences.** No repository migration cost, no lost history. The tree carries two implementations
for the duration; `docs/STATUS.md` must state clearly which is real.

**Reversal Conditions.** A commercial requirement for a separate repository (licensing, access
control, or a customer-facing open-source split).

---

### A-004 — UI: TUI-first over a typed event stream

**Context.** PLANNING.md Q4. A `frontend/` monorepo already exists (pnpm + turbo, Tauri GUI, CLI,
`packages/protocol`, `mock-engine`) with a documented bridge contract.

**Decision.** **Headless engine first; TUI as the first client.** Every surface — TUI, CLI, GUI, CI —
is a client of one typed event stream. Detail in [UI and TUI](./rewrite_v300_uiux_tui.md).

**Consequences.** No privileged path: the CLI cannot do anything the protocol does not expose, which
keeps the protocol honest. Reuses the existing frontend workspace.

**Reversal Conditions.** A customer requirement for a GUI-first product surface.

---

### A-005 — Wire format: WS + JSON, TS types generated from the schema

**Context.** PLANNING.md Q5. Alternative: gRPC/Protobuf.

**Decision.** **WebSocket + JSON** for the UI leg, with TypeScript types generated from the schema.
Protobuf is reserved for a genuine cross-language sidecar boundary, if RT-1/2/3 ever fires.

**Consequences.** Debuggable by eye, no codegen toolchain on the critical path, browser-native. Higher
per-message overhead than protobuf — irrelevant at UI event rates.

**Reversal Conditions.** Measured serialization overhead becoming a material share of engine CPU, or a
cross-language sidecar boundary where a schema-first IDL earns its keep.

---

### A-006 — Benchmark targets: Pro ≥ 80%, Verified ≥ 96%, lift reported alongside

**Context.** PLANNING.md §1 recorded Pro's leader at 69.2%; as of Aug 2026 it is ~80.3%. Verified is
saturating at ~96%. The stakeholder decision is real SOTA rather than a comfortable intermediate
target.

**Decision.** **Primary: SWE-bench Pro ≥ 80%. Secondary: Verified ≥ 96%.** Every published absolute is
accompanied by **scaffold-attributable lift** — paired delta versus a single-shot baseline on the
identical model, with a CI excluding the measured A/A noise floor, plus cost and wall-clock per
resolved task. Amends ADR-0015. Protocol in
[measurement strategy](./rewrite_v300_measurement_strategy.md).

**Consequences.** High-ambition targets whose absolute component is dominated by model tier
(**PLANNING.md R1**), stated explicitly in this record and in any client-facing document. Lift is the
claim that survives a model swap.

**Reversal Conditions.** Benchmark retirement or migration; a leaderboard shift making Pro
uninformative; contamination findings invalidating the public pool.

---

### A-007 — Reference study policy

**Context.** RFP §3 and the reference clones. The project competes with systems whose source is
readable.

**Decision.** **Concepts and published theory transfer; implementation does not.**

**(a) No external code enters `src/aether/`. Ever.** Not copied, not adapted, not vendored. What
crosses from a reference is understanding — an algorithm, a protocol shape, a design constraint, a
failure mode — expressed in our own code. Reference trees exist to be *read*, and reading is the only
thing they are for. This is stricter than "attribution" or "license compatibility": even permissively
licensed code stays out, because the project's value is that its design is its own and defensible.

(b) Only official and open-source trees are cloned, and preference goes to **documentation over
source** where documentation suffices — `src/claude_refs/` is markdown, and that is the right shape
for a reference. (c) De-obfuscated or decompiled artifacts of closed CLIs are **deferred, not
permanently excluded** — bringing one in would be a separate, explicitly recorded decision with its
own legal review, never a silent one. (d) Any design change that converges on a competitor's choice
must be justified by **our own KPIs** — an ablation on our suites, against our noise floor, recorded
in `docs/rationale/benchmarks/`. (e) Dependencies are open-source only, license class reviewed on
addition.

**Reference harnesses run as benchmark arms, and that is a different relationship.** Executing Hermes
against our tasks on our model ([measurement §1b](./rewrite_v300_measurement_strategy.md)) is
measurement, not derivation — we run the binary, we read the score, no code moves. It is the most
valuable use of a competitor's tree and it is fully consistent with (a).

**Consequences.** Clean IP provenance for a commercial product. Slower to copy a known-good
implementation; the ablation requirement is the cost of being able to defend every design choice.

**Reversal Conditions.** Explicit legal review concluding a specific artifact is safe to study, with
the scope recorded.

---

### A-008 — Documentation language: English

**Context.** The RFP is pt-BR; every normative document, ADR, `AGENTS.md`, and CI script in the tree
is English.

**Decision.** **English**, including this rewrite set. RFP-mandated filenames are kept verbatim
(Portuguese slugs included) because they are a contract; the three additional documents use English
slugs.

**Consequences.** One retrieval corpus in one language — AETHER's own indexer will read these files.
Mixed-language filenames are a cosmetic inconsistency accepted in exchange for honoring the RFP.

**Reversal Conditions.** A team or client requirement for Portuguese documentation.

---

### Still open — require a human or commercial answer

| # | Decision | Why it cannot be resolved here | Blocks |
| :--- | :--- | :--- | :--- |
| **Q3** | Model tier the client will fund | Drives the absolute score more than any engineering choice (R1). Recommendation: **mixed routing** — frontier for coding, cheap tier for planning and summarization | **A-006 absolute targets only — M4** |
| **Q6** | Private held-out benchmark repository | Requires a repository and a license. Must not be public | T3 contamination control — M3 |
| **Q8** | Compute budget for benchmarking | A full Pro run is not free | **M4 only** |

**These no longer gate M1b.** An earlier revision treated Q3/Q8 as blocking B2 and therefore the whole
plan. The **Tier 0** strategy retires that: a locally hosted open-weight model covers the noise floor,
the single-shot baseline, T1 scaffold lift, every ablation, and the head-to-head against real
competitor harnesses, at zero marginal cost. Lift is a paired delta on a *fixed* model — it needs a
constant model, not an expensive one. The commercial decision now buys the absolute headline number at
M4 and nothing before it.

---

## Part II — New AETHER decisions

### A-010 — Start with eight ports; add each with its first adapter

**Context.** SAGIHA declared 17 ports; **five have zero implementations** (`Orchestrator`, `LSPAdapter`,
`Toolchain`, `Advisory`, `MetaImprover`). The `Orchestrator` port — documented as the single headless
signature everything reduces to — was never called; `RunLoop` is invoked directly from three places.

**Decision.** AETHER starts with **eight ports**: `ModelProvider`, `Workspace` + `WorktreeManager`,
`ToolRegistry`, `PolicyEngine`, `TrajectoryStore`, `Evaluator`, `Indexer`, `ResourceGovernor`. **A new
port is added in the same change as its first adapter and its conformance test.** Supersedes
ADR-0019; strengthens ADR-0023 from a rent rule (demote after two idle blocks) to an entry rule.

**Consequences.** Fewer boundaries to maintain and no interface designed against an imagined adapter.
`CodeGraph`, `Memory`, `Toolchain`, `CandidateSearch`, `LSPAdapter`, `Advisory` enter as their
adapters land.

**Reversal Conditions.** A port with two independent adapters planned in the same phase may be
introduced ahead of the first, with the second named.

---

### A-011 — Streaming is required, not optional

**Context.** `ModelProvider.stream()` is declared on SAGIHA's port and raises `NotImplementedError` in
all three adapters; the conformance test its docstring names does not exist. Meanwhile the Best-of-N
cache sequencing in [context & cache §1.4](./rewrite_v300_contexto_memoria.md) *requires* awaiting a
first streamed token, and the TUI requires token-level output.

**Decision.** `stream()` ships with a working adapter and a real conformance test in **M1a**, or it is
not on the port. No declared-and-unimplemented methods.

**Consequences.** Higher M1a cost. Unblocks BoN cache economics and the TUI simultaneously.

**Reversal Conditions.** None. This is the loud-stub doctrine applied to a port method.

---

### A-012 — Explicit cache breakpoints; cache hit rate is a gated metric

**Context.** SAGIHA has a layered assembler and a `stable_prefix_digest` but emits **no `cache_control`
at all** — caching is implicit and positional. The `anthropic` extra is declared in `pyproject.toml`
with the comment "cache_control prompt caching, extended thinking" and has no code behind it.

**Decision.** Explicit breakpoints on a five-layer prefix, at most four per request, with the
per-model minimum-cacheable-prefix as a config value (512 / 1024 / 2048 / 4096 — **not monotonic**
across model generations). Cache hit rate is tracked, alerted, and carries a **CI floor**. The cost
model carries three rates: full input, write (1.25× / 2×), read (~0.1×). Full mechanics in
[context & cache](./rewrite_v300_contexto_memoria.md).

**Consequences.** A native Anthropic adapter is required, not optional. Prompt assembly becomes
constrained by cache stability rather than convenience.

**Reversal Conditions.** A provider-side change to caching semantics.

---

### A-013 — Anchored search/replace with anchor-sequence matching

**Context.** RFP §4-B. SAGIHA's `apply_edit` already requires `expected_occurrences`; it matches
anchors by exact string equality.

**Decision.** Anchored search/replace as the primary edit mechanism, with **required
`expected_occurrences`** and **anchor-sequence matching** — locating a hunk by its surrounding context
lines with whitespace tolerance, rather than by byte-exact block equality. Batch edits are
transactional. Read-before-write is enforced by policy. AST-scoped edits are secondary, for structural
refactors.

**Consequences.** Robust on real repositories rather than on the model's memory of them. A wrong
occurrence count is a loud failure instead of silent corruption.

**Reversal Conditions.** An ablation showing AST-scoped edits win on multi-file refactors.

---

### A-014 — Tree-sitter syntax validation, not `ast.parse`

**Context.** The RFP suggests `ast.parse` for deterministic post-edit validation. That is Python-only;
SWE-bench Pro is multi-language, and `tree-sitter` is already a dependency for indexing.

**Decision.** Tree-sitter parse of every touched file after every edit batch, before any expensive
suite. One parser serves both syntax validation and the repo map.

**Consequences.** Multi-language coverage with no new dependency. Rollback via git worktree
checkpoint/restore on parse failure.

**Reversal Conditions.** A language whose tree-sitter grammar is materially worse than a native
parser, for that language only.

---

### A-015 — No parsing of tool calls out of prose

**Context.** SAGIHA's `openai.py` regex-extracts tool calls emitted as text by weak local models. With
thinking disabled, current frontier models occasionally do the same — writing a call into visible text
that then silently never runs.

**Decision.** **The structured tool-call channel is the only channel that reaches dispatch.** A turn
producing neither a structured call nor a final answer is a **failed step** — visible, counted,
repaired — never silently rescued by a parser. Upstream mitigation: keep thinking enabled and lower
`effort` for cost rather than disabling thinking.

**Consequences.** Loses compatibility with models that cannot emit structured tool calls, which is an
acceptable trade for not maintaining a path around the [choke point](./rewrite_v300_seguranca_sandbox.md).

**Reversal Conditions.** None on the security property. A separate *validation-only* text scanner that
flags the failure without executing anything is permitted.

---

### A-016 — Architect/Editor split: seam built, shipped off

**Context.** RFP §4-B. The split roughly doubles per-task cost and introduces a lossy prose hand-off;
the evidence is mixed and frontier models emit correct anchored edits directly.

**Decision.** Add an `editor` model role to the config-level role→tier binding. **Ship it disabled.**
Enable only if an ablation on the smoke suite shows a resolve-rate gain whose CI excludes the noise
floor, at acceptable cost delta.

**Consequences.** Establishes the standing pattern for every contested mechanism: make it a
config-level ablation, ship it off, let the number decide (RFP §1.1).

**Reversal Conditions.** The ablation, in either direction.

---

### A-017 — Structural fix for evaluation isolation

**Context.** `s4-harvest-findings.md` D3: the editable install's `.pth` leaked the live `src/` into
every isolated worktree, making candidate diffs invisible to the gates scoring them. D1 and D2 are
companion instrument defects.

**Decision.** No editable install inside an evaluation container; the container's environment is built
from the task's own dependency specification; a **canary test asserts a deliberately broken candidate
fails**, proving the gate can see the candidate at all. Instrument failures are typed and excluded
from the denominator, never scored as task failures.

**Consequences.** An entire class of silently-wrong measurement becomes structurally impossible rather
than merely detected.

**Reversal Conditions.** None. This is the honesty rule applied to the isolation layer.

---

### A-018 — Compaction trigger is a measured parameter, not a copied constant

**Context.** Context rot is structural (n² attention scaling), and field reports place a **non-linear**
quality cliff near ~70% of budget used, with the effective window around 92% of the advertised one.
But shipped tools trigger auto-compaction at 75%, 92%, 95%, and "1–5% remaining" depending on surface.
Four credible sources, four different numbers, one mechanism.

**Decision.** The compaction trigger ships as a **config value defaulted below the reported cliff**,
and is settled by ablation on our own suites. Planning is done against the effective window, not the
advertised one. Compaction is preferred **earlier and less often** — repeated compression cycles lose
nuance and break references, so one well-timed compaction beats three late ones.

**Consequences.** No copied magic number. One more ablation to run, on a parameter that materially
moves both cost and resolve rate.

**Reversal Conditions.** Our own measurement placing the cliff elsewhere; a provider change to
attention or context handling.

---

### A-019 — Sub-agents: depth 1, scoped registry, explicit context passing

**Context.** Delegation is where multi-agent designs fail, and the failure is usually an assumption:
that sub-agents inherit context. They do not — in the dominant hub-and-spoke topology a worker
receives only its task string.

**Decision.** (a) **Depth capped at one level, enforced at the registry** — a sub-agent's tool set
excludes the delegation tool. Unbounded recursion, per-level context accumulation, undebuggable
chains, and unpredictable cost all compound. (b) A sub-agent receives a **scoped tool registry and its
own budget**; delegation never widens authority. (c) **The coordinator's context-passing is a
first-class mechanism** and an ablation target — what it forwards and how it compresses is where
delegated runs succeed or fail. (d) Best-of-N concurrency (zero shared state) and collaborative
delegation (coordination-taxed) get **separate settings**.

**Consequences.** No agent-spawning-agent topologies. Coordinator prompt design becomes a measured
component rather than an afterthought.

**Reversal Conditions.** A measured case where depth 2 beats decomposition at depth 1 on the same
budget — which would also require solving the cost-predictability problem.

---

### A-020 — Allowlist entries are capability grants; broad wildcards are a validation error

**Context.** Three documented escape vectors share one shape — a configuration that looks restrictive
and is not: an allowlisted CDN apex hosts attacker content (domain fronting); a socket glob grants
whatever daemon happens to listen there (`/var/run/docker.sock` is full host access); a writable
`$PATH` directory or shell rc file is deferred execution outside the sandbox.

**Decision.** Egress hosts, Unix sockets, and write paths are **deny-by-default and allowlisted
individually after audit**. Broad wildcards in any of the three lists are a **config validation
error**, not a style warning. Write scope is the worktree; `$PATH` directories and login-sourced files
are never writable. Egress is treated as **auditable, not airtight** — perfect blocking is impossible
without TLS inspection, and claiming otherwise is the dangerous part.

**Consequences.** More friction configuring an environment, in exchange for the allowlist meaning what
it appears to mean. Consistent with ADR-0006: the perimeter is enforced, and configuration cannot
silently widen it.

**Reversal Conditions.** None on the deny-by-default posture. Individual allowlist entries are always
revisable with an audit.

---

### A-021 — The compaction boundary is a trust boundary and an instruction channel

**Context.** A compaction summary re-enters the context as text the model reads. Forward-looking
headings in a summary (`## Next Steps`, `## Remaining Work`) are read as *current* directives, causing
the agent to wrap up finished work or revive historical to-dos. Separately, the summarizer is a model
reading a transcript containing repository content, tool output, and web results — all untrusted — and
anything that survives into the summary is laundered into the stable part of the context.

**Decision.** Summaries use **historical headings only**, are wrapped in an explicit
`REFERENCE ONLY` envelope, and carry an internal **precedence rule** (latest message wins over the
historical block). The summarizer preamble is **filter-safe** — prior turns are source material, never
instructions — and secret redaction is an explicit instruction. The compaction boundary is listed in
the TaintGate threat model. Supporting mechanics: tool-output pruning pre-pass, token-budget tail
protection, scaled summary budget, iterative summary updates, cheap auxiliary summarizer with a
startup feasibility probe, preflight and idle compaction.

**Consequences.** A more complex compactor than "summarize the middle". In exchange, compaction stops
being a silent second instruction source and a silent injection path.

**Reversal Conditions.** Envelope wording is an ablation parameter, not a constant — over-strengthening
it has been observed to suppress tool use entirely.

---

### A-022 — Loop guardrails are typed policy; API errors are a taxonomy

**Context.** SAGIHA halts on three identical tool signatures and classifies provider failures with
inline string matching. Neither distinguishes cases that need different responses.

**Decision.** (a) **Three guardrail signals** — exact repeated failure, same-tool repeated failure,
idempotent no-progress — each with its own warn and stop thresholds, reusing the existing effect-class
declaration for the idempotent/mutating split. The controller is **side-effect free** and returns
decisions; the runtime chooses guidance, synthetic result, or halt. Warnings are on by default; hard
stops are opt-in interactively and default-on autonomously. One failure classifier is shared with the
user-visible error rendering. (b) **API failures are a structured taxonomy** mapping to
`retry · rotate credential · failover · compress context · abort`, classified in one place. The
`ModelProvider` port surfaces a typed classified error, not a raw exception.

**Consequences.** More configuration surface. In exchange, thresholds are unit-testable without a
running agent, and "context too long" stops being handled as either a retry or a crash.

**Reversal Conditions.** Threshold values are ablation parameters throughout.

---

### A-023 — Auxiliary model calls run on the parent's prefix

**Context.** AETHER makes several model calls *about* a run rather than *in* it: the compaction
summarizer, the Best-of-N judge, background memory/skill review. Assembled independently, each pays a
cold cache write on a prefix nearly identical to one already warm.

**Decision.** Auxiliary calls **fork from the parent's live runtime** — same provider, model, base
URL, credentials and cached system prompt — and append their own tail, rather than constructing a
fresh prompt. They never mutate the main transcript. Background review specifically runs off the
critical path and writes to the memory and skill stores directly.

**Consequences.** Auxiliary work costs a cheap tail on a warm prefix instead of a full write. Couples
auxiliary calls to the parent's model choice, which is the intended trade — a different model would
invalidate the cache anyway, since caches are model-scoped.

**Reversal Conditions.** An auxiliary task genuinely requiring a different model tier; that call
accepts the cold-write cost explicitly and records it.

---

### A-024 — The walking skeleton is a graph; memoization is deferred

**Context.** The workflow DAG (ADR-0018, extended) is the one component in AETHER with **no reference
implementation** — no system in the study set applies a node graph to agent cognition. The original
roadmap placed it in M3, which is the worst position for an unproven abstraction: introduced late,
over code that already assumes a straight line, with retrofit cost paid exactly when the system is
most complex.

Two facts change the sequencing. A linear pipeline **is** a DAG with no branches, so exercising the
abstraction costs almost nothing at the start. And retrofitting a graph onto a pipeline is far more
expensive than starting with a trivial graph — the dependency direction is asymmetric.

**Decision.** Split the DAG across phases by cost rather than shipping it whole:

| Phase | What lands | Cost |
| :--- | :--- | :--- |
| **M0** | `WorkflowStep[In, Out]` — node and socket types only. No executor | Near zero |
| **M1a** | The walking skeleton runs as a **four-node linear graph** (`retrieve → generate → apply → evaluate`) through a trivial executor. Nodes execute unconditionally | Small |
| **M2** | **Per-node memoization keyed by input digest**, and partial re-execution | Real, and it pays for itself immediately |
| **M3** | Branching, fan-out, conditional paths — parallel candidates as graph structure | Real |

**M2 is where memoization earns its place, not earlier.** The project's core discipline is that no
mechanism promotes without an ablation, and an ablation re-runs a pipeline with one node changed.
Memoization turns that from a full re-execution into a subtree re-execution. The cost of running
ablations is therefore a first-order design concern, and this is the mechanism that pays it down —
which is only true once ablations are routine.

**Consequences.** The riskiest original component gets continuous exposure in its simplest form
instead of a late big-bang integration. Every phase after M1a is written against the graph, so nothing
accumulates a straight-line assumption. The cost is a small indirection in the walking skeleton, where
a direct function call would be simpler to read.

**Reversal Conditions.** If the node abstraction is still not carrying weight at the M2 boundary — no
memoization benefit measurable, no branching in sight — collapse it to a plain sequential pipeline.
The escape hatch stays open until M2 precisely because four nodes are cheap to un-abstract; forty
would not be.

---

### A-025 — Progressive benchmark tiers; competitors run as arms on our model

**Context.** §1's absolute targets need a frontier model, which needs a budget decision. Treating that
as a prerequisite puts an external approval on the critical path of an engineering project. Separately,
"beat the best published open scaffold" is a weak comparison: a published number carries a different
model, tool budget, retry policy and task pool than ours.

**Decision.** Three tiers, entered in order.

**Tier 0 — free, local, head-to-head.** A locally hosted open-weight model. Four arms on the *same*
model, tasks and hardware: pure single-shot LLM (**the floor**), AETHER, **Hermes** (**the target**),
and at least one more open scaffold. Competitor harnesses are pinned by commit, like the tasks. This
tier fully validates every instrument, the A/A noise floor, the baseline, **T1 lift**, and every
ablation.

**Tier 1 — sampled API.** An OpenRouter adapter and stratified samples, not full suites: an
intermediate signal at a fraction of the cost, and a second look at mechanisms that showed nothing at
Tier 0.

**Tier 2 — premium spot checks.** Small, isolated, deliberately non-statistical comparisons against
vendor CLIs on concrete artifacts, scored on quality, wall-clock, cost and tokens/second. Qualitative
calibration, never a headline.

Only after those does the full absolute run at frontier tier happen.

**Consequences.** Q3/Q8 leave the critical path and bind at M4. The head-to-head is stronger evidence
than any literature comparison — three confounds vanish when every arm runs the same model on the same
tasks on the same machine. Vendor CLIs cannot participate in Tier 0: they authenticate to their own
provider and are interactive subscription products, not programmable endpoints, so Claude Code and
Gemini CLI appear only at Tier 2.

**Reversal Conditions.** If Tier 0's resolve rates are so low that no mechanism produces a signal
distinguishable from the noise floor, the tier is uninformative and Tier 1 becomes the working floor —
at which point the budget decision returns to the critical path. Run the strongest locally hosted
model available before concluding this.

---

## Part IIb — Candidate records from the competitor and literature review

**Status: proposed, not accepted.** These arise from the four teardowns in
[`docs/competitors_research/tech_lead_A/`](../../competitors_research/tech_lead_A/rewrite_v300_synthesis_amendments.md)
and the 2026 harness literature verified in
[measurement §1c](./rewrite_v300_measurement_strategy.md). Each is stated at the density needed to be
argued about; a record the review accepts gets promoted into Part II with full Context / Decision /
Consequences / Reversal Conditions.

### A-026 — Typed run outcome, pause taxonomy, and the Receptivity invariant

**Context.** Five pause reasons exist across this document set and none share a type. An operator
watching an 8-hour run cannot distinguish "waiting on you" from "backing off".

**Proposed.** `RunOutcome = Completed | Paused{kind, message, clears_on} | BudgetLimited |
MaxTurnsReached | Cancelled | Failed{classified_error}`, with
`PauseKind = User | BackOff | NoProgress | Verification | Infra | Blocked`. Every terminal or degraded
state declares the event that would clear it (invariant **I11**, Receptivity). `MaxTurnsReached` is a
distinct variant — hitting a cap is not failing a task.

**Cost.** Near-zero at M0; a breaking change to every producer and consumer afterwards.

**Reversal.** If the taxonomy proves under-discriminating in practice, variants are additive; a closed
sum type makes the exhaustiveness check catch every consumer.

### A-027 — Effect replay provenance

**Proposed.** Effect-carrying events gain `replayed: bool`, and each effect family is classified
idempotent or not. A resumed run replays its journal; without the flag, every non-model effect fires
twice.

**Open question this forces.** We have not enumerated which of our effects are idempotent. That
enumeration is the actual work; the flag is one field.

### A-028 — Tool contract versioning; the version is a manifest field

**Context.** The project's defensible claim is scaffold-attributable lift — a paired delta on a *fixed*
model. That holds everything constant except the intervention. It does not currently hold the **tool
contract** constant.

**Proposed.** Tool descriptors carry a `contract_version`; a registry maps tool → supported versions
with lifecycle (`Active` / `Deprecated` / `RemovalCandidate`) and a one-line summary of what each
version's behaviour *is*. The active preset is recorded in every run manifest alongside model, effort
and retry policy. Amends [A-006](#a-006--benchmark-targets-pro--80-verified--96-lift-reported-alongside)
and measurement §7.

**Why now.** Free at M0. **Impossible to retrofit onto historical results** — a measurement taken
without it cannot be repaired later.

### A-029 — The completion verification cascade, and anti-ratchet as a gate property

**Context.** Our completion check is one `Evaluator.evaluate()`. Three references layer it at three
price points, and one names the failure mode that makes an adversarial gate non-terminating.

**Proposed.** A cost-ordered cascade (stop detector → evidence ledger → cheap structured evaluator →
adversarial panel, [edit mechanism §5b.1](./rewrite_v300_mecanismo_edicao.md)), plus a structural
**anti-ratchet** property: prior-round findings are passed forward and must be resolved, and novel
objections are a separate lower-priority channel. On a ≥8h unattended target this is a termination
property, not a quality one.

**Open.** How many tiers we build, and where the `VerificationLedger` lives — port, `TrajectoryStore`
table, or `Evaluator` internal. [A-010](#a-010--start-with-eight-ports-add-each-with-its-first-adapter)'s
entry rule argues against making it a port on principle alone.

### A-030 — Budget reservation under fan-out; tree-total accounting

**Context.** `ResourceGovernor` records spend after the fact. Under Best-of-N, N candidates each check
`remaining > 0`, all pass, all spend. Overrun bounded by N — the knob M4 increases.

**Proposed.** `reserve` / `commit` / `release` alongside the existing lease; turn caps keyed to task
class with `MaxTurnsReached` as a terminal state (A-026); the **tree total** recorded in the manifest,
since per-child budgets do not compose into a global cap; and iterations that consume no model call are
refunded.

**Open policy question.** When a reservation cannot be met mid-fan-out: degrade to fewer candidates, or
refuse the whole fan-out? That is policy, not mechanism.

### A-031 — `RunProfile`: rules versus skills, path scoping, disclosed staleness

**Context.** AETHER will answer "what kind of run is this?" in at least four forms — benchmark vs
interactive, container vs host, Tier 0 vs frontier, single-language vs polyglot. Absent a seam, that
question gets re-answered in eight places with eight slightly different answers, and a benchmark run
cannot pin its profile in the manifest.

**Proposed.** A resolved, **immutable** `RunProfile` where the profile is *data* — declaring toolset,
operating brief, model hint, memory policy, sub-agent defaults. With it: the rules-versus-skills
membership test, path-scoped instruction modules, and **disclosed staleness** for snapshot facts
(*"true at prompt-build time; re-check before acting"*) instead of cache-hostile per-turn refresh.
Detail in [context §5b.7](./rewrite_v300_contexto_memoria.md).

**Counter-evidence to weigh.** arXiv 2602.11988 measured that repository context files do not improve
resolve rate on average while costing >20% more, with generated files *hurting*. That is an argument
for *less* always-on instruction, not more — and A-031 is the mechanism that makes "less" targeted
rather than blunt.

### A-032 — Auto-denial limits and fail-closed authorization provenance

**Proposed.** Bounded consecutive and total auto-denials with explicit anti-circumvention guidance in
the denial message; `ask` gains provenance (rule-matched versus **fail-closed**, ranked); and any
config-derived authority store fails closed when its root cannot be located. Detail in
[security §6b.2–§6b.3](./rewrite_v300_seguranca_sandbox.md).

**Note.** ADR-0006 is **not** reopened. Shell AST analysis is proposed for *effect classification*
only, never containment.

### A-033 — Prefire compaction; rewriting sent history is cache-hostile

**Proposed.** Background pass-1 summarization at trigger −10 pp, validated by a prefix fingerprint,
with pass-2 synchronous over `NOTE₁` plus the tail; the split index snapped to tool boundaries
(invariant **I10**, Parity). Plus the standing rule that any mechanism rewriting already-sent history
converts cached reads into writes and must carry that multiplier into its ablation. Detail in
[context §5b.2–§5b.3](./rewrite_v300_contexto_memoria.md).

**Evidence.** Hermes ships the per-turn alternative **off by default** and documents why in its own
user guide. Two teams, one problem, opposite answers, one documented as a mistake by its authors.

### A-034 — OpenTelemetry as an export adapter, not a replacement surface

**Proposed.** The typed event stream remains the only observable surface (§7 of the blueprint). An
**export adapter** maps events to OTel spans — `run_id` as trace id, steps as spans, tool calls as
child spans carrying effect class and grant outcome — over OTLP/HTTP, with no vendor SDK in the core
(consistent with A-007(e)). Companion rule: every enum reaching telemetry declares a stable wire
string, pinned by a test, so renaming a Python member cannot break a dashboard.

**Why it is more than operational.** An 8-hour unattended run is unreadable as a flat event log. Span
nesting is what makes *"where did the four hours go"* answerable.

---

## Part III — Carrying forward the 27 existing ADRs

Every record in [`docs/08-decisions/`](../../08-decisions/README.md) is explicitly re-affirmed,
amended, or superseded. Silence is not a verdict.

| ADR | Verdict | Note |
| :--- | :--- | :--- |
| 0001 Project name | **Superseded** by A-001 | SAGIHA → AETHER |
| 0002 Ports speak domain language | Re-affirm | No untyped `dict` crosses a port |
| 0003 Conformance over `isinstance` | Re-affirm | Structural typing; reflection contracts |
| 0004 No DI container | Re-affirm | Explicit composition root |
| 0005 Best-of-N, not MCTS | Re-affirm | And its cost analysis is not voided by renaming the tree |
| 0006 Sandbox is the perimeter | Re-affirm | Blocklists are UX |
| 0007 Trusted Computing Base | Re-affirm | Strengthened: TCB immutable by the meta-loop too |
| 0008 Native SDKs, no LiteLLM | Re-affirm | Now means a **native Anthropic adapter** (A-012) |
| 0009 Python ≥3.13 and toolchain | Re-affirm | Consistent with A-002 |
| 0010 Defer exotic components | Re-affirm | The `research`-tier trigger discipline |
| 0011 Split code and episodic graphs | Re-affirm | Structured code vs. unstructured memory |
| 0012 Record/replay determinism | Re-affirm | T8: 100% byte-equality |
| 0013 Extension registration via entry points | Re-affirm | Resolved once, then frozen |
| 0014 Defer dense retrieval | Re-affirm | recall@10 trigger, not a date |
| 0015 Benchmark target repository | **Amended** by A-006 | Pro is primary; lift published alongside |
| 0016 Container runtime: rootless Podman | Re-affirm | One backend of a cross-platform abstraction |
| 0017 Execution profiles | Re-affirm | Profiles mount fewer ports |
| 0018 Native `WorkflowStep` DAG | Re-affirm, **extended** | Adds per-node memoization keyed by input digest |
| 0019 Port consolidation 24→19 | **Superseded** by A-010 | Start at 8; add with the adapter |
| 0020 Per-invocation effect classification | Re-affirm | `classify_command` |
| 0021 Seed-only layer-6 retrieval | Re-affirm | Construction-time only; never invalidates the prefix |
| 0022 RHI economic refounding | Re-affirm | Tiers A/B/C |
| 0023 Port rent rule | Re-affirm, **strengthened** | From an exit rule to an entry rule |
| 0024 `e0/` is a tool, not a port | Re-affirm | Measurement is not an agent capability |
| 0025 CandidateSearch seams | Re-affirm | — |
| 0026 `Indexer.search()` replaces `neighbors()` | Re-affirm | — |
| 0027 Fixed chunk-size policy | Re-affirm | `max_chunk_tokens` removed |

The ADR index README is stale — it stops at 0025 while 0026 and 0027 exist, and `docs/README.md`
still says "18 decisions". Both need updating when this set promotes.

---

## Part IV — Standing declines (not re-litigated)

`planning_future_sprints.md` §3 evaluated these and the conclusions hold. Re-opening one requires new
evidence, not a new opinion.

| Verdict | Items |
| :--- | :--- |
| **Decline** | LangGraph · Temporal.io · Neo4j / NetworkX · Redis short-term memory · DI container with dynamic plugin discovery |
| **Defer** | Ray · LanceDB / sqlite-vec (behind ADR-0014's trigger) · MCTS (ADR-0005) · server-side compaction (until our compactor has a baseline to compare against) |
| **Adopt** | DuckDB · Promptfoo · Inspect AI behind the `Evaluator` port · SWE-bench Pro as the primary screen |

The common thread in the Decline column: each replaces an explicit, inspectable mechanism with a
framework that owns the control flow. For a system whose entire value proposition is that every
mechanism is measured and ablatable, that is the wrong trade — a mechanism inside a framework is one
we cannot turn off to find out whether it helps.
