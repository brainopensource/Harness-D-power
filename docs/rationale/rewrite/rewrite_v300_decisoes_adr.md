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
(a) Only official and open-source trees are cloned. (b) De-obfuscated or decompiled artifacts of
closed CLIs are **deferred, not permanently excluded** — bringing one in would be a separate,
explicitly recorded decision with its own legal review, never a silent one. (c) Any design change that
converges on a competitor's choice must be justified by **our own KPIs** — an ablation on our suites,
against our noise floor, recorded in `docs/rationale/benchmarks/`. (d) Dependencies are open-source
only, license class reviewed on addition.

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
| **Q3** | Model tier the client will fund | Drives the absolute score more than any engineering choice (R1). Recommendation: **mixed routing** — frontier for coding, cheap tier for planning and summarization | A-006 absolute targets |
| **Q6** | Private held-out benchmark repository | Requires a repository and a license. Must not be public | T3 contamination control |
| **Q8** | Compute budget for benchmarking | A full Pro run is not free; sets CI tiering | M1b onward |

**Q3 and Q8 together gate B2** — no model endpoint means no measurement, which means M1b cannot exit.
These are the highest-priority external dependencies in the plan.

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
