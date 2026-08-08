---
status: proposal
updated: 2026-08-08
---

# AETHER v3.0.0 — Sprints 6 to 10 Master Execution Plan & Architecture Seam

## Executive Summary & Strategic Vision Alignment

This document is the **Master Technical Reference** for planning, implementing, and evaluating **Sprints 6 through 10** of AETHER v3.0.0 (Milestones M2-eng, M3, M4, and M5). It serves as the baseline for generating individual sprint development prompts (`sprint-06-dev-prompt.md` through `sprint-10-dev-prompt.md`) and establishes pre-vs-post evaluation metrics for complex coding benchmark tasks.

### 1. Vision Horizons (`docs/vision.md`)
- **H1 (Harness Calibration — Sprints 6–9)**: Build a calibrated measurement instrument (noise floor, derived $N$, paired lift) before publishing leaderboard claims.
- **H2 (Framework Decoupling — Sprint 10)**: Decouple task types (`code_fix`, `qa`, `explanation`), dynamic execution strategies, and front-end event streaming.
- **H3 (Meta-Loop — Post-Sprint 10)**: Autonomous topology mutation (`src/aether/evolution/`) under strict TCB isolation.

### 2. Front-End Bridge Integration (`docs_front/BRIDGE_CONTRACT.md`, `docs_front/spec.md`)
All backend workflow, state, budget, and gate events stream over the Event Bus (`src/aether/kernel/bus.py` / `src/aether/engine.py`) to `@aether/core` front-end consumers (`apps/cli` Ink TUI, `apps/desktop` Tauri + React Flow GUI) without violating Invariant **FI1** (zero direct imports of `src/aether` inside `src_front`).

---

## Core System Architectural Patterns Matrix

| Pattern Name | Architectural Purpose | Primary Backend Module | Primary Front-End Seam (`@aether/core`) |
| :--- | :--- | :--- | :--- |
| **Port-Adapter Boundary** | Isolates I/O behind wire-serializable `Protocol` classes | `src/aether/ports/` & `src/aether/adapters/` | `AetherWebsocketClient`, `MockCassettePlayer` |
| **Capability Authorization (CAR)** | Single choke point dispatch with pre-effect verification | `src/aether/kernel/dispatch.py`, `policy.py` | `useTaintAudit`, `TaintAuditBadge` |
| **Workflow DAG as Data** | Declarative YAML topologies validated statically | `src/aether/workflow/validator.py`, `executor.py` | `useWorkflowStore` (React Flow node canvas) |
| **Unified Capability Model** | Consolidated LLM execution via `RoleSpec` + `ModelNode` | `src/aether/agency/roles.py`, `nodes/model_node.py` | `useNodeTrace`, `<TurnLogStream />` |
| **Layered Context Assembly** | Byte-stable L1–L5 prompt prefix construction | `src/aether/agency/context/assembler.py` | Prompt inspector drawer in GUI |
| **Event Stream Bridge** | Pub/Sub event catalog streaming over WebSocket/SSE | `src/aether/kernel/bus.py`, `engine.py` | `useEngineStore`, `useAetherStream` |

---

## Sprint-by-Sprint Technical Specifications & Before/After Comparison

### 🚀 Sprint 6: Engine Efficiency, Memoization & Compaction (Milestone M2-eng)

#### 1. Objective & Feature Block
Eliminate redundant LLM calls across DAG iterations, enforce 5-layer prompt prefix caching (L1–L5), compact long dialogue histories, and decouple reasoning from editing via the Architect/Editor seam.

#### 2. Architecture & Design Patterns Used
- **Memoization Decorator / Interceptor**: Hashes node inputs `sha256(node_kind, impl_version, payload)` in `WorkflowExecutor`.
- **Compactor Pattern**: Structural dialogue history pruner operating exclusively on Layer 5.
- **Strategy Pattern**: Swappable `EditFormat` (`unified_diff`, `whole_file_codeblock`, `search_replace`).

#### 3. Key Code File Paths

##### Backend Source Files to Edit / Create:
- `src/aether/workflow/executor.py` — Digest-based node result memoization (`TASK-032`).
- `src/aether/agency/context/assembler.py` — Five-layer prompt prefix assembler (`TASK-031` / `TASK-056`).
- `src/aether/agency/context/compactor.py` *(New)* — Dialogue history compactor (`TASK-024`).
- `src/aether/agency/roles.py` — Architect (`ARCHITECT`) and Editor (`EDITOR`) role specs (`TASK-025`).
- `src/aether/agency/capabilities/inference.py` — Consecutive identical call loop detector (`TASK-069`).

