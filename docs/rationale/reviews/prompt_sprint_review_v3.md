---
status: rationale
retrieval: excluded
updated: 2026-08-01
---
# SENIOR ARCHITECT REVIEW GATE: SAGIHA v2 SERIES AUDIT V3 (v2-S0 THROUGH v2-S6)

You are acting as a Senior Principal Software Architect and Systems Auditor. Your task is to perform an exhaustive, objective, and unbiased code-vs-documentation audit of the **SAGIHA** autonomous coding harness before closing the current development phase.

Your evaluation must compare the actual implementation under `src/sagiha` against the normative architectural specifications, design decisions, and sprint plans in `docs/`.

---

## 1. SCOPE AND BOUNDARIES

### In Scope (Phases 0–6 / Sprints `v2-S0` to `v2-S6`)
* **Sprint `v2-S0`**: Documentation shrink, SSOT consolidation, ADRs 0019–0023, baseline `docs/STATUS.md`, and word budget enforcement (`scripts/docs_budget.py`).
* **Sprint `v2-S1`**: Instrument Honesty (fixes for H1–H4 findings: base-commit diff gates, spend telemetry, AST syntax checks, loud stub raising).
* **Sprint `v2-S2`**: Port Consolidation (17 active ports), PURE/DESTRUCTIVE effect classification, builtin tool corrections, composition hardening, trajectory completeness (`Message` persistence).
* **Sprint `v2-S3`**: Context Engine (`src/sagiha/agency/context/assembler.py` seed-only L6, `src/sagiha/agency/context/compactor.py`), TaintGate v1 (monotonic taint), `src/sagiha/domain/control.py`, role failover.
* **Sprint `v2-S4`**: E0 Harness hardening (`src/sagiha/e0/`), Best-of-N mechanism over worktrees (`src/sagiha/adapters/search/best_of_n.py`), ranking-only scoring (S-0/S-1), SFT/DPO dataset exporter (`src/sagiha/outer_loop/export/exporter.py`).
* **Sprint `v2-S5`**: Rootless Podman `src/sagiha/adapters/sandbox/container.py`, egress proxy allowlist, namespace firewall, `autonomous` profile unlock.
* **Sprint `v2-S6`**: FTS5 code indexer with AST chunking (`src/sagiha/adapters/indexer/fts5.py`), Tree-sitter code graph (`src/sagiha/adapters/code_graph/treesitter.py`), code-intelligence builtins, seed wiring, `sagiha init` (`src/sagiha/outer_loop/init/generate.py`).

### Strictly OUT OF SCOPE (Do NOT evaluate or penalize for missing implementation)
* **Sprint `v2-S7` / Block 4-macro & B5b/c**: Story-DAG workflow runner (`src/sagiha/agency/workflow/`), MCP client driver (`src/sagiha/adapters/mcp/driver.py`), streaming/steerable TUI.
* **Wave 6 / Conductor (AGI Evolution Path)**: Phase C0 and beyond documented in `docs/rationale/reviews/agi_evolution_path.md`.
* **Explicitly Deferred Items**: Dense vector retrieval (ADR-0014), AOI acting mode, RHI Tier C (ADR-0022), A2A remote pilots, performance sidecars, warm LSP.

---

## 2. REFERENCE DOCUMENTATION CORPUS (@docs)

Inspect and cross-reference the following authoritative documents in `docs/`:

1. **Sprint & Baseline Plan**:
   - `docs/implementation/development_plan_v2.md` (Normative re-baseline plan for Sprints v2-S0..v2-S7)
   - `docs/implementation/refactor_sagiha_v2_guidelines.md` (Refactoring guidelines & verification commands)
   - `docs/implementation/sprint_v2_s4_options.md` (Block 2/3 E0 & Best-of-N trade-offs)
   - `docs/STATUS.md` (Current single source of implementation truth)
   - `AGENTS.md` (Core architectural invariants & TCB definition)

