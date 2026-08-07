---
status: historical
updated: 2026-08-07
---

# Sprint 3.5 — Inner Loop Context Lift & Harness Improvements

## 1. Overview & Rationale

Prior to this intervention, the AETHER walking skeleton achieved a 0% resolve rate on both trivial floor tasks and multi-file medium tasks when paired with local LLMs (`qwen2.5:1.5b`, `qwen3.6:27b`). Investigation revealed that this failure was **not an architectural defect** in the kernel, choke point, governor, or evaluator, but rather a context degradation issue inside the workflow nodes:

1. **Stale Repair Context**: The repair node (`RepairStep`) previously prompted the model with the task instructions, previous patch, and test traceback, but **omitted the source code files**. Consequently, repair turns forced the model to guess source code from memory, leading to hallucinated edits.
2. **Hardcoded Instruction Mismatch**: Execution scripts supplied a hardcoded instruction mentioning a non-existent `mod.py` function `f` across all task manifests.
3. **Hardcoded File Lists in Topologies**: Existing YAML topologies explicitly hardcoded `[mod.py, store.py]`, causing retrieval failures on multi-file tasks (e.g. `storage.py`, `playlist.py`, `smart_rules.py`).

By resolving these issues in a **decoupled, config-driven manner**, we restore compliance with [ADR-0010 (Context Prefix Layers)](../decisions/0010-context-prefix-layers.md) and [ADR-0014 (Workflow Topology as Data)](../decisions/0014-workflow-topology-is-data.md) without altering TCB core modules.

---

## 2. Core Architectural Assumptions & Compliance

| Assumption / Rule | How Sprint 3.5 Complies | Architectural Invariant |
| :--- | :--- | :--- |
| **L1–L5 Context Stack Integrity** | `RepairStep` re-reads worktree files via `self._dispatch.read()` and embeds them under `## Current source files`, preserving L1 (system), L3 (files), L4 (task), and L5 (failure) in every repair turn. | I10 (Prompt cache is architecture) |
| **Topology is Data** | File lists are no longer hardcoded in python node definitions or static YAML topologies; `linear_repair_autofiles_v1.yaml` resolves entry files from runtime parameters. | ADR-0014 (Topologies are data) |
| **TCB Immutability** | No changes were made to `kernel/`, `measurement/evaluator.py`, `workflow/executor.py`, or `workflow/validator.py`. | I8 (Immutable TCB) |
| **Choke Point Verification** | File re-reading in `RepairStep` executes through `DispatchFacade` (`ReadArgs`), ensuring authorization and resource tracking. | I5 (Single choke point) |
| **Bounded Repair Unroll** | Repair iterations remain bounded ($k \le 3$) and `GateStatus.NONE` payload rejection is strictly enforced. | ADR-0013 (Phased workflow DAG) |

---

## 3. Implemented Tasks & Component Changes

### TASK-039: Repair Step Source Context Re-reading
- **Location**: [`src/aether/workflow/nodes/repair.py`](../../src/aether/workflow/nodes/repair.py)
- **Mechanism**: Added `entry_files: tuple[str, ...]` to `RepairStep.__init__` and implemented private async method `_read_current_files(worktree)`.
- **Prompt Effect**: Every repair iteration formats the current state of source files into the user prompt, ensuring the model sees the result of its previous (failed) patch before attempting a fix.

### TASK-040: Engine Factory Extension & Dynamic Topologies
- **Location**: [`src/aether/engine.py`](../../src/aether/engine.py), [`workflows/linear_repair_autofiles_v1.yaml`](../../workflows/linear_repair_autofiles_v1.yaml)
- **Mechanism**: `build_step_registry` forwards `params.get("entry_files")` to `RepairStep`. New topology `linear_repair_autofiles_v1` introduced using `whole_file_codeblock` edit format.

### TASK-041: Dynamic Task Instruction & File Auto-Discovery
- **Location**: [`scripts/run_local_check.py`](../../scripts/run_local_check.py)
- **Mechanism**: Added `auto_discover_entry_files()` to find non-test `.py` source files, and `build_task_instructions()` to read and include `run_tests.py` content directly in task instructions. Small models receive explicit `assert` criteria instead of generic descriptions.

---

## 4. Immediate Benefits & Performance Strategy

1. **Zero-Token Cache Overhead**: Stable L1–L4 prefixes remain identical across repair iterations, maximizing KV cache hit ratios for local engines (vLLM/Ollama) and cloud APIs.
2. **Multi-File Reasoning Unblocked**: Local models (`qwen3.6:27b`) can now navigate tasks spanning multiple files (`storage.py`, `smart_rules.py`, `playlist.py`).
3. **No Legacy Debt**: All new components conform strictly to Pydantic models, async protocols, and `pyright --strict` validation.