##### Backend Test Files to Create / Run:
- `tests/aether/workflow/test_memoization.py` — Subtree cache invalidation tests.
- `tests/aether/agency/test_compactor.py` — L5 context window compaction tests.
- `tests/aether/agency/test_architect_editor_seam.py` — Dual-model routing integration test.
- `tests/aether/agency/test_loop_detection.py` — Repeated tool call short-circuit tests.

##### Front-End Integration Points (`docs_front/`):
- `packages/core/stores/useWorkflowStore.ts` — Memoized nodes render with cached badge (`is_cached: true`).
- `packages/core/stores/usePatchStore.ts` — Diff updates from `EDITOR` node routed directly to code diff drawer.

#### 4. Before vs. After Feature Comparison Matrix

| Dimension | Before Sprint 6 Baseline | Post-Sprint 6 Implementation |
| :--- | :--- | :--- |
| **Node Re-execution** | Unchanged nodes re-invoke model on every repair loop turn. | Input-digest match skips model call in <5ms with cached output. |
| **Context Window** | Multi-turn history grows linearly until token window exhaustion. | L5 Compactor prunes superseded snapshots while keeping L1–L4 prefix immutable. |
| **Role Topologies** | Single monolithic model handles planning and editing. | `ARCHITECT` (reasoning model) produces plan; `EDITOR` (coding model) emits patch. |
| **Looping Behavior** | Retries identical failing tool calls until budget wall. | Loop detector terminates run clean with `StopReason("loop_detected")` after 3 repeats. |

#### 5. Task Breakdown & Complexity Tiers

| Task ID | Component / Task Name | Complexity Tier | Justification |
| :--- | :--- | :---: | :--- |
| `TASK-032` | Per-Node Digest Memoization | **Tier 3** (Medium) | DAG traversal invalidation logic; must never reuse stale outputs downstream. |
| `TASK-024` | Dialogue Context Compactor | **Tier 3** (Medium) | Compaction logic strictly bounded to L5; type system forbids touching L1–L4. |
| `TASK-025` | Architect/Editor Dual-Model Seam | **Tier 3** (Medium) | Dual-model routing integration over `RoutingModelProvider`. |
| `TASK-069` | Turn Budget & Loop Detection | **Tier 2** (Easy) | In-memory count check inside `ToolLoop.invoke()`. |

---

### ⚡ Sprint 7: Dynamic Branching, Fan-Out & Candidate Ranking (Milestone M3)

#### 1. Objective & Feature Block
Support multi-candidate DAG branching (Best-of-$N$), budget lease tree management, candidate ranking under Invariant **I9**, and role-level capability attenuation (ADR-0017).

#### 2. Architecture & Design Patterns Used
- **Composite Lease Tree**: Hierarchical child lease reservation in `ResourceGovernor`.
- **Type-Level Separation (I9)**: Proxy `Ranker` outputs `CandidateRanking`, while TCB `Evaluator` outputs `GateReport`.
- **Barrier Synchronization**: Cache-sequenced fan-out warming candidate 1 prefix before releasing candidate 2..$N$.

#### 3. Key Code File Paths

##### Backend Source Files to Edit / Create:
- `src/aether/workflow/validator.py` & `executor.py` — Fan-out (`fan_out`) and join (`join`) node topology support (`TASK-035`).
- `src/aether/kernel/governor.py` — Hierarchical child lease reservation and parent refunding (`TASK-035`).
- `src/aether/measurement/ranker.py` *(New)* — Proxy candidate ranker (`TASK-067`).
- `src/aether/workflow/nodes/model_node.py` — Cache-sequenced candidate fan-out dispatch (`TASK-033`).
- `src/aether/workflow/dispatch_facade.py` — RoleSpec capability attenuation wrapper (`TASK-068`).

##### Backend Test Files to Create / Run:
- `tests/aether/workflow/test_fan_out.py` — Parallel candidate fan-out & join execution tests.
- `tests/aether/measurement/test_ranker_i9.py` — Assert type system prevents `CandidateRanking` from passing as `GateReport(PASSED)`.
- `tests/aether/agency/test_cache_sequencing.py` — Candidate 1 prefix warming test.
- `tests/aether/agency/test_role_attenuation.py` — Assert restricted role (e.g. `architect`) cannot invoke shell execution.

