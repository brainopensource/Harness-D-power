---
status: historical
retrieval: excluded
updated: 2026-08-01
---
# SAGIHA v0.3.0 — Sprints Execution Plan, Dependencies & Developer Prompts

**Basis:** [development_plan_v2.md](development_plan_v2.md) · [refactor_sagiha_v2_guidelines.md](refactor_sagiha_v2_guidelines.md)  
**Purpose:** Delegation playbook with difficulty ranking, time estimates, dependency wave mapping, explicit documentation sharing guides, and ready-to-use developer prompts for AI/human developers.

---

## 1. Master Difficulty Ranking & Delegation Summary

| Rank | Sprint ID & Name | Required Skill Tier | Senior Dev Time | Files | Est. LOC | Dependency Prerequisites |
| :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **1** | **v2-S0**: Docs Shrink, SSOT & Governance | **Tier 0** *(Junior Dev)* | 4–6 hrs | ~35 files | ~400 | None |
| **2** | **v2-S1**: Instrument Honesty *(Gates, Cost, Syntax, Stubs)* | **Tier 1** *(Average Dev)* | 12–16 hrs | ~15 files | ~700 | v2-S0 |
| **3** | **v2-S2**: Port Consolidation & Kernel Corrections | **Tier 2** *(Senior Dev)* | 16–24 hrs | ~22 files | ~1,000 | v2-S1 |
| **4** | **v2-S6**: Retrieval, Code Graph & Cold-Start | **Tier 2** *(Senior Dev)* | 24–32 hrs | ~18 files | ~1,500 | v2-S3, v2-S4 |
| **5** | **v2-S5**: Perimeter & Isolation *(Container Sandbox)* | **Tier 3** *(Specialist Dev)* | 28–40 hrs | ~15 files | ~1,300 | v2-S3, v2-S4 |
| **6** | **v2-S3**: Context Engine & Safety *(Compactor & TaintGate)* | **Tier 3** *(Specialist Dev)* | 32–48 hrs | ~25 files | ~1,800 | v2-S1, v2-S2 |
| **7** | **v2-S4**: Measurement Re-Baseline & Best-of-N | **Tier 3–4** *(Specialist/PhD)* | 40–56 hrs | ~28 files | ~2,200 | v2-S1, v2-S2, v2-S3 |
| **8** | **v2-S7**: Story-DAG, MCP Client & Steerable TUI | **Tier 4** *(PhD / CTO)* | 48–64 hrs | ~32 files | ~3,000 | v2-S4, v2-S5, v2-S6 |

---

## 2. Required Documentation Sharing Matrix by Wave & Sprint

Provide the assigned developer (human or autonomous agent) with these exact files before they begin their sprint:

| Wave | Sprint ID & Name | Required Documentation to Share with Developer |
| :--- | :--- | :--- |
| **Wave 1** | **v2-S0**: Docs Shrink & Governance | - [refactor_sagiha_v2_guidelines.md §4](refactor_sagiha_v2_guidelines.md#4-phase-0--docs-governance-and-the-ssot)<br>- [development_plan_v2.md §Sprint v2-S0](development_plan_v2.md#sprint-v2-s0--docs-shrink-ssot-consolidation-decision-records)<br>- [docs/README.md](../README.md) (Taxonomy & Sitemap)<br>- [docs/STATUS.md](../STATUS.md) (Capability matrix) |
| **Wave 2 (Track A)** | **v2-S1**: Instrument Honesty *(H1–H4)* | - [refactor_sagiha_v2_guidelines.md §2.1 & §5](refactor_sagiha_v2_guidelines.md#21-the-honesty-defects-h-series)<br>- [development_plan_v2.md §Sprint v2-S1](development_plan_v2.md#sprint-v2-s1--instrument-honesty-gates-cost-syntax-stubs)<br>- [docs/reviews/codebase_delta_refactor.md](../rationale/reviews/codebase_delta_refactor.md) (H1–H4 findings)<br>- [docs/03-contracts-and-models/domain-schemas.md](../03-contracts-and-models/domain-schemas.md)<br>- [docs/04-workflows-and-loops/dmartic-inner-loop.md](../04-workflows-and-loops/dmartic-inner-loop.md) |
| **Wave 2 (Track B)** | **v2-S2**: Port Consolidation & Kernel | - [refactor_sagiha_v2_guidelines.md §6](refactor_sagiha_v2_guidelines.md#6-phase-2--port-consolidation-and-kernel-corrections)<br>- [development_plan_v2.md §Sprint v2-S2](development_plan_v2.md#sprint-v2-s2--port-consolidation--kernel-corrections)<br>- [docs/03-contracts-and-models/hexagonal-ports.md](../03-contracts-and-models/hexagonal-ports.md)<br>- [docs/02-architecture/car-model.md](../02-architecture/car-model.md)<br>- [ADR-0019](../08-decisions/0019-port-consolidation.md), [ADR-0020](../08-decisions/0020-per-invocation-effect-classification.md), [ADR-0023](../08-decisions/0023-port-rent-rule.md) |
| **Wave 3** | **v2-S3**: Context Engine & Safety | - [refactor_sagiha_v2_guidelines.md §7](refactor_sagiha_v2_guidelines.md#7-phase-3--context-engine-and-safety-compactor-taintgate-frozenrunstate)<br>- [development_plan_v2.md §Sprint v2-S3](development_plan_v2.md#sprint-v2-s3--context-engine--safety-compactor-taintgate-frozenrunstate)<br>- [docs/02-architecture/context-and-cache-engineering.md](../02-architecture/context-and-cache-engineering.md)<br>- [docs/02-architecture/prompt-architecture.md](../02-architecture/prompt-architecture.md)<br>- [docs/02-architecture/security-and-threat-model.md](../02-architecture/security-and-threat-model.md) (T7)<br>- [docs/03-contracts-and-models/frozen-run-state.md](../03-contracts-and-models/frozen-run-state.md)<br>- [ADR-0021](../08-decisions/0021-seed-only-layer-6-retrieval.md) |
| **Wave 4 (Track A)** | **v2-S4**: Measurement & Best-of-N | - [refactor_sagiha_v2_guidelines.md §8](refactor_sagiha_v2_guidelines.md#8-phase-4--measurement-re-baseline-and-best-of-n)<br>- [development_plan_v2.md §Sprint v2-S4](development_plan_v2.md#sprint-v2-s4--measurement-re-baseline--best-of-n-block-2--block-3)<br>- [docs/04-workflows-and-loops/rhi-outer-loop.md](../04-workflows-and-loops/rhi-outer-loop.md)<br>- [docs/04-workflows-and-loops/trace-distillation.md](../04-workflows-and-loops/trace-distillation.md)<br>- [ADR-0005](../08-decisions/0005-best-of-n-not-mcts.md), [ADR-0022](../08-decisions/0022-rhi-economic-refounding.md) |
| **Wave 4 (Track B)** | **v2-S5**: Container Sandbox & Perimeter | - [refactor_sagiha_v2_guidelines.md §9](refactor_sagiha_v2_guidelines.md#9-phase-5--perimeter-and-isolation-container-sandbox)<br>- [development_plan_v2.md §Sprint v2-S5](development_plan_v2.md#sprint-v2-s5--perimeter--isolation-b5a)<br>- [docs/02-architecture/security-and-threat-model.md](../02-architecture/security-and-threat-model.md)<br>- [ADR-0006](../08-decisions/0006-sandbox-is-the-perimeter.md), [ADR-0016](../08-decisions/0016-container-runtime-podman.md) |
| **Wave 5** | **v2-S6**: Retrieval & Code Graph | - [refactor_sagiha_v2_guidelines.md §10](refactor_sagiha_v2_guidelines.md#10-phase-6--retrieval-code-graph-and-cold-start)<br>- [development_plan_v2.md §Sprint v2-S6](development_plan_v2.md#sprint-v2-s6--retrieval-code-graph--cold-start-block-4)<br>- [docs/02-architecture/context-and-cache-engineering.md](../02-architecture/context-and-cache-engineering.md)<br>- [ADR-0011](../08-decisions/0011-split-code-and-episodic-graphs.md), [ADR-0014](../08-decisions/0014-defer-dense-retrieval.md) |
| **Wave 6** | **v2-S7**: Story-DAG & MCP Client | - [refactor_sagiha_v2_guidelines.md §11](refactor_sagiha_v2_guidelines.md#11-phase-7--story-dag-mcp-client-and-interactive-surface)<br>- [development_plan_v2.md §Sprint v2-S7](development_plan_v2.md#sprint-v2-s7--story-dag-mcp--interactive-surface-block-4-macro--b5bc)<br>- [docs/04-workflows-and-loops/workflow-orchestration-and-dags.md](../04-workflows-and-loops/workflow-orchestration-and-dags.md)<br>- [docs/03-contracts-and-models/protocols-mcp-a2a.md](../03-contracts-and-models/protocols-mcp-a2a.md)<br>- [ADR-0018](../08-decisions/0018-native-workflow-dag.md) |

---

## 3. Wave Execution Flow & Parallel Dependencies

```
  [ Wave 1 ] ──► Sprint v2-S0 (Docs Shrink & SSOT Consolidation)
                      │
  [ Wave 2 ] ──► ┌────┴──────────────────────────┐
                 │ Sprint v2-S1 (Dev A)         │ Sprint v2-S2 (Dev B)
                 └────┬──────────────────────────┘
                      │
  [ Wave 3 ] ──► Sprint v2-S3 (Specialist / Dev A - Context Engine & TaintGate)
                      │
  [ Wave 4 ] ──► ┌────┴──────────────────────────┐
                 │ Sprint v2-S4 (Dev A)         │ Sprint v2-S5 (Dev B - Security/Infra)
                 └────┬──────────────────────────┘
                      │
  [ Wave 5 ] ──► Sprint v2-S6 (Dev A / Dev B - Code Graph & Retrieval)
                      │
  [ Wave 6 ] ──► Sprint v2-S7 (CTO / Dev A - Story-DAG & MCP Client)
```

---

## 4. Developer Execution Prompts by Wave

Use these exact copy-paste prompts to delegate tasks to your AI agents or engineering team members.

---

### Wave 1 — Documentation & Normative Governance
> **Target Tier:** Tier 0 (Junior Developer)  
> **Estimated Senior Dev Effort:** 4–6 hrs (0.5 days)  
> **Prerequisites:** None  
> **Scope:** `docs/` and `scripts/` only (Zero `src/` modifications allowed).

#### Developer Prompt (Sprint v2-S0):
```text
You are acting as a Junior Developer / Technical Lead assigned to implement Sprint v2-S0 described in docs/implementation/development_plan_v2.md.

REQUIRED READING & DOCUMENTATION TO SHARE:
- refactor_sagiha_v2_guidelines.md (§4 Phase 0)
- docs/implementation/development_plan_v2.md (Sprint v2-S0)
- docs/README.md (Documentation Taxonomy & Sitemap)
- docs/STATUS.md (Capability Baseline Matrix)

CORE INVARIANTS:
- Scope is strictly docs/ and scripts/ ONLY. ZERO edits or additions to src/ or tests/.
- Enforce normative word ceiling <= 15,000 words mechanically via scripts/docs_budget.py.

OBJECTIVES:
1. Epic S0.1: Ensure scripts/docs_budget.py validates normative markdown word counts (ceiling 15,000 words). Update frontmatter status to 'rationale' for non-normative derivation files.
2. Epic S0.2: Reorganize legacy rationale files into docs/rationale/ with 'retrieval: excluded' frontmatter. Verify relative links pass scripts/check_links.py. Update docs/README.md sitemap.
3. Epic S0.3: Update normative architecture specs (context-and-cache-engineering.md, security-and-threat-model.md, rhi-outer-loop.md) to encode seed-only Layer 6 retrieval, exchange compaction, and TaintGate v1. Add frozen-run-state.md and trace-distillation.md specs.
4. Epic S0.4: Verify ADR-0019 through ADR-0023 in docs/08-decisions/ carry explicit reversal conditions and are indexed in docs/08-decisions/README.md.
5. Epic S0.5: Re-baseline docs/STATUS.md with honest capability disclosures for v2 sprint series (v2-S0 to v2-S7).

VERIFICATION GATES:
- python3 scripts/docs_budget.py --max 15000 (exits 0)
- python3 scripts/check_links.py (exits 0)
- git status --short src/ tests/ (empty output)
```

---

### Wave 2 — Core Honesty & Port Refactoring (Parallel Wave)
> **Prerequisites:** Wave 1 (v2-S0) complete.  
> **Dev A & Dev B Day-1 Sync:** Agree on `ModelProvider` v2 interface (`complete() -> Completion(message, usage, model)`).

#### Developer Prompt — Track A (Sprint v2-S1):
> **Target Tier:** Tier 1 (Average Developer)  
> **Estimated Senior Dev Effort:** 12–16 hrs (1.5–2 days)

```text
You are acting as Dev A (Tier 1 Developer) assigned to implement Sprint v2-S1 in docs/implementation/development_plan_v2.md.

REQUIRED READING & DOCUMENTATION TO SHARE:
- refactor_sagiha_v2_guidelines.md (§2.1 H-series defects & §5 Phase 1)
- docs/implementation/development_plan_v2.md (Sprint v2-S1)
- docs/reviews/codebase_delta_refactor.md (H1–H4 audit findings)
- docs/03-contracts-and-models/domain-schemas.md (TokenUsage, CostSummary, Completion models)
- docs/04-workflows-and-loops/dmartic-inner-loop.md (RunLoop execution context)

CORE INVARIANTS:
- Do NOT mask gate drops. Benchmark pass rates will drop when real gates stop lying — record before/after numbers in docs/rationale/benchmarks/.
- GateEvaluator (src/sagiha/outer_loop/evaluator/) is TCB code — changes must be author-verified.

OBJECTIVES:
1. Epic S1.1 (H1): Fix gate dishonesty in src/sagiha/outer_loop/evaluator/gate_evaluator.py. Implement real git diff checks (tests_unmodified, diff_within_bounds, no_new_suppressions) against base_commit.
2. Epic S1.2 (H2): Implement ModelProvider v2 complete() signature in src/sagiha/ports/model.py and adapters/model/openai.py. Wire record_spend() in src/sagiha/kernel/governor.py and emit real TokenUsage / CostSummary.
3. Epic S1.3 (H4): Add AST pre-write check (ast.parse) in src/sagiha/adapters/workspace/local.py returning syntax_valid=False on SyntaxError without writing to disk.
4. Epic S1.4 (H3): Invert stubs in adapters/sandbox/container.py, adapters/mcp/driver.py, and adapters/telemetry/otel.py to raise explicit NotImplementedError.
5. Epic S1.5: Re-measure baseline harness metrics (sagiha bench --aa) before and after S1.1 merge; commit reports.

VERIFICATION GATES:
- pytest tests/ -q (127+ tests passing)
- Gate dishonesty e2e test fails admission on test file edits
- Smoke run emits non-zero spend telemetry
```

#### Developer Prompt — Track B (Sprint v2-S2):
> **Target Tier:** Tier 2 (Senior Developer)  
> **Estimated Senior Dev Effort:** 16–24 hrs (2–3 days)

```text
You are acting as Dev B (Senior Developer) assigned to implement Sprint v2-S2 in docs/implementation/development_plan_v2.md.

REQUIRED READING & DOCUMENTATION TO SHARE:
- refactor_sagiha_v2_guidelines.md (§6 Phase 2)
- docs/implementation/development_plan_v2.md (Sprint v2-S2)
- docs/03-contracts-and-models/hexagonal-ports.md (Hexagonal Port specification)
- docs/02-architecture/car-model.md (Capability authorization model)
- docs/08-decisions/0019-port-consolidation.md (ADR-0019)
- docs/08-decisions/0020-per-invocation-effect-classification.md (ADR-0020)
- docs/08-decisions/0023-port-rent-rule.md (ADR-0023)

CORE INVARIANTS:
- Ports are pure typed Protocols in src/sagiha/ports/ with zero internal imports.
- PURE command allowlists live inside TCB (src/sagiha/kernel/policy/effects.py).

OBJECTIVES:
1. Epic S2.1: Consolidate ports (24 Protocols -> 15). Delete reviewer.py, embedding.py, and ShortTermMemory protocol. Refactor advisory.py to Advisory.predict().
2. Epic S2.2: Implement PURE command classification in src/sagiha/kernel/policy/effects.py. Update ToolRegistry v2 effect_for_call.
3. Epic S2.3: Fix builtins in adapters/tools/builtins.py (remove app/ path-strip hack, add write_file, reclassify apply_edit as DESTRUCTIVE).
4. Epic S2.4: Derive tool_schemas directly from BUILTIN_SCHEMAS in composition.py. Enforce judge-separation refusal in composition configuration.
5. Epic S2.5: Persist assistant Message on TrajectoryStep in domain/trajectory.py and trajectory adapters for clean resume/replay.

VERIFICATION GATES:
- pytest tests/contracts/test_port_shape.py (exactly 15 active ports, zero dangling imports)
- lint-imports passes 5/5 contract checks
- pyright src/sagiha reports 0 errors
```

---

### Wave 3 — Context Engine & Safety Substrate (Sequential Bottleneck)
> **Target Tier:** Tier 3 (Specialist Developer — AI Safety & Systems)  
> **Estimated Senior Dev Effort:** 32–48 hrs (4–6 days)  
> **Prerequisites:** Wave 2 (v2-S1 & v2-S2) complete.

#### Developer Prompt (Sprint v2-S3):
```text
You are acting as a Lead Systems & Security Specialist assigned to implement Sprint v2-S3 in docs/implementation/development_plan_v2.md.

REQUIRED READING & DOCUMENTATION TO SHARE:
- refactor_sagiha_v2_guidelines.md (§7 Phase 3)
- docs/implementation/development_plan_v2.md (Sprint v2-S3)
- docs/02-architecture/context-and-cache-engineering.md (Layer 6 seed-only retrieval & compaction)
- docs/02-architecture/prompt-architecture.md (Prompt structure & headroom)
- docs/02-architecture/security-and-threat-model.md (Threat T7 & TaintGate v1)
- docs/03-contracts-and-models/frozen-run-state.md (FrozenRunState grants-absent spec)
- docs/08-decisions/0021-seed-only-layer-6-retrieval.md (ADR-0021)

CORE INVARIANTS:
- Layer 6 Retrieval seeds are accepted ONLY at ContextAssembler construction time (seed-only invariant).
- Monotonic run-taint tracking MUST propagate through compaction.
- FrozenRunState MUST NEVER serialize active capability grants.

OBJECTIVES:
1. Epic S3.1: Create src/sagiha/agency/context/assembler.py (ContextAssembler) accepting retrieval seeds strictly at construction. Emit prefix_digest.
2. Epic S3.2: Create src/sagiha/agency/context/compactor.py (ExchangeCompactor) preserving whole assistant-tool exchanges.
3. Epic S3.3: Implement TaintGate v1 in kernel/policy/engine.py, kernel/dispatch.py, and adapters/tools/registry.py. Monotonically flag tainted runs on untrusted tool outputs and deny mutations with requires_human=True.
4. Epic S3.4: Implement FrozenRunState in domain/control.py with grant-absent security semantics and failover/checkpointing behavior.

VERIFICATION GATES:
- 200-step long-horizon compaction test passes under 128k context window limit
- Injection canary test confirms 0 unapproved tainted diffs reach disk
- Freeze -> kill -9 -> thaw roundtrip yields identical GateReport
```

---

### Wave 4 — Search Strategy vs. Perimeter Isolation (Parallel Wave)
> **Prerequisites:** Wave 3 (v2-S3) complete.

#### Developer Prompt — Track A (Sprint v2-S4):
> **Target Tier:** Tier 3–4 (Specialist Developer / PhD — Concurrency & Benchmark Search)  
> **Estimated Senior Dev Effort:** 40–56 hrs (5–7 days)

```text
You are acting as Dev A (Specialist / PhD Developer) assigned to implement Sprint v2-S4 in docs/implementation/development_plan_v2.md.

REQUIRED READING & DOCUMENTATION TO SHARE:
- refactor_sagiha_v2_guidelines.md (§8 Phase 4)
- docs/implementation/development_plan_v2.md (Sprint v2-S4)
- docs/04-workflows-and-loops/rhi-outer-loop.md (RHI outer loop execution & economics)
- docs/04-workflows-and-loops/trace-distillation.md (Trace dataset exporter spec)
- docs/08-decisions/0005-best-of-n-not-mcts.md (ADR-0005)
- docs/08-decisions/0022-rhi-economic-refounding.md (ADR-0022)

CORE INVARIANTS:
- Hard gates admit candidates; scoring proxies may rank but NEVER admit or override a gate failure.
- Worktree-parallel candidates must execute in isolated worktrees with clean teardown.

OBJECTIVES:
1. Epic S4.1: Harden E0-lite benchmark harvester validation in src/sagiha/e0/ and adapters/benchmark/. Verify paired statistical calculations in e0/statistics.py.
2. Epic S4.2: Implement CandidateSearch v2 Best-of-N search in adapters/search/best_of_n.py over GitWorktreeManager with early gate-failure pruning.
3. Epic S4.3: Implement scoring bootstrap (S-0/S-1) in adapters/search/scoring.py with deterministic composite proxies and judge-separation checks.
4. Epic S4.4: Build trace dataset exporter in src/sagiha/outer_loop/export/ for SFT/DPO JSONL output with secret-redaction and taint filtering.

VERIFICATION GATES:
- sagiha bench --aa demonstrates BoN outperforms single-shot beyond A/A noise floor
- Zero grader modifications across benchmark runs
- Exported JSONL trace dataset passes schema validation and excludes tainted runs
```

#### Developer Prompt — Track B (Sprint v2-S5):
> **Target Tier:** Tier 3 (Specialist Developer — OS / Container Security & Infra)  
> **Estimated Senior Dev Effort:** 28–40 hrs (3.5–5 days)

```text
You are acting as Dev B (Security / Infrastructure Specialist) assigned to implement Sprint v2-S5 in docs/implementation/development_plan_v2.md.

REQUIRED READING & DOCUMENTATION TO SHARE:
- refactor_sagiha_v2_guidelines.md (§9 Phase 5)
- docs/implementation/development_plan_v2.md (Sprint v2-S5)
- docs/02-architecture/security-and-threat-model.md (Perimeter isolation model)
- docs/08-decisions/0006-sandbox-is-the-perimeter.md (ADR-0006)
- docs/08-decisions/0016-container-runtime-podman.md (ADR-0016)

CORE INVARIANTS:
- Container sandbox is the primary security boundary for autonomous execution profiles.
- Subprocess + autonomous mode must be strictly refused in configuration.

OBJECTIVES:
1. Epic S5.1: Implement rootless Podman ContainerSandbox in adapters/sandbox/container.py with worktree bind mounts and resource constraints.
2. Epic S5.2: Implement egress proxy allowlisting and namespace network firewalls to restrict outbound traffic and prevent host credential leaks.
3. Epic S5.3: Wire container gating in domain/config.py to unlock sagiha run --autonomy autonomous safely.

VERIFICATION GATES:
- Workspace conformance suite parametrized green over both LocalWorkspace and ContainerSandbox
- Injection canary suite confirms zero host credential reads and zero non-allowlisted egress
```

---

### Wave 5 — Code Intelligence & Cold-Start (Sequential / Paired)
> **Target Tier:** Tier 2 (Senior Developer — AST / Compilers / Search Indexing)  
> **Estimated Senior Dev Effort:** 24–32 hrs (3–4 days)  
> **Prerequisites:** Wave 3 (v2-S3) and Wave 4 (v2-S4) complete.

#### Developer Prompt (Sprint v2-S6):
```text
You are acting as a Senior Developer assigned to implement Sprint v2-S6 in docs/implementation/development_plan_v2.md.

REQUIRED READING & DOCUMENTATION TO SHARE:
- refactor_sagiha_v2_guidelines.md (§10 Phase 6)
- docs/implementation/development_plan_v2.md (Sprint v2-S6)
- docs/02-architecture/context-and-cache-engineering.md (Code intelligence tools)
- docs/08-decisions/0011-split-code-and-episodic-graphs.md (ADR-0011)
- docs/08-decisions/0014-defer-dense-retrieval.md (ADR-0014)

CORE INVARIANTS:
- Code graph edges are rebuildable deterministically from HEAD.
- Indexer MUST respect 'retrieval: excluded' YAML frontmatter key.

OBJECTIVES:
1. Epic S6.1: Implement SQLite FTS5 indexer with AST chunking in adapters/indexer/fts5.py.
2. Epic S6.2: Build Tree-sitter code graph analyzer in adapters/code_graph/treesitter.py for import/call/co-change edges.
3. Epic S6.3: Register code intelligence tools (find_symbols, get_skeleton, impacted_by) and wire construction-time retrieval seeds into ContextAssembler.
4. Epic S6.4: Implement sagiha init command in src/sagiha/cli.py and outer_loop/init/ to bootstrap AGENTS.md.
5. Epic S6.5: Respect retrieval: excluded doc frontmatter in FTS5 indexer.

VERIFICATION GATES:
- Recall@10 >= target on labelled test query suite
- Ablation tests demonstrate retrieval-on > retrieval-off and init-on > init-off beyond A/A noise floor
```

---

### Wave 6 — Macro Architecture & Ecosystem (Final Integration Wave)
> **Target Tier:** Tier 4 (PhD / CTO / Principal Architect)  
> **Estimated Senior Dev Effort:** 48–64 hrs (6–8 days)  
> **Prerequisites:** Wave 4 (v2-S4, v2-S5) and Wave 5 (v2-S6) complete.

#### Developer Prompt (Sprint v2-S7):
```text
You are acting as Principal Systems Architect / CTO assigned to implement Sprint v2-S7 in docs/implementation/development_plan_v2.md.

REQUIRED READING & DOCUMENTATION TO SHARE:
- refactor_sagiha_v2_guidelines.md (§11 Phase 7)
- docs/implementation/development_plan_v2.md (Sprint v2-S7)
- docs/04-workflows-and-loops/workflow-orchestration-and-dags.md (Macro DAG engine)
- docs/03-contracts-and-models/protocols-mcp-a2a.md (MCP integration spec)
- docs/08-decisions/0018-native-workflow-dag.md (ADR-0018)

CORE INVARIANTS:
- Macro DAG planning MUST beat feeding raw prompts to the inner loop in E0 ablation tests (ADR-0018).
- MCP tool outputs register trusted_output=False and dispatch through the policy choke point.

OBJECTIVES:
1. Epic S7.1: Implement Workflow Runner & Story-DAG engine in src/sagiha/agency/workflow/ (PipelineRunner, PRDGeneratorStep, StoryDecomposerStep, IntegrationStep, ResolveConflictTask).
2. Epic S7.2: Build MCP stdio client driver in adapters/mcp/driver.py. Register MCP tools as trusted_output=False through PolicyEngine dispatch.
3. Epic S7.3: Implement streaming support in adapters/model/openai.py, exchange-boundary interrupt-and-steer, and interactive steering TUI in src/sagiha/cli.py.

VERIFICATION GATES:
- E0 ablation confirms planning outperforms raw inner-loop prompt feeding
- External MCP tool executes under grant policy and propagates taint end-to-end
- Steering interrupt response < 2s with preserved prompt tail-cache
```
