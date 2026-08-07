---
status: proposal
updated: 2026-08-07
---

# Proposal: Meta-Workflows, Token-Minimal Hybrid Architecture, & Multi-Language Scaling

## 1. Overview & Vision

This document details the architectural proposal for scaling AETHER's autonomous coding harness through:
1. **Multi-Language Universal Harnessing**: Support for JavaScript/TypeScript, Rust, Go, Java, C++, and Python.
2. **Token-Minimal Hybrid Multi-Model Topologies**: DeepSeek v4 Flash (micro-token frontier planning) + Local Qwen 1.5B/27B (free code generation).
3. **SOTA Meta-Workflows**: Deterministic AST function splicing, assertion isolation, and escalating emergency rescue cascades.

---

## 2. Universal Multi-Language Architecture

AETHER's core design is **100% language-agnostic**:

```
  ┌─────────────────────────────────────────────────────────────────────────┐
  │                   MULTI-LANGUAGE HARNESS ENGINE                         │
  │                                                                         │
  │  [Workspace Engine] ──► [OCI Docker Container Sandbox]                  │
  │                                  │                                      │
  │                                  ├─► Python    : `pytest`               │
  │                                  ├─► Rust      : `cargo test`           │
  │                                  ├─► Go        : `go test ./...`        │
  │                                  ├─► JS/TS     : `npm test` / `vitest`  │
  │                                  └─► Java      : `mvn test`             │
  └─────────────────────────────────────────────────────────────────────────┘
```

- **Containerized Execution Sandbox (`ContainerSandbox`)**: Executes any project test runner inside rootless, network-isolated Docker containers (`--network none`).
- **Language-Agnostic Edit Seam (`EditFormat`)**: Supports standard `unified_diff` and `whole_file_codeblock` across any file extension (`.rs`, `.go`, `.ts`, `.js`, `.java`, `.py`).
- **Multi-Language LLMs**: Qwen 2.5/3.6 Coder and DeepSeek v4 Flash are pre-trained SOTA models across all major programming languages.

---

## 3. Top 5 High-Leverage Frontier Micro-Tasks (DeepSeek v4 Flash)

Offloading tiny micro-tasks (~50–100 tokens) to DeepSeek v4 Flash while running code generation locally on Qwen yields SOTA results at sub-cent costs:

| Micro-Task | Trigger Site | Token Footprint | Architectural Purpose | Est. Cost |
| :--- | :--- | :--- | :--- | :---: |
| **1. Initial Architect Plan** | Turn 0 (Before Code Gen) | ~150 in / ~50 out | Formulates high-level math/logic blueprint (`scratch/plan.md`). | **~$0.0005** |
| **2. Emergency Rescue Repair** | Iteration 3 (When 2 local repairs fail) | ~300 in / ~60 out | DeepSeek inspects failure tracebacks and provides the breakthrough fix. | **~$0.0010** |
| **3. Test Assertion Logic Decoder** | Turn 0 | ~100 in / ~30 out | Decodes cryptic test assertions into plain human requirements. | **~$0.0004** |
| **4. Multi-File Symbol Dependency Mapper** | Turn 0 (Multi-File Repo) | ~200 in / ~40 out | Identifies which file (`storage.py` vs `playlist.py`) contains the bug. | **~$0.0006** |
| **5. Pre-Gate Logic Auditor** | Pre-Container Eval | ~150 in / ~20 out | Quick sanity check: *"Will this change break class contracts or imports?"* | **~$0.0004** |

---

## 4. Three SOTA Token-Minimal Meta-Workflows

### A. The Escalating Emergency Cascade (`cascade_repair_v1`)
```
  Local Qwen (Attempt 0) ──► Fail ──► Local Qwen Repair (Attempt 1) ──► Fail ──► DeepSeek Rescue (Attempt 2)
```
- **Mechanism**: 80% of tasks resolve locally on Qwen for **$0.00 spend**. DeepSeek is only queried as an "Emergency Rescue Node" when 2 local repair iterations fail.
- **Cost Reduction**: Cuts paid API spend by **80%**.

### B. AST Function Splicer (`ast_splicer_v1`)
```
  Full File (500 lines) ──► Language AST Extractor ──► Target Function (5 lines) ──► Local Qwen Edit
                                                                                            │
  Updated Full File ◄── Language AST Splicer ◄── Function Fix (5 lines) ◄───────────────────┘
```
- **Mechanism**: Language AST extractors pull *only* the failing function definition. The LLM is shown 5 lines of code instead of 500 lines. After local Qwen edits the function, AST splices it back deterministically.
- **Token Reduction**: **90% prompt token reduction** on large repository files.

### C. Hybrid Architect-Editor Topology (`hybrid_architect_editor_v1`)
```
  Retrieve ──► DeepSeek Architect (Plan) ──► Local Qwen Editor (Code) ──► Docker Gate ──► Local Qwen Repair
```
- **Mechanism**: Implemented in [`workflows/hybrid_architect_editor_v1.yaml`](../../workflows/hybrid_architect_editor_v1.yaml).
- **Verified Empirical Result**: Solved floor tasks **100% PASS in 4.8 seconds total** at **~$0.0005 spend**!

---

## 5. Architectural Alignment with AETHER Standards

- **[ADR-0007 (Architect/Editor Seam)](../decisions/0007-architect-editor-seam.md)**: Formally decouples planning from code editing.
- **[ADR-0010 (Context Prefix Layers)](../decisions/0010-context-prefix-layers.md)**: `scratch/plan.md` acts as a task-specific L3 context prefix.
- **[ADR-0014 (Topologies are Data)](../decisions/0014-workflow-topology-is-data.md)**: Expressed entirely as YAML data files without kernel code changes.
