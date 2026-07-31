---
status: historical
retrieval: excluded
---
# NEXT-GEN HARNESS ARCHITECTURE SPEC — SAGIHA v2 Blueprint

**Status:** Proposed evolution of the audited `Harness-D-power` architecture. This spec *retains* the validated core (CAR layering, capability grants, hexagonal ports, record/replay, E0 statistics) and *rewrites* what the audit found broken, missing, or mis-sequenced. Section references `(→ Audit Wx / R-x)` point at the companion `CRITICAL_GAP_ANALYSIS_AND_AUDIT.md`.

**Design invariants carried forward unchanged (non-negotiable):**
1. Sandbox is the security perimeter; blocklists are UX.
2. Repository/web content is data, never instruction; provenance survives storage round-trips.
3. A candidate never scores itself; `tests_unmodified` is a hard gate; gates admit, scores rank.
4. No `dict[str, Any]` crosses a port; ports speak domain language; contracts live in `src/` only.
5. No claim without a benchmark, no accept/reject without an A/A noise floor.

---

## 1. Refined System Architecture

### 1.1 Layer model (CAR, amended)

```
┌────────────────────────────────────────────────────────────────────────┐
│ PILOTS  (CLI/TUI · IDE-MCP · CI headless · remote A2A — thin clients)  │
├────────────────────────────────────────────────────────────────────────┤
│ CONTROL   PolicyEngine · ResourceGovernor · Gates · TaintGate(new)     │
│           Budget & approval ledger · TCB (never agent-writable)        │
├────────────────────────────────────────────────────────────────────────┤
│ AGENCY    Inner Loop (DMARTIC) · Story-DAG scheduler (macro)           │
│           ContextAssembler + Compactor(new) · CandidateSearch          │
│           No imports of runtime/ or adapters/ (CI-enforced)            │
├────────────────────────────────────────────────────────────────────────┤
│ KERNEL    Single dispatch choke point · EventBus · record/replay       │
│           (mechanism only — owns no policy, no reasoning)              │
├────────────────────────────────────────────────────────────────────────┤
│ RUNTIME   Container sandbox (Podman, rootless) · Worktrees · LSP pool  │
│           MCP drivers · egress proxy — the only layer with effects     │
└────────────────────────────────────────────────────────────────────────┘
```

Amendments to the existing model:

- **Kernel is named as a fourth explicit stratum.** The current tree treats it implicitly ("the dispatch choke point"); making it explicit clarifies that EventBus/replay/dispatch are *mechanism* shared by all layers and belong to none — which is why the Meta-loop may never mutate them (TCB membership).
- **`TaintGate` joins Control** (→ W8/R-7): a hard gate over diff *content*, not just diff mechanics. Rules (v1, deterministic, no LLM judge in the gate): (a) any `EditRequest` emitted within a taint window of EXTERNAL-provenance context is flagged `tainted=True` and requires `request_approval` at every autonomy level; (b) diffs introducing new network endpoints, new dependencies, disabled lint/type suppressions, or modified CI config are gate failures unless the `TaskSpec` explicitly authorizes that category. Taint is tracked as a boolean on trajectory steps, set when EXTERNAL content enters context and cleared at compaction of that span — coarse, cheap, and fail-closed.

### 1.2 Port surface (consolidated: 21 → 15)  (→ R-15)

Keep, unchanged: `ModelProvider`, `PolicyEngine`, `ResourceGovernor`, `Memory`, `Indexer`, `CodeGraph`, `LSPAdapter`, `Workspace`, `WorktreeManager`, `ToolRegistry`, `TrajectoryStore`, `Toolchain`, `Evaluator`, `Orchestrator`, `MetaImprover` (retained as spec, dormant — §6).

Consolidations:

| Removed / merged | Into | Rationale |
| :--- | :--- | :--- |
| `ShortTermMemory` | (deleted — already done, R7) | History is loop-local state, not a port. |
| `Reviewer` | `CandidateSearch.evaluate()` scoring inputs | A soft score that only ranks is an input to selection, not a boundary. One fewer versioned contract; the frontier-judge/never-self-judge rules move to `CandidateSearch` conformance tests. |
| `EmbeddingProvider` | Adapter-internal to `Memory`/`Indexer` | Already invisible to consumers by design; a port nobody outside an adapter may call is a module, not a port. Re-promote iff ADR-0014's trigger fires *and* two stores need to share one embedder. |
| `RewardPredictor` / `FailurePredictor` / `CostPerformanceEstimator` | Single `Advisory` port: `predict(kind, features) -> Prediction` | Three shadow-mode rankers with identical shape and identical constraints (never admit/reject) are one port with a kind discriminator. |

**Port stability policy unchanged** (provisional/experimental/stable, earned by adapters + conformance), with one addition: a port with zero non-test adapters for two consecutive blocks is automatically demoted to `experimental` and listed for deletion review — ports must pay rent.

### 1.3 Configuration schema (single file, layered, TOML)

TOML is retained over YAML deliberately (the repo's existing choice): no implicit typing footguns, no anchors/aliases indirection, `tomllib` in stdlib. The brief's requirement is *declarative, schema-validated, hot-swappable composition* — the format is incidental; the schema is normative and validated by the same Pydantic models that refuse insecure states today.

```toml
# sagiha.toml — the entire composition surface. build_kernel(config) reads only this.
[profile]                    # execution profile selects which ports are mounted
name        = "coding"       # coding | analysis | review | chat
autonomy    = "interactive"  # interactive | hybrid | autonomous | scheduled
gates       = "coding"       # coding | none   (none ⇒ no GateReport exists)

[model.roles]                # role → tier binding; callers request roles, never models
planning    = "frontier"
execution   = "workhorse"
compaction  = "fast"
scoring     = "frontier"     # candidate scoring judge; MUST differ from execution
[model.tiers.frontier]  provider = "anthropic"          model = "…"
[model.tiers.workhorse] provider = "anthropic"          model = "…"
[model.tiers.fast]      provider = "anthropic"          model = "…"
[model.tiers.local]     provider = "openai-compatible"  model = "…"  base_url = "http://localhost:11434/v1"
mode = "live"                # live | record | replay  — honored by composition (D3 regression-tested)

[context]                    # §3 — normative numbers, not code
headroom_pct        = 20
keep_first_turns    = 2
keep_last_tokens    = 24_000   # token-budgeted, whole-exchange granularity (replaces keep-last-6 turns)
retrieval_authority = "agentic" # seed-only Layer 6; mid-task retrieval is tool-driven (→ W3)

[budget]
max_usd_per_run     = 5.00
max_steps_per_run   = 120
max_wall_clock_s    = 3600

[search]                     # System 2 (§4)
n_candidates        = 3
prune_on_first_gate_fail = true
repair_attempts     = 2

[sandbox]
runtime   = "podman-rootless"
egress    = ["pypi.org", "files.pythonhosted.org", "github.com"]  # proxy allowlist, namespace-enforced
# subprocess dev-mode is only legal with autonomy = "interactive"; validated at load, refused otherwise

[workflow]                   # macro layer (§5) — order is composition, steps are swappable
pipeline  = ["prd", "stories", "schedule", "code", "verify"]

[telemetry]
otel_exporter = "none"       # none | otlp   — TrajectoryStore always on; OTel optional extra
trace_export  = { sft = true, min_gate = "admitted" }   # §6 dataset pipeline
```

Hot-swap semantics: config is resolved **once** at `build_kernel` (ADR-0004 preserved — no runtime DI); "hot" means a new run picks up a new config, never a running kernel mutating. Extensions register via entry points, resolved once then frozen (ADR-0013 preserved).

---

## 2. Dual-Loop Engine Specification

### 2.1 Inner Loop (runtime) — DMARTIC, amended

The eight-stage cycle (Design→Measure→Analyze→Review→Test→Improve→Control→Self-Reflect) is retained; three amendments:

**A. Failure-disposition ladder is normative (→ R-13).** Stuck-signature detection already exists; its consequence is now specified as a budget-aware ladder, each rung consuming from `[budget]`:

```
detect(stuck | EditRejected×k | ContextOverflow)
  1. rehydrate     — re-insert affected files in full (compaction rollback)  [cheap]
  2. replan        — one planning-role call to restate approach              [1 frontier call]
  3. escalate      — System 1 → System 2 via the escalation ladder           [N× cost]
  4. checkpoint+abort — commit worktree, park run resumable, surface to human
```
No rung may repeat; the ladder is monotonic. Disposition transitions emit typed events (`RecoveryEscalated`) so E0 can measure recovery efficacy per rung.

**B. Retrieval authority ruling (→ W3, normative).** Layer 6 pre-assembled retrieval is **seed-only**: computed once at task start, closed under the Layer-7 cache breakpoint, never refreshed mid-task. All subsequent retrieval is agentic (tool calls, tail-resident). Consequence: the semi-stable layers become *stable-per-task*, mid-task cache invalidation events reduce to exactly one class (compaction), and cache hit rate becomes a clean regression signal.

**C. Per-invocation effect classification (→ W5).** `ToolRegistry` gains a pure-argv allowlist (`ls`, `cat`, `git status|diff|log|show`, `grep`, `pytest --collect-only`, …). `run_command` invocations matching it are recorded `PURE` and re-executed on `replay --verify`, restoring re-verification for the majority of real steps. Anything unmatched stays `DESTRUCTIVE`. The allowlist is TCB (agent-unwritable).

### 2.2 Context engine & compactor (pulled forward — implements now)  (→ R-2, W4, R-8)

Prompt layout unchanged (stability-ordered, breakpoints after Layers 4 and 7). Compactor spec, superseding R9's turn-count policy:

1. **Unit of compaction is the *exchange*** — one assistant message plus all its paired `tool_result`s (and any signed reasoning block). Boundaries never fall inside an exchange; provider block-pairing is preserved by construction.
2. **Keep policy is token-budgeted:** keep-first-2 exchanges verbatim (intent anchor) + most recent exchanges up to `keep_last_tokens`, whole exchanges only. Middle span → one synthetic summary turn produced by the `compaction` model role, tagged in the trajectory (`CompactionApplied` event with span digests) so replay distinguishes model speech from compactor speech.
3. **Anchored artifacts survive outside the transcript:** `TaskSpec` + acceptance criteria (Layer 5), plan state (Layer 7), and two lifted artifacts — the *open-file set* (files with edits this run) and *unresolved diagnostics* — are structured state re-rendered every assembly, never entrusted to the summary.
4. **Trigger:** headroom < `headroom_pct` of model window, checked pre-assembly, never mid-turn. If total tail ≤ keep budgets, no-op.
5. **Verification:** conformance tests assert (a) post-compaction request is provider-valid (no orphan tool_results, reasoning blocks intact or wholly dropped with their exchange), (b) EXTERNAL provenance re-wraps in `<untrusted-data>` after summarization (extends the existing laundering test to the compactor path — the summary of untrusted content is untrusted).

### 2.3 Outer Loop — Meta-Harness, economically re-founded  (→ W6, R-11)

The outer loop splits into three mechanisms ordered by cost; only the first two are scheduled work:

**Tier A — Prompt & config regression CI (continuous, ~$10s/run).** Prompts are versioned artifacts already; every PR touching `src/sagiha/prompts/` or `[context]`/`[search]` config triggers the pinned suite once, paired against baseline, judged against the stored A/A floor with multiple-comparison correction. Red = merge blocked. This is 90% of "self-improvement's" defensive value at CI cost.

**Tier B — Trace mining (per-bench-run, near-zero marginal cost).** Post-run jobs over the `TrajectoryStore`:
- *Exemplar mining:* gate-admitted trajectories clustered by task class; top-k become few-shot exemplars in a versioned exemplar library, injected into Layer 5 per task class. Exemplars are prompt artifacts ⇒ Tier A gates their adoption.
- *Failure taxonomy:* `GateReport`-failed runs labeled by terminal error class (from the error taxonomy), feeding a ranked "what actually kills runs" report — the empirical input the old Meta-Improver was supposed to intuit.
- *Dataset export:* §6.

**Tier C — Mutation search (dormant, trigger-gated).** The full Meta-Improver + four-tier verification gauntlet is retained as spec, TCB constraints and human sign-off intact, behind an explicit trigger: *sustained eval budget ≥ $2k/month or a sponsoring deployment*. Until then it is `rationale/`, not roadmap.

The **telemetry-driven evolution** contract is thereby honest: every run improves the system through Tiers A/B mechanically; Tier C is the research option, not the load-bearing claim.

---

## 3. DAG Orchestration Engine (macro layer)  (→ W10)

Retains ADR-0018's two constraints — native `WorkflowStep` protocol (no LangGraph/Temporal), and the E0 ablation gate (planning must beat no-planning or the layer does not ship) — and upgrades the linear pipeline to a genuine story-DAG.

### 3.1 Node & edge model

```python
# ports/workflow.py  (experimental until adapters exist)
class WorkflowStep(Protocol[In, Out]):        # In/Out: BaseModel
    name: str
    async def execute(self, ctx: StepContext, input_data: In) -> Out: ...

class PipelineRunner(Protocol):
    async def run(self, dag: StoryDAG) -> AsyncIterator[Event]: ...
```

```
Prompt ─▶ PRDGeneratorStep ─▶ StoryDecomposerStep ─▶ StoryDAG
                                                        │
                     ┌──────────────────────────────────┤ scheduler
                     ▼                                  ▼
               CodingStep(story_i)  ∥  CodingStep(story_j)   … parallel where file-set
                     │                                  │      closures are disjoint AND
                     ▼                                  ▼      no dependency edge exists
               VerifierStep ──rejected──▶ re-scope (back to decomposer, story-local)
                     │accepted
                     ▼
               IntegrationStep(new) — rebase story branch onto moving base; on conflict
                                      or closure-invalidation ⇒ re-plan that story only
```

- `StoryDAG = (stories: dict[id, StorySpec], deps: set[(id, id)])`. The decomposer emits dependency edges explicitly (interface-before-consumer, migration-before-usage); disjoint closures without edges are schedulable concurrently, each in its own worktree under `ResourceGovernor` admission.
- **`IntegrationStep` is the new, load-bearing node:** parallel stories land against a moving base. Policy: rebase story branch onto current base; re-run the story's gates post-rebase (gates are cheap relative to re-implementation); if the rebase invalidates the story's file-set closure, the story returns to the board — never silent merge.
- Steps hold no tool references, mint no Grants, call no provider outside `ModelProvider` — the existing `agency/` restriction, unchanged. Each step boundary persists output to `TrajectoryStore` and emits events ⇒ pipelines are resumable at step granularity and cassette-replayable, same as the inner loop.

### 3.2 A2A protocol interface

Adoption trigger unchanged (a genuinely remote peer must exist first), but the *shape* is fixed now so the pilot layer and `spawn_subagent` converge on it:

- A remote peer is addressed as an `Orchestrator` adapter over A2A: it accepts a `TaskSpec`, streams typed `Event`s, terminates in a `GateReport` (or none, per profile). Identical contract local and remote — remoteability rule 4 already guarantees the payloads serialize.
- Delegation semantics are grant-monotonic: a delegated task carries a strict subset of the delegator's grants and an explicit budget slice; the receiving kernel's own `PolicyEngine` may narrow further, never widen. `request_approval` from a remote peer routes to the *originating* human, through the same durable, deny-on-timeout gate.
- Sub-agents (`spawn_subagent`) are the degenerate local case of the same contract — one protocol, two transports.

---

## 4. System 2 — Candidate Search, hardened  (→ R-10)

Best-of-N + sequential repair retained (ADR-0005). Additions:

1. **Early termination:** with `prune_on_first_gate_fail = true`, a candidate is killed at its first hard-gate failure signal (first failing pristine test, first `tests_unmodified` violation) rather than run to completion; its worktree is released immediately. Expected spend reduction is measured by E0, not assumed.
2. **Staggered launch:** candidates launch with a short stagger; if candidate 1 admits cleanly with margin above the PRM threshold, remaining launches are cancelled (bandit-flavored, but deterministic policy — no learned router until label volume exists, per the existing cold-start doctrine).
3. **Judge separation is config-enforced:** `[model.roles].scoring` must resolve to a different model than `execution`; `build_kernel` refuses the config otherwise (same mechanism as existing security refusals).

---

## 5. Runtime & capability roadmap corrections

**Block 5 is decomposed** (→ R-9) — sandbox is not a peer of MCP and streaming; it is the precondition for the autonomy levels the whole design targets:

| New block | Contents | Exit gate |
| :--- | :--- | :--- |
| **B5a — Perimeter** | Rootless Podman sandbox, worktree materialization inside it, egress proxy + namespace firewall, secret exclusion | `autonomous` autonomy legal; injection canary suite (planted hostile README/issue/test-fixture instructions) shows zero out-of-worktree effects across the pinned suite |
| **B5b — Ecosystem** | MCP stdio→HTTP-SSE client, tools registered `trusted_output=False`, warm LSP pool | External tool round-trip under grant + envelope; LSP diagnostics latency budget met |
| **B5c — Experience** | Streaming TUI, mid-run interrupt/steer (interrupt = durable checkpoint + replan, reusing the recovery ladder), `sagiha init` (→ W12: generates AGENTS.md from code-graph + toolchain detection) | Interrupt round-trip < 2s to a steerable state; init produces a Layer-4 file the pinned suite measurably benefits from (E0 ablation) |
| **B5d — Multimodal** | `ContentBlock` image kind, screenshot ingestion for UI-verification tasks | deferred behind a trigger: first task class requiring it |

**Memory:** deterministic auto-links only (record→files-touched, record→task, record→superseder), derived from the trajectory at `remember` time — no LLM edge inference (→ W11). `neighbors`/`backlinks` land on the port as the flagged S2 version bump when the first graph-capable adapter ships.

**Docs governance (→ W1):** normative word budget ≤ 15k; additions require equal deletions; everything else demoted to `rationale/` and excluded from default agent retrieval scope. ADRs exempt.

---

## 6. Trace → Fine-Tuning Dataset Pipeline (new, spec-complete)  (→ W7)

Every ingredient exists; this composes them. Runs as a Tier-B post-processing job — zero inner-loop cost.

**Selection.** Export unit = one run. Eligibility: `GateReport.admitted == true` ∧ replay-verified (`sagiha replay --verify` green) ∧ cost within budget ∧ `tainted == false` on every step (→ §1.1 — never train on injection-window behavior).

**Transformation.** For each step, reconstruct the exact assembled request from the trajectory (prompt version + layers + tail digests make this exact, not approximate — this is the replay machinery reused) and pair it with the model's emitted message:

```
sample = {
  "messages": [system, …context…, assistant(tool_use|text)],   # provider-neutral schema
  "tools":    canonical tool schemas at that step,
  "labels":   { gate_report, step_score, cost_usd, prompt_version, harness_version, model }
}
```
- **SFT set:** all steps of admitted runs.
- **Preference set (DPO/RLAIF-ready):** System-2 runs are natural preference pairs — the admitted winner vs. gate-failed siblings *on the identical prefix* (same TaskSpec, same seed context). This is the highest-value byproduct of best-of-N and costs nothing extra.
- Reasoning blocks: excluded when provider terms prohibit distillation-bearing export; the exporter takes a per-provider policy flag and defaults to exclusion. Local-tier (Tier 4) traces carry no restriction.

**Hygiene.** Secret-redaction pass (same scanner as the log path) re-applied at export; EXTERNAL-provenance spans excluded wholesale; dedup by request digest; per-repo license gate (exports only from repos whose license permits derivative training data, recorded per sample).

**Consumption.** `sagiha export --format sft|dpo --min-gate admitted` emits JSONL; the Tier-4 local slot (Qwen-class) is the intended first consumer, closing the loop the vision names: *the harness's verified work product improves the open-weight model that runs inside it* — a self-improvement claim that is mechanical, cheap, and TCB-safe, unlike mutation search.

---

## 7. Prioritized Action Plan

Ordered by (risk retired × user-visible delta) ÷ cost. Each item names its exit gate; nothing ships on calendar.

| # | Action | Scope | Exit gate | Retires |
| :- | :--- | :--- | :--- | :--- |
| 1 | **Compactor implementation** per §2.2 (exchange-granular, token-budgeted, anchored artifacts) | `agency/context/` + conformance tests | 200-step synthetic run completes under a 128k window; provider-validity + provenance tests green | R-2, R-8, W4 |
| 2 | **Retrieval-authority ruling** (seed-only Layer 6) — one doc PR + one assembler assertion | docs + `ContextAssembler` | Cache-hit-rate metric emitted per run; no mid-task Layer-6 writes possible by construction | R-3, R-4, W3 |
| 3 | **Per-invocation PURE allowlist** for `run_command` | `ToolRegistry` + replay | `replay --verify` re-executes ≥60% of steps on the pinned suite | R-5, W5 |
| 4 | **Trace→dataset exporter** (§6) | `outer_loop/export/` | `sagiha export` emits schema-valid SFT+DPO JSONL from existing bench cassettes | W7 |
| 5 | **Block 3 as planned** (best-of-N) with §4 pruning + judge-separation config refusal | `agency/search/` | S3 gate: BoN beats single-shot > A/A floor; zero grader modifications; pruning spend delta reported | — |
| 6 | **TaintGate v1** (§1.1) before any non-interactive autonomy outside a sandbox | Control + gates | Injection canary suite: 0 tainted diffs land without approval | R-7, W8 |
| 7 | **B5a Perimeter** (sandbox first, alone) | Runtime | §5 exit gate; `autonomous` unlocked | R-6, R-9 |
| 8 | **Block 4** (FTS5 + code graph + `sagiha init`) — init moves here from B5c: it is a retrieval consumer | Indexer/CodeGraph | S2 gate: recall@10 target + retrieval-beats-none ablation; init ablation positive | W12 |
| 9 | **Story-DAG macro layer** (§3), *iff* ADR-0018's planning-beats-no-planning ablation passes | `agency/workflow/` | E0 ablation positive incl. `IntegrationStep` under 2-way parallelism | W10 |
| 10 | **B5b/B5c** (MCP, LSP pool, streaming/interrupt) | Runtime/pilots | Per-block gates in §5 | matrix gaps |
| 11 | **RHI Tier A regression CI** (cheap, immediate) — runs from #5 onward; **Tier C archived** behind funding trigger | CI | Prompt-PR suite wired; ADR amending RHI economics recorded | R-11, W6 |
| 12 | **Docs shrink program** (§5 governance) | docs | Normative mass ≤ 15k words; retrieval scope excludes `rationale/` by default | W1, R-1 |

**Explicitly de-prioritized:** frontend sprints (fe-1…fe-7) until B5c; dense retrieval (ADR-0014 stands); MCTS/PRM-guided search (ADR-0005 stands, PRM data accrues from #5); A2A transport (trigger stands, contract fixed in §3.2); quantization, Kùzu, sidecars, Redis, graph daemons (ADR-0010 stands — every one behind its measured trigger).

---

## 8. Closing position

The audit's synthesis holds: **freeze the contract layer, shrink the prose layer, rebuild the plan around the capability layer.** The three implemented differentiators — capability-grant security, digest-verified replay, and the statistical evaluation harness — are the parts no competitor has and the parts this spec touches least. Everything added here (compactor, taint gate, story-DAG with integration semantics, dataset pipeline, economically honest outer loop) is composed from primitives the architecture already paid for, which is the strongest available evidence that the hexagon was drawn correctly. The system earns the word "self-evolving" the day `sagiha export` output measurably improves the Tier-4 model on the E0 suite — a falsifiable claim, with a threshold, on a benchmark. That is the standard this tree set for itself; this spec keeps it.