2. **Architecture & Design Specs**:
   - `docs/rationale/reviews/next_gen_architecture_specs.md` (v2 Next-Gen Specs: seed-only L6, compaction, TaintGate, FrozenRunState)
   - `docs/rationale/reviews/critical_gaps_analysis.md` (Root cause analysis of pre-v2 harness gaps)
   - `docs/rationale/reviews/codebase_delta_refactor.md` (Delta audit detailing H1–H4 findings)
   - `docs/rationale/reviews/agi_evolution_path.md` (Conductor / AGI roadmap — future reference only)

3. **Core Contracts & Decisions**:
   - `docs/02-architecture/car-model.md` & `docs/02-architecture/security-and-threat-model.md`
   - `docs/03-contracts-and-models/frozen-run-state.md` & `docs/03-contracts-and-models/hexagonal-ports.md`
   - `docs/08-decisions/` (ADRs 0001–0025, specifically ADRs 0019 through 0025)

---

## 3. CODEBASE TARGET STRUCTURE TO AUDIT (@src)

Thoroughly inspect all modules under `src/sagiha/`:

```text
src/sagiha/
├── domain/            # Pure Pydantic domain models (zero I/O dependencies)
│   ├── config.py, control.py, events.py, trajectory.py, work.py, content.py, upcasters.py, 
│   │   benchmark.py, graph.py, identity.py, memory.py, toolchain.py
├── ports/             # Protocol interfaces (17 active ports, 100% remoteable/async)
│   ├── advisory.py, code_graph.py, evaluator.py, governor.py, indexer.py, lsp.py, memory.py,
│   │   meta_improver.py, model.py, orchestrator.py, policy.py, search.py, tool_registry.py,
│   │   toolchain.py, trajectory.py, workspace.py
├── kernel/            # Trusted Computing Base (TCB) & dispatch choke point
│   ├── dispatch.py, bus.py, governor.py
│   └── policy/ (engine.py, effects.py, grants.py, rules.py)
├── agency/            # Inner loop execution & context handling
│   ├── run_loop.py, freeze.py
│   └── context/ (assembler.py, compactor.py)
├── adapters/          # Port implementations
│   ├── workspace/, sandbox/, model/, tools/, search/, indexer/, code_graph/, trajectory/, memory/, mcp/, telemetry/
├── outer_loop/        # Gate evaluation, dataset export, initialization
│   ├── evaluator/ (gate_evaluator.py), export/, init/ (generate.py)
├── e0/                # Evaluation & benchmarking harness
│   ├── harvester.py, runner.py, statistics.py, reporter.py, protocols.py
├── composition.py     # System wiring, dependency injection, TCB boundary validation
└── cli.py             # Entry points (run, replay, harvest, bench, export, init)
```

---

## 4. AUTOMATED VERIFICATION COMMANDS

The auditor must execute and report the results of the following project verification tools:

1. **Test Suite Monotonicity & Execution**:
   `uv run pytest` (Must pass 100% of collected tests; baseline is >= 332 passed).
2. **Static Type Checking**:
   `uv run pyright src/sagiha` (Must return exactly 0 errors).
3. **Import Architecture Layering**:
   `uv run lint-imports` (Must pass 5/5 contract boundaries).
4. **Code Quality & Formatting**:
   `uv run ruff check` & `uv run ruff format --check` (Must report 0 lint or formatting errors).
5. **Documentation Word Budget Ceiling**:
   `python3 scripts/docs_budget.py --max 15000` (Normative docs budget ceiling: <= 15,000 words).
6. **Documentation Link Integrity**:
   `python3 scripts/check_links.py` (Must report 0 broken relative links).
7. **Event Catalog Synchronization**:
   `python3 scripts/gen_event_catalog.py --check` (Must report event catalog in sync).

---

## 5. AUDIT DIMENSIONS & EVALUATION CRITERIA

Evaluate the codebase against these 7 comprehensive software engineering dimensions:

### Dimension 1: Tech Stack, Requirements & Sprint Delivery Matrix (v2-S0 to v2-S6)
For each sprint from `v2-S0` to `v2-S6`:
1. Verify if all planned epics and subtasks in `docs/implementation/development_plan_v2.md` are fully implemented in `src/sagiha/`.
2. Determine if the sprint status is **Complete**, **Partially Complete**, or **Incomplete**.
3. Identify any implementation gaps, missing exit criteria, or unintended scope creep.

### Dimension 2: Core Architectural & Security Invariant Conformance (CAR Model & TCB)
1. **Capability Authorization (CAR Model)**: Is tool execution strictly gated via `PolicyEngine.authorize()` (`src/sagiha/kernel/policy/engine.py`) and dispatched through `src/sagiha/kernel/dispatch.py`? Is point-of-effect grant verification `policy.verify_grant()` in `src/sagiha/kernel/dispatch.py` enforced unconditionally?
2. **TCB Immunity**: Are `src/sagiha/kernel/policy/`, `src/sagiha/outer_loop/evaluator/`, and import-linter rules protected from untrusted modifications?
3. **Port-Adapter Hexagonal Isolation**: Are `src/sagiha/domain/` models pure with zero I/O? Are all `src/sagiha/ports/` methods `async` and Pydantic-serializable without live handles or unpicklable state crossing boundaries? Confirm the active port count matches **17 Protocols across 16 files** (ADR-0019 / ADR-0024).
4. **Effect Classification & Taint Security**: Are tool calls correctly classified as `PURE` or `DESTRUCTIVE` in `src/sagiha/kernel/policy/effects.py`? Does `TaintGate` (v2-S3) untrusted data envelope hold without leaking unapproved mutations (`requires_human=True`)?
5. **Context Integrity & Frozen State**: Does `src/sagiha/agency/context/assembler.py` enforce seed-only Layer-6 retrieval (no post-construction surface)? Is `src/sagiha/domain/control.py` (`FrozenRunState`) completely free of live authorization grants?

### Dimension 3: Instrument Honesty Verification (H1–H5 Audit)
1. **H1 (Real Coding Gates)**: Does `src/sagiha/outer_loop/evaluator/gate_evaluator.py` perform real `git diff` checks against `RunContext.base_commit` for `tests_unmodified`, `diff_within_bounds`, and `no_new_suppressions`?
2. **H2 (Budget & Telemetry)**: Does `src/sagiha/ports/model.py` (`ModelProvider`) return actual token usage? Does `src/sagiha/agency/run_loop.py` call `governor.record_spend()` after every turn and abort on budget breach?
3. **H4 (Syntax Validation)**: Does `src/sagiha/adapters/workspace/local.py` (`LocalWorkspace.apply_edit`) run `ast.parse` before writing python files to prevent broken writes?
4. **H3 (Stub Sanity)**: Are unimplemented adapters (e.g. `src/sagiha/adapters/mcp/driver.py`, `src/sagiha/adapters/telemetry/otel.py`) explicitly raising `NotImplementedError` rather than returning false success payloads?

### Dimension 4: Code Quality, SOLID Principles, Encapsulation & DRY
1. **Liskov Substitution & Protocol Signatures**: Do adapter method signatures match their target `Protocol` definitions exactly in parameter names, default values, and return types (e.g., `src/sagiha/ports/indexer.py` vs `src/sagiha/adapters/indexer/fts5.py`)?
2. **Encapsulation & Private Attribute Access**: Are adapters properly encapsulated without leaking private attributes (e.g., `_db_path`) across service or composition boundaries (e.g. `src/sagiha/adapters/indexer/service.py`)?
3. **DRY & Constant Reusability**: Are shared constants (such as `SKIP_DIRS`) centralized in a single module rather than duplicated across indexer, graph, and generator files?

### Dimension 5: Perimeter & Container Isolation (v2-S5)
1. **Rootless Podman Sandbox**: Does `src/sagiha/adapters/sandbox/container.py` (`ContainerSandbox`) pass the workspace conformance suite parametrized against `src/sagiha/adapters/workspace/local.py`?
2. **Egress Firewall & Secret Isolation**: Does the egress proxy drop direct outbound connections while permitting only explicit allowlisted HTTP CONNECT hosts? Is host environment credentials excluded from container environments?
3. **Autonomy Profile Unlock**: Is `--autonomy autonomous` legally allowed in `src/sagiha/domain/config.py` only when running inside a container sandbox?

