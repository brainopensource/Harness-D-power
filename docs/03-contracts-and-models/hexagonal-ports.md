# **Hexagonal Interface Ports**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

All kernel components interact exclusively via stable `typing.Protocol` interfaces. Full signatures live in the [Architecture Specification Blueprint](../reference/SAGIHA2%20Architecture%20Specification%20Blueprint.md); this module is the normative index and the rules that govern the boundary.

## **Four Contract Rules**

1. **No `Dict[str, Any]` crosses a port.** Every payload is a Pydantic model. Untyped dicts are *worse* coupling than a concrete class: consumers hardcode key names that no type checker can see, so contract drift is silent and unrefactorable. The previous port set returned bare dicts from `search_similar`, `query_ast_symbols`, `get_definition`, `get_references`, `search_facts`, and `propose_harness_mutation` — defeating the purpose of adopting Pydantic at all.

2. **Ports speak domain language, never storage language.** `remember()` / `recall()`, not `store_vector(key, vector)`. A port phrased in storage terms is a driver wearing a Protocol; it welds one implementation class into the core and breaks at the first migration.

3. **All timestamps are timezone-aware UTC.** Naive datetimes are a schema violation, because bi-temporal comparison across adapters either raises or silently misorders.

4. **Verification is static plus conformance, never `isinstance`.** `@runtime_checkable` checks method *presence* only — an adapter whose method takes entirely different arguments passes it — so it provides false confidence at runtime cost. Ports are verified by `mypy`/`pyright` in strict mode plus a per-port behavioral suite in `tests/contracts/`, parametrized over every adapter. See [Port Conformance Testing](../06-guides-and-patterns/port-conformance-testing.md).

## **Port Index**

### Model & Control
| Port | Responsibility |
| :---- | :---- |
| **`ModelProvider`** | Streaming, completion, tool-schema translation, retries, token accounting, cache breakpoints. The record/replay cassette implements this same Protocol. |
| **`PolicyEngine`** | Authorizes every effect; mints capability `Grant`s. The Control layer's interface. |
| **`ResourceGovernor`** | Global admission control: concurrency, spend, rate limits, sandbox and server pool sizes. |

### Memory & Retrieval
| Port | Responsibility |
| :---- | :---- |
| `ShortTermMemory` | Append and retrieve trajectory steps for the active session. |
| **`Memory`** | Durable knowledge: `remember` / `recall` / `invalidate`. No vectors in the signature. |
| **`EmbeddingProvider`** | Text → vectors. Swappable independently of the store. |
| `Indexer` | **Query-shaped**: `find_symbols`, `get_skeleton`, `neighbors`. Never returns ASTs or bulk tables. |
| **`CodeGraph`** | Deterministic structure from Tree-sitter and git; `impacted_by` for partitioning parallel work. |
| `LSPAdapter` | Diagnostics, definitions, references. Returns typed `Symbol` and `DiagnosticItem`. |

### Execution
| Port | Responsibility |
| :---- | :---- |
| **`Workspace`** | `read`, `write`, `apply_edit`, `run`, `checkpoint`, `restore`. **No `get_path()`.** Side-effecting methods require a `Grant`. |
| `WorktreeManager` | `allocate`, **`materialize`**, `release`. Returns a `Workspace`, not a path. |
| `ToolRegistry` | Register schemas with an `EffectClass`; dispatch under a `Grant`. Open tool namespace. |
| **`TrajectoryStore`** | Append-only steps and scores; source of truth for replay, audit, and training data. |

### Orchestration & Improvement
| Port | Responsibility |
| :---- | :---- |
| `Orchestrator` | Executes a `TaskSpec`, streaming trajectory steps. |
| **`CandidateSearch`** | `propose` / `evaluate` / `select`. Best-of-N with sequential repair — deliberately not named MCTS, which requires a persistent tree, visit counts, and backpropagation that this port has none of. |
| `Evaluator` | Runs a `TaskSpec` against a **pristine injected** test suite, returning a `GateReport`. |
| `MetaImprover` | Proposes mutations restricted to the mutable surface, outside the trusted computing base. |

### Advisory (AOI)
`RewardPredictor`, `FailurePredictor`, `CostPerformanceEstimator` — all return a calibrated `Prediction`, all ship in shadow mode. Advisory only; they rank and filter but never admit or reject.

## **Ports the Previous Revision Lacked**

`ModelProvider`, `PolicyEngine`, `ResourceGovernor`, `EmbeddingProvider`, `CodeGraph`, `TrajectoryStore`. Their absence was structural rather than cosmetic: the system had **no contract for its single most important dependency**, and the CAR model's entire Control layer had no interface at all.

## **Removed or Reshaped**

| Was | Now | Why |
| :---- | :---- | :---- |
| `LongTermMemory.store_vector` | `Memory.remember/recall` | Storage-language port; could not accept the roadmap's own Day-2 target |
| `Workspace.get_path()` | Mediated read/write/run | A real path lets consumers bypass the port, foreclosing container and remote runtimes |
| `TreeSearchOrchestrator` | `CandidateSearch` | Honest naming: the port described best-of-N, not tree search |
| `KnowledgeGraph` (unified) | `CodeGraph` + episodic `Memory` | Deterministic structure must not pass through probabilistic extraction |
| `@runtime_checkable` everywhere | Static typing + conformance suites | Presence checks give false confidence about signatures |
