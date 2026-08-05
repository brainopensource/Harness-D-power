---
status: rationale
updated: 2026-07-29
retrieval: excluded
---
# **Hexagonal Interface Ports**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

Kernel components interact exclusively via stable `typing.Protocol` interfaces defined in `src/sagiha/ports/` and models in `src/sagiha/domain/`. Code is authoritative; see [Contracts to Code](../implementation/contracts-to-code.md).

## **Five Contract Rules**

1. **No `Dict[str, Any]` across ports**: All payloads use Pydantic models (exemptions: JSON Schema definitions and Tool arguments).
2. **Domain language over storage language**: `remember()` / `recall()`, not `store_vector()`.
3. **Timezone-aware UTC**: All timestamps must be aware UTC datetimes.
4. **Wire-implementable**: Methods are `async` and payloads are serializable (no live handles or callables). See [Remoteable Ports](../02-architecture/remoteable-ports.md).
5. **Static and conformance verification**: Verified by `mypy`/`pyright` strict mode and test suites in `tests/contracts/`, not `@runtime_checkable` or `isinstance`. See [Port Conformance Testing](../06-guides-and-patterns/port-conformance-testing.md).

## **Port Index**

Ports marked *(optional)* may be unbound by specific [execution profiles](../02-architecture/execution-profiles.md).

### **Model & Control**

| Port | Responsibility | Protocol File |
| :--- | :--- | :--- |
| **`ModelProvider`** | Streaming (`AsyncIterator[StreamEvent]`), token accounting, reasoning blocks (`ThinkingContent`/`ReasoningBlock`), schema translation, retries, prompt cache breakpoints. | `ports/model.py` |
| **`PolicyEngine`** | Authorizes dispatches. Grants stay inside `kernel/dispatch.py`. Checked via reachability. | `ports/policy.py` |
| **`ResourceGovernor`** | Global admission control: concurrency, spend, rate limits, sandbox/server pools. | `ports/governor.py` |

> [!IMPORTANT]
> **Model routing is composition, not a port method.** Composition binds **one `ModelProvider` per role** (frontier, workhorse, fast). Callers request roles rather than model names. See [Model Tiering](../05-tech-stack/llm-providers-and-economics.md#2-model-tiering).

### **Memory & Retrieval**

| Port | Responsibility | Protocol File |
| :--- | :--- | :--- |
| `ShortTermMemory` | Append and retrieve trajectory steps for active sessions. | `ports/memory.py` |
| **`Memory`** | Durable knowledge store (`remember` / `recall` / `invalidate`) with trust-provenance. | `ports/memory.py` |
| **`EmbeddingProvider`** | Vector embedding generation. | `ports/embedding.py` |
| `Indexer` | Query interface (`find_symbols`, `get_skeleton`, `neighbors`) returning `RetrievalHit`. | `ports/indexer.py` |
| **`CodeGraph`** | Code structure graph (`upsert_edges`, `impacted_by`, `callers_of`, `co_changed_with`). | `ports/code_graph.py` |
| `LSPAdapter` | Diagnostics, definitions, references returning typed `Symbol` and `DiagnosticItem`. | `ports/lsp.py` |

### **Execution**

| Port | Responsibility | Protocol File |
| :--- | :--- | :--- |
| **`Workspace`** *(optional)* | Workspace file operations (`read`, `write`, `apply_edit`, `run`, `checkpoint`, `restore`). | `ports/workspace.py` |
| `WorktreeManager` *(optional)* | Worktree allocation (`allocate`, `materialize`, `release`). | `ports/workspace.py` |
| `ToolRegistry` | Tool registration with `EffectClass` and dispatch execution. | `ports/tool_registry.py` |
| **`TrajectoryStore`** | Append-only step and score storage. | `ports/trajectory.py` |
| **`Toolchain`** *(optional)* | Workspace-relative verification (`detect`, `test`, `typecheck`, `lint`, `coverage`). | `ports/toolchain.py` |

### **Orchestration & Improvement**

| Port | Responsibility | Protocol File |
| :--- | :--- | :--- |
| `Orchestrator` | `TaskSpec` execution streaming events (`AsyncIterator[Event]`). | `ports/orchestrator.py` |
| **`CandidateSearch`** | Candidate exploration (`propose` / `evaluate` / `select`). | `ports/search.py` |
| `Evaluator` *(optional)* | Evaluation against pristine test suites, outputting `GateReport`. | `ports/evaluator.py` |
| **`Reviewer`** *(optional)* | Soft-score design quality evaluation, outputting `ReviewReport` (never enters `GateReport`). Evaluated by a distinct frontier model. | `ports/reviewer.py` |
| `MetaImprover` | Controlled self-improvement proposals outside the trusted computing base. | `ports/meta_improver.py` |

### **Advisory (AOI)**

* **`RewardPredictor`**, **`FailurePredictor`**, **`CostPerformanceEstimator`** (`ports/advisory.py`): Return calibrated `Prediction` objects (defined in `domain/work.py`) in shadow mode for filtering/ranking.
