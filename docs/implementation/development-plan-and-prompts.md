# **SAGIHA2 Implementation Plan & Modular Prompt Guidelines**

> [!NOTE]
> **Working Proposal Disclaimer**: This document represents a structured implementation guideline for SAGIHA2. Prompts are parameterized and modularized to remain valid even as specific adapter implementations or stack choices evolve.

---

## 🗓️ **Phased Execution Roadmap**

| Phase | Focus Area | Primary Deliverables | Key Success Criteria |
| :--- | :--- | :--- | :--- |
| **Phase 1** | Scaffolding & Ports | Package tree, Pydantic v2 schemas, `typing.Protocol` ports, Composition Root | 100% port type-checking & conformance test suite passing |
| **Phase 2** | Day-Zero Microkernel | SQLite-WAL trajectory store, Stdio MCP driver, ReAct event-bus microkernel | Single-turn task execution with 0% crash rate |
| **Phase 3** | Isolation & LSP | Git Worktree manager, workspace materialization, stdio LSP adapter, pristine test gates | 100% worktree isolation & diagnostic error feedback loop |
| **Phase 4** | Memory & AST Chunking | Tree-sitter AST skeletonizer, LanceDB vector + SQLite BM25 hybrid search, telemetry logging | Sub-second retrieval & AST prompt compaction |
| **Phase 5** | System 2 & Scaling | Best-of-N worktree search, A2A multi-agent fleet, Docker sandbox, optional AOI | Verified multi-file refactoring without regressions |

---

## 🛠️ **Reusable Modular Implementation Prompts**

### **Sprint 1: Core Scaffolding, Typed Ports & Conformance Tests**
```markdown
Scaffold the Python 3.12+ project structure under `src/sagiha2/`. Define all Pydantic v2 domain schemas in `domain.py` and strict `typing.Protocol` interfaces in `ports.py` (including `LLMProvider`, `Memory`, `LSPAdapter`, `Workspace`, `PolicyEngine`, `TrajectoryStore`). Create a single composition root (`build_kernel(config) -> Kernel`) and write a port conformance test suite under `tests/conformance/` to ensure zero contract leakage.
```

### **Sprint 2: Day-Zero Baseline Kernel & MCP Driver**
```markdown
Implement the Day-Zero baseline kernel in `src/sagiha2/kernel/`. Create an in-process SQLite-WAL Trajectory Store, an in-memory ShortTermMemory adapter, a Stdio MCP tool client driver for filesystem/bash tools, and a deterministic Async ReAct state machine. Write unit tests in `tests/unit/` ensuring end-to-end task execution without external framework lock-in.
```

### **Sprint 3: Git Worktree Isolation & LSP Diagnostic Gate**
```markdown
Implement `GitWorktreeManager` in `src/sagiha2/workspace/` with automated materialization of ignored essentials (`.env`, `.venv`). Add a stdio `LSPAdapter` using `pygls` to collect real-time diagnostic items before running tests. Ensure test evaluations run against a pristine, read-only test checkout to prevent test self-editing vulnerabilities.
```

### **Sprint 4: Hybrid Memory & Tree-sitter AST Chunking**
```markdown
Implement Tree-sitter AST skeletonization for prompt compaction in `src/sagiha2/indexing/`. Integrate LanceDB vector search with SQLite BM25 sparse search for hybrid retrieval. Enable Day 0 Parameter Telemetry logging to capture task features, costs, and results as structured JSONL/SQLite events for future AOI training.
```

### **Sprint 5: System 2 Best-of-N Search & Fleet Delegation**
```markdown
Implement System 2 Best-of-N branch exploration across parallel Git worktrees in `src/sagiha2/orchestration/`, scoring branches via LSP diagnostic deltas and pytest PRMs. Add an A2A protocol driver for peer sub-agent delegation and integrate Docker container sandboxes for command execution.
```