##### Front-End Integration Points (`docs_front/`):
- `packages/core/stores/useWorkflowStore.ts` — React Flow canvas renders parallel branch edges and join nodes.
- `packages/core/stores/useMetricsStore.ts` — Renders candidate rank scores and Best-of-$N$ selection confidence.

#### 4. Before vs. After Feature Comparison Matrix

| Dimension | Before Sprint 7 Baseline | Post-Sprint 7 Implementation |
| :--- | :--- | :--- |
| **DAG Structure** | Pure linear DAG with single-path repair unrolling. | Multi-candidate parallel branching with explicit join and conditional routing. |
| **Candidate Selection**| First passing attempt is accepted; no multi-candidate ranking. | Best-of-$N$ candidate ranker ranks candidates by test pass counts prior to admission. |
| **Prefix Caching** | Naive parallel model requests compete cold against provider. | Candidate 1 warms shared prefix before candidates 2..$N$ issue requests. |
| **Role Authority** | All nodes possess identical access to facade capabilities. | `RoleSpec.permitted_effect_classes` narrows facade authority per node. |

#### 5. Task Breakdown & Complexity Tiers

| Task ID | Component / Task Name | Complexity Tier | Justification |
| :--- | :--- | :---: | :--- |
| `TASK-035` | Graph Fan-Out & Lease Trees | **Tier 4** (Hard) | Concurrency, child lease tree allocation, and parent refund accounting. |
| `TASK-067` | Candidate Ranker (I9) | **Tier 4** (Hard) | Invariant I9 type separation ensuring soft proxies never override hard gates. |
| `TASK-033` | Best-of-N Cache Sequencing | **Tier 3** (Medium) | Async dispatch barrier ordering. |
| `TASK-068` | Capability Attenuation per Role | **Tier 3** (Medium) | `DispatchFacade` method attenuation wrapper. |

---

### 🔒 Sprint 8: Security, AST Classification & Budget Choke (Milestones M2/M3)

#### 1. Objective & Feature Block
Enforce untrusted taint propagation (Invariant **I11**), classify shell commands via `tree-sitter-bash` AST to prevent capability widening, and move dollar ceiling checks to dispatch reservation.

#### 2. Architecture & Design Patterns Used
- **AST Visitor Pattern**: `tree-sitter-bash` AST traversal inspecting shell execution nodes.
- **Taint Tracker / Provenance Chain**: Monotone bit-flag propagation across data spans (`UNTRUSTED_EXTERNAL`).
- **Fail-Closed Guard**: Policy engine choke point rejecting unbudgeted or untrusted capability escalation.

#### 3. Key Code File Paths

##### Backend Source Files to Edit / Create:
- `src/aether/kernel/ast_classifier.py` *(New)* — Bash AST classifier (`TASK-030a`).
- `src/aether/domain/taint.py` & `src/aether/kernel/policy.py` — Untrusted taint span propagation and predicate checks (`TASK-030b`).
- `src/aether/kernel/dispatch.py` — Dollar ceiling (`usd_micros`) reserve-time choke point (`TASK-045`, `TASK-044`).
- `src/aether/engine.py` — Cleanup unused/legacy step registrations (`TASK-046`).

##### Backend Test Files to Create / Run:
- `tests/aether/kernel/test_ast_classifier.py` — Tests for `sudo`, `curl`, subshell escaping detection.
- `tests/fixtures/red_team_corpus.json` — Pinned prompt-injection adversarial test corpus.
- `tests/aether/kernel/test_taint_propagation.py` — Tests asserting `UNTRUSTED_EXTERNAL` spans flag outputs.
- `tests/aether/kernel/test_dollar_budget_choke.py` — Tests asserting reserve-time budget denial.

##### Front-End Integration Points (`docs_front/`):
- `packages/core/stores/useTaintStore.ts` & `useTaintAudit.ts` — Real-time taint provenance visualizer badges.
- `packages/core/stores/useBudgetStore.ts` — Dollar reservation vs. committed ledger meters.

#### 4. Before vs. After Feature Comparison Matrix

| Dimension | Before Sprint 8 Baseline | Post-Sprint 8 Implementation |
| :--- | :--- | :--- |
| **Shell Inspection** | Command strings executed verbatim without AST analysis. | `tree-sitter-bash` AST inspects commands for capability-widening patterns. |
| **Taint Tracking** | Taint spans created but `UNTRUSTED_EXTERNAL` label not enforced. | Taint provenance propagates monotonically; untrusted spans block unsafe effects. |
| **Budget Enforcement**| Dollar overrun debited post-execution (after expenditure). | Monetary budget checked at `reserve()` time; over-budget requests fail immediately. |

