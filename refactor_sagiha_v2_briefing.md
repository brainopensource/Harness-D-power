# SAGIHA v2 Refactor & Evolution Briefing

This document outlines the execution roadmap for refactoring SAGIHA to the v2 architecture. The plan enforces strict instrument honesty, contract consolidation, context engine safety, sandbox perimeter security, and phased capability evolution.

## 1. Documentation & Governance Changes (Sprint v2-S0)
* **SSOT Consolidation & Word Budget:** Shrink normative docs in [docs/](file:///home/rock_dev/Code/Harness/docs) to ≤15,000 words. Move legacy sprint specs and reference material to `docs/rationale/` with `retrieval: excluded` frontmatter.
* **Normative Amendments:** Update [02-architecture/context-and-cache-engineering.md](file:///home/rock_dev/Code/Harness/docs/02-architecture/context-and-cache-engineering.md) with the seed-only Layer 6 retrieval ruling and exchange-granular compaction. Add TaintGate v1 as T7 in [02-architecture/security-and-threat-model.md](file:///home/rock_dev/Code/Harness/docs/02-architecture/security-and-threat-model.md).
* **ADRs & Status Re-baseline:** Record ADR-0019 (port consolidation 21→15), ADR-0020 (PURE allowlist), ADR-0021 (seed-only retrieval), ADR-0022 (RHI economic re-founding), and ADR-0023 (port rent rule). Update [STATUS.md](file:///home/rock_dev/Code/Harness/docs/STATUS.md) to reflect honest capabilities.

## 2. Code Honesty & Infrastructure Refactoring (Sprints v2-S1 & v2-S2)
* **Instrument Honesty (H1–H4 Fixes - Mandatory First Step):**
  * **H1 (Real Gates):** Replace hardcoded boolean gates in [gate_evaluator.py](file:///home/rock_dev/Code/Harness/src/sagiha/outer_loop/evaluator/gate_evaluator.py) with actual `git diff` checks (`tests_unmodified`, `diff_within_bounds`, `no_new_suppressions`).
  * **H2 (Live Cost Telemetry):** Update [ports/model.py](file:///home/rock_dev/Code/Harness/src/sagiha/ports/model.py) to return `Completion` payloads carrying `TokenUsage`. Wire `record_spend()` in [governor.py](file:///home/rock_dev/Code/Harness/src/sagiha/kernel/governor.py) and [run_loop.py](file:///home/rock_dev/Code/Harness/src/sagiha/agency/run_loop.py).
  * **H3 (Loud Stubs):** Make stub methods in container sandbox and MCP driver raise `NotImplementedError`.
  * **H4 (Syntax Gating):** Enforce stdlib `ast.parse` checks pre-write in [local.py](file:///home/rock_dev/Code/Harness/src/sagiha/adapters/workspace/local.py).
* **Port Consolidation (21 → 15):** Delete [reviewer.py](file:///home/rock_dev/Code/Harness/src/sagiha/ports/reviewer.py), [embedding.py](file:///home/rock_dev/Code/Harness/src/sagiha/ports/embedding.py), and `ShortTermMemory` from [memory.py](file:///home/rock_dev/Code/Harness/src/sagiha/ports/memory.py). Rewrite [advisory.py](file:///home/rock_dev/Code/Harness/src/sagiha/ports/advisory.py) into a unified discriminator interface.
* **Kernel & Effects Safety:** Implement PURE command classification in `kernel/policy/effects.py`. Remove path-stripping hacks in [builtins.py](file:///home/rock_dev/Code/Harness/src/sagiha/adapters/tools/builtins.py) and reclassify `apply_edit` as `DESTRUCTIVE`. Single-source tool schemas dynamically in [composition.py](file:///home/rock_dev/Code/Harness/src/sagiha/composition.py).

## 3. Core Capability Implementation (Sprints v2-S3 to v2-S7)
* **Context & Safety Engine (v2-S3):** Build `ContextAssembler` (seed-only Layer 6) and `ExchangeCompactor` (whole-exchange token budgeting) in `src/sagiha/agency/context/`. Enforce TaintGate v1 in [engine.py](file:///home/rock_dev/Code/Harness/src/sagiha/kernel/policy/engine.py) to deny untrusted mutations without human approval. Add [FrozenRunState](file:///home/rock_dev/Code/Harness/src/sagiha/domain/control.py).
* **Best-of-N & Dataset Exporter (v2-S4):** Implement worktree-parallel `CandidateSearch` with early hard-gate pruning. Build `sagiha export` to produce SFT/DPO JSONL datasets from admitted trajectories.
* **Perimeter & Code Intelligence (v2-S5 & v2-S6):** Implement rootless Podman `ContainerSandbox` to unlock `autonomous` mode. Add FTS5 indexing, Tree-sitter code graph, and `sagiha init`.
* **Macro Workflow & Ecosystem (v2-S7):** Implement `StoryDAG` pipeline runner with `IntegrationStep` rebase verification, stdio MCP driver, and streaming steerable turns.

## 4. Conductor Layer Execution Guidelines (Phases C0–C7)
* **Agent Execution Workflow:** Senior developers and coder agents must execute sequentially from Sprint v2-S0 through v2-S7. Every commit must verify static quality (`pytest`, `pyright`, `ruff check`, `lint-imports`) and replay determinism.
* **Conductor System 3 (`sagiha_conductor`):** Once v2-S7 exit gates pass, implement the System 3 Conductor package over the `Orchestrator` port for long-horizon mission scheduling, active memory consolidation, and Tier-4 model promotion.