### Dimension 6: Empirical vs. Mechanism Validation Status
1. Examine features where mechanism is delivered but empirical defaults are set to disabled due to dataset harvest constraints (e.g., `search.enabled=false` in Best-of-N, `retrieval.enabled=false` in FTS5/Code-Graph).
2. Confirm whether the code correctly enforces these honest-negative safeguards as documented in `docs/STATUS.md`.

### Dimension 7: MVP Scope vs. Future Horizon Alignment
1. Differentiate operational MVP capabilities achieved at `v2-S6` from future enhancements (`v2-S7` macro-workflows, Conductor C0+ AGI layer).
2. Validate that no stub or partial code from `v2-S7` or Conductor pollutes the core `v2-S6` execution loop.

---

## 6. CRITICAL & MAJOR ARCHITECTURAL FOCUS AREAS

The auditor must pay special attention to the following verified technical focus areas during code inspection:

1. **Protocol-Adapter Signature Alignment**:
   Inspect `src/sagiha/ports/indexer.py` and `src/sagiha/adapters/indexer/fts5.py` to verify parameter name alignment on `neighbors(...)` (`query: str` vs `path: str`) and ensure `pyright` evaluates zero structural type mismatch errors.
2. **Encapsulation of Private Object State**:
   Inspect `src/sagiha/adapters/indexer/service.py` to ensure external classes do not access private instance attributes (`._db_path`) of underlying adapters.
3. **Normative Documentation Word Budget Ceiling**:
   Run `python3 scripts/docs_budget.py --max 15000` to verify that `status: normative` documentation does not exceed the 15,000-word limit established in `v2-S0`.
4. **Empirical Ablation Fixture Population**:
   Verify whether benchmark noise-floor fixtures (`docs/rationale/benchmarks/noise-floor.md`) are populated before enabling search or retrieval mechanisms by default.

---

## 7. REQUIRED OUTPUT STRUCTURE

Provide your audit response using the following structured layout:

### Section 1: Executive Summary & Gate Decision
* **Overall Status**: [PASS / CONDITIONAL PASS / REJECT]
* **Summary Scorecard**: Total Sprints Completed (out of S0–S6), Active Ports Count (out of 17 Protocols), Test Monotonicity Verification (Pytest count & pass status), Pyright Type Checker Status, Import Linter Status.
* **Top 3 Strengths & Top 3 Critical Risks/Drifts**.

### Section 2: Sprint Delivery Audit Matrix (v2-S0 through v2-S6)
A detailed Markdown table covering:
`| Sprint | Objective | Planned Epics | Implementation Status (Complete/Partial/Missing) | Delivered Modules / Files | Open Issues / Drifts |`

### Section 3: Detailed Architectural Invariant & Security Review
Deep dive into:
- CAR Policy & TCB Containment (`kernel/dispatch.py`, `kernel/policy/engine.py`)
- Hexagonal Port Remoteability (Async/Pydantic purity, 17 active ports)
- Instrument Honesty (H1–H4 validation proof)
- TaintGate v1 & Context Engine Compliance (`ContextAssembler`, `ExchangeCompactor`, `FrozenRunState`)
- Podman Sandbox Perimeter & Egress Proxy (`ContainerSandbox`, `domain/config.py`)

### Section 4: Codebase Drift & Defect Log
List any bugs, architectural drifts, interface signature mismatches, dead code, formatting errors, or documentation mismatches discovered during the code review, categorized by severity (Critical, Major, Minor).

### Section 5: MVP Status vs. Deferred Roadmap
Detailed summary of what constitutes the production-ready MVP today (`v2-S6`) versus what remains explicitly deferred or out-of-scope (`v2-S7`, Conductor C0+).

### Section 6: Actionable Remediation Plan
Prioritized, step-by-step checklist of fixes required before formally tagging the release.