#### 5. Task Breakdown & Complexity Tiers

| Task ID | Component / Task Name | Complexity Tier | Justification |
| :--- | :--- | :---: | :--- |
| `TASK-030a` | Shell AST Classifier | **Tier 4** (Hard) | Parsing bash ASTs safely requires handling aliases, pipelines, and subshells. |
| `TASK-030b` | TaintGate Provenance & Red-Team | **Tier 5** (Very Hard) | High security blast radius; tested against adversarial red-team injection corpus. |
| `TASK-045` | Dollar Budget Choke Point | **Tier 3** (Medium) | Kernel dispatch choke point ledger update. |
| `TASK-044` | Dollar Budget Reservation | **Tier 2** (Easy) | Pre-execution calculation check. |
| `TASK-046` | Reflector Step Cleanup | **Tier 1** (Very Easy) | Code hygiene and step registry cleanup. |

---

### 📊 Sprint 9: Benchmark Scale, SWE-bench Noise Floor & Lift (Milestone M4)

#### 1. Objective & Feature Block
Scale manifests to real SWE-bench Verified/Pro instances, execute the benchmark-specific A/A noise floor run, perform paired lift evaluations against baselines and OpenHands, and publish results on the `SEALED` split.

#### 2. Architecture & Design Patterns Used
- **Paired Evaluation Harness**: Synchronized execution of treatment vs. baseline arms on identical containerized worktrees.
- **Statistical Gatekeeper**: Exact McNemar test calculator enforcing Holm–Bonferroni correction ($\alpha = 0.05$).
- **Content-Addressed Benchmark Manifest**: Immutable task dataset pinned by SHA256 checksum.

#### 3. Key Code File Paths

##### Backend Source Files to Edit / Create:
- `scripts/build_floor_manifest.py` — Manifest generation with issue problem statements (`TASK-071`).
- `scripts/run_aa_floor.py` — SWE-bench A/A variance floor runner (`TASK-072`).
- `src/aether/measurement/runner.py` — Paired lift runner for bare-model vs AETHER (`TASK-073`).
- `src/aether/adapters/evaluator/openhands_adapter.py` *(New)* — OpenHands evaluation arm adapter (`TASK-015b`).
- `docs/benchmarks/results/sealed_publication_report.md` *(New)* — Sealed publication report (`TASK-074`).

##### Backend Test Files to Create / Run:
- `tests/aether/measurement/test_swe_bench_manifest.py` — Manifest validation and canary tests.
- `tests/integration/test_paired_lift.py` — Integration test for paired McNemar statistics calculation.

##### Front-End Integration Points (`docs_front/`):
- `packages/core/stores/useMetricsStore.ts` — Statistical lift charts, McNemar $p$-values, confidence intervals.
- `<GateStatusIndicator />` — Tri-state rendering for benchmark instance reports (`PASSED` / `FAILED` / `NONE`).

#### 4. Before vs. After Feature Comparison Matrix

| Dimension | Before Sprint 9 Baseline | Post-Sprint 9 Implementation |
| :--- | :--- | :--- |
| **Manifest Scale** | Small internal manifest (`internal-floor-01.yaml`, 84 synthetic tasks). | Pinned SWE-bench Verified & Pro manifest with complete problem statements. |
| **Noise Calibration**| Internal dry-run variance measured; SWE-bench noise unmeasured. | Benchmark-specific A/A floor executed, deriving exact $p_{01}, p_{10}$ and $N$. |
| **Lift Comparison** | Lift claims anecdotal / unverified against competitors. | Rigorous paired lift statistics vs. bare-model and OpenHands harnesses. |
| **Data Split** | `DEV` / `HOLDOUT` split only. | `SEALED` split evaluated adhering to all 7 conditions of `measurement.md` §6. |

#### 5. Task Breakdown & Complexity Tiers

| Task ID | Component / Task Name | Complexity Tier | Justification |
| :--- | :--- | :---: | :--- |
| `TASK-071` | SWE-bench Manifest Scale | **Tier 3** (Medium) | Dataset transformation and container canary screening. |
| `TASK-072` | SWE-bench A/A Floor Run | **Tier 4** (Hard) | Large-scale automated execution and variance derivation. |
| `TASK-073` | Paired Lift (Bare vs AETHER) | **Tier 4** (Hard) | Paired McNemar evaluation engine. |
| `TASK-015b` | OpenHands Evaluation Arm | **Tier 5** (Very Hard) | Adapting third-party harness into TCB evaluation container without leakage. |
| `TASK-074` | SEALED Split Publication Run | **Tier 3** (Medium) | Formal publication verification and checksum generation. |

