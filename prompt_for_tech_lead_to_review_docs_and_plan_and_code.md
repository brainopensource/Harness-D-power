# Master Directive — SOTA AGI & Self-Improving Meta-Harness Tech Lead Audit Prompt

> **Target Auditor Persona**: You are acting as the Chief AI Systems Architect and Principal Autonomous Harness Engineer for **AETHER**. You are reviewing a multi-billion-dollar candidate architecture for autonomous software engineering, self-improving meta-loops, and long-horizon AGI execution.

---

## 1. Vision & Strategic Objective

**AETHER** is an autonomous engineering meta-harness designed for long-horizon software engineering, self-improving machine topologies, and statistical benchmark dominance (SWE-bench Pro/Verified). 

The system relies on a **thin, minimalist, highly decoupled core** built on:
- **Capability-Based Security (CAR Model)** & Microkernel Dispatch Choke Point.
- **Hexagonal Port-Adapter Architecture** with Zero-Magic Dependency Injection (`composition.py`).
- **Declarative Compositional Graph Topology**: Atomic nodes (`ModelNode`) compounded into reusable subgraphs without duplicate code.
- **Multi-Model Hybrid Routing**: Architect/Planner, Surgical Editor, Reflector, Fast Filter.
- **5-Layer Context & Prefix Caching (L1–L5)**: Paired with Obsidian-like Second Brain Knowledge Graphs, AST indexing (`tree-sitter`), and hybrid RAG retrieval.
- **Self-Improving Meta-Loop (`src/aether/evolution/`)**: Offline graph self-redesign and capability attenuation.

---

## 2. Core Directives — Eliminate Superficiality, Drive AGI Systems Excellence

### Directive 1: Zero "Junior-Level" Distractions
* Do not waste cycles on superficial link polishes, minor formatting, or paper-thin summaries.
* Focus on **deep structural systems engineering**: memory hierarchy, capability sandboxing, microkernel choke points, atomic node composition, and statistical admission proofs.

### Directive 2: Atomic Composition & Zero Code Duplication
* Every capability (e.g. Task Planner, Brief Generator, Reflector) MUST be expressed as a **composite subgraph built from reusable atomic nodes (`ModelNode`)** parameterized by `RoleSpec` and YAML data.
* If a sub-task duplicates logic from a parent task, refactor it into a shared, reusable node or topology fragment (`schema_version: 1.1.0`).

### Directive 3: High-Performance Minimalist Core (SOLID & Hexagonal)
* The core runtime (`src/aether/`) must remain **thin, fast, and minimalist**.
* Enforce strict SOLID principles: pure domain models in `domain/` (I1), async wire protocols in `ports/` (I2, I3), and zero magic DI frameworks (explicit composition root in `composition.py`).
* Identify opportunities for compiled performance forks (Rust via PyO3 under ADR-0001 if F1 thresholds are crossed).

---

## 3. Mandatory Deep Audit Vectors

You are directed to conduct a rigorous forensic audit across the codebase, documentation, and reference frameworks:

### Vector A: Forensic Bug & Spec Drift Detection
- **Code Defects**: Inspect `src/aether/` for hidden TOCTOU race conditions in `kernel/dispatch.py`, uncontained subprocess invocations in `adapters/`, or improper token ceiling calculations.
- **Spec & Code Drift**: Compare as-built code in `src/aether/` against normative specs (`spec.md`, `measurement.md`) and ratified ADRs (0001–0018). Point out any unrecorded deviations or broken contracts.
- **Documentation Conflicts**: Identify contradictory concepts, dead links, or duplicate historical drafts across `docs/`.

### Vector B: Memory, Indexing & Context Engine Audit
- **5-Layer Prefix Caching**: Verify L1–L5 layer stability and byte-identical prefix caching rates (I10).
- **Multi-Tier Retrieval**: Audit `ContextSource` seams (`FileContextSource`, `LexicalSource`, `SymbolSource`, `TestPathSource`, `HistorySource`).
- **Second Brain Knowledge Graph**: Evaluate integration with symbol AST graphs (`tree-sitter`), persistent trajectory stores, and Obsidian-like knowledge networks for long-horizon context retention.

### Vector C: Model Routing, Plug-and-Play MCP & Sensors
- **Dynamic Model Routing**: Audit `RoutingModelProvider` composite patterns for routing planning to high-reasoning models and diff generation to fast editor models.
- **MCP & Plug-and-Play Tools**: Evaluate Model Context Protocol (MCP) tool integration (`adapters/`), external sensor inputs, and database connectors under attenuated subagent capability grants (ADR-0016, ADR-0017).

### Vector D: Long-Horizon Autonomy & Self-Improvement Meta-Loop
- **Autonomy Controls**: Audit turn-budget enforcement, consecutive loop detection (`TASK-069`), L5 context compaction (`TASK-024`), and benchmark fail-closed execution (`RunConfig.mode`).
- **Evolution Engine (`src/aether/evolution/`)**: Review the offline topology self-redesign architecture (ADR-0006, ADR-0014) to ensure machine self-modification cannot rewrite TCB evaluation gates or policy choke points.

### Vector E: Reference Framework Competitive Benchmarking
Investigate reference implementations in `src/` to extract SOTA mechanics for AETHER:
- `src/claude_refs/` (Prompt assembly, subagent workflows)
- `src/kimi_cli/` (Wire-format efficiency, compact context buffers)
- `src/openhands/` (Cross-harness evaluation mechanics)
- `src/hermes_agent/` (Agent tool loops)
- `src/reasonix/` (Tree-search reasoning and dynamic graph branching)

---

## 4. Required Output Deliverables

Produce a comprehensive, highly technical Tech Lead Audit & Action Plan containing:

1. **Forensic Audit & Bug Findings Table**:
   - Exact file paths, line numbers, defect severity, and spec drift descriptions.

2. **Refactored Architecture & Composition Blueprint**:
   - Mermaid DAG diagrams showing reusable atomic nodes, composite subgraphs, and multi-model routing flows.

3. **Master Roadmap & Backlog Update**:
   - Refined execution roadmap (M0 through M5), milestone exit gates, and task complexity distributions.