---

### 🤖 Sprint 10: Meta-Loop, Macro Fragments & Live Telemetry (Milestone M5)

#### 1. Objective & Feature Block
Establish pluggable `ExecutionStrategy` implementations, topology macro fragments, real-time event telemetry streaming, and a read-only terminal UI over the event bus.

#### 2. Architecture & Design Patterns Used
- **Strategy Pattern**: Pluggable graph traversal routines (`SequentialStrategy`, `BranchingStrategy`).
- **Macro Expansion Pattern**: YAML topology fragment import and inline expansion prior to validation.
- **Publish-Subscribe Event Bridge**: Non-blocking event streaming channel serving external TUI/GUI clients.

#### 3. Key Code File Paths

##### Backend Source Files to Edit / Create:
- `src/aether/workflow/strategy.py` *(New)* — Pluggable `ExecutionStrategy` interface and registry (`TASK-059`).
- `src/aether/workflow/validator.py` — Macro fragment expansion and validation (`TASK-060`).
- `src/aether/domain/telemetry.py` *(New)* — Telemetry event definitions (`TASK-063`).
- `src/aether/clients/tui.py` *(New)* — Read-only terminal interface (`TASK-075`).

##### Backend Test Files to Create / Run:
- `tests/aether/workflow/test_execution_strategies.py` — Custom strategy execution tests.
- `tests/aether/workflow/test_macro_fragments.py` — YAML macro expansion & validation tests.
- `tests/aether/clients/test_tui.py` — Event bus consumption and TUI state rendering tests.

##### Front-End Integration Points (`docs_front/`):
- `src_front/apps/cli/` — React 19 + Ink TUI implementation consuming `@aether/core`.
- `packages/core/client/AetherWebsocketClient.ts` — Live WebSocket connection handling streaming telemetry.

#### 4. Before vs. After Feature Comparison Matrix

| Dimension | Before Sprint 10 Baseline | Post-Sprint 10 Implementation |
| :--- | :--- | :--- |
| **Graph Traversal** | Hard-coded sequential DAG traversal in `WorkflowExecutor`. | Modular `ExecutionStrategy` registry allowing custom traversal patterns. |
| **Topology Declarations**| Single monolithic YAML topology files. | Modular YAML files supporting reusable macro fragment imports. |
| **Operator Visibility** | Engine logs printed to stdout/stderr or written to SQLite DB. | Streaming WebSocket telemetry feeding live terminal TUI and desktop GUI. |

#### 5. Task Breakdown & Complexity Tiers

| Task ID | Component / Task Name | Complexity Tier | Justification |
| :--- | :--- | :---: | :--- |
| `TASK-059` | `ExecutionStrategy` Registry | **Tier 4** (Hard) | Abstracting DAG traversal while preserving lease & choke point invariants. |
| `TASK-060` | Topology Macro Fragments | **Tier 4** (Hard) | Macro expansion must preserve static validation safety before execution. |
| `TASK-063` | Live Log Telemetry Stream | **Tier 2** (Easy) | Non-blocking event stream publisher. |
| `TASK-075` | Read-Only Bus TUI | **Tier 2** (Easy) | Terminal UI event consumer layer. |

---

## Summary Roadmap & Developer Reference

```
Sprints 1–5 (Completed)         Sprints 6–10 (Planning Phase)
[M0: Core Domain & Ports]  ──>  [Sprint 6: Memoization, Compactor & Dual-Model (M2-eng)]
[M1a: Walking Skeleton]    ──>  [Sprint 7: Graph Fan-Out, Ranker & Attenuation (M3)]
[M1a+: Bounded Repair]     ──>  [Sprint 8: AST Classifier, TaintGate & Dollar Choke (M2/M3)]
[M1a++R: Restoration]      ──>  [Sprint 9: SWE-bench Manifest, A/A Floor & Lift (M4)]
[M1b: Agency & ModelNode]  ──>  [Sprint 10: Meta-Loop Strategies & Bus TUI (M5)]
```

### Transition to Individual Sprint Dev Prompts
When ready to begin a sprint:
1. Copy the targeted sprint section from this document.
2. Create `docs/agile/sprints/sprint-XX-dev-prompt.md`.
3. Fill in the exact Definition of Done, test command lines (`uv run pytest`), and target file paths specified herein.
