# **Hexagonal Interface Ports**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

All kernel components interact exclusively via stable `typing.Protocol` interfaces. Full signatures live in the [Architecture Specification Blueprint](../reference/SAGIHA%20Architecture%20Specification%20Blueprint.md); this module is the normative index and the rules that govern the boundary.

## **Four Contract Rules**

1. **No `Dict[str, Any]` crosses a port.** Every payload is a Pydantic model. Untyped dicts are *worse* coupling than a concrete class: consumers hardcode key names that no type checker can see, so contract drift is silent and unrefactorable. (Note: JSON Schema definitions and Tool arguments are explicitly exempted and allowed to use dicts).

2. **Ports speak domain language, never storage language.** `remember()` / `recall()`, not `store_vector(key, vector)`. A port phrased in storage terms is a driver wearing a Protocol; it welds one implementation class into the core and breaks at the first migration.

3. **All timestamps are timezone-aware UTC.** Naive datetimes are a schema violation, because bi-temporal comparison across adapters either raises or silently misorders.

4. **Verification is static plus conformance, never `isinstance`.** `@runtime_checkable` checks method *presence* only — an adapter whose method takes entirely different arguments passes it — so it provides false confidence at runtime cost. Ports are verified by `mypy`/`pyright` in strict mode plus a per-port behavioral suite in `tests/contracts/`, parametrized over every adapter. See [Port Conformance Testing](../06-guides-and-patterns/port-conformance-testing.md).

## **Port Index**

### Model & Control
| Port | Responsibility |
| :---- | :---- |
| **`ModelProvider`** | Streaming (`AsyncIterator[StreamEvent]`) with token accounting on completion, completion dispatches, reasoning blocks (`ThinkingContent`/`ReasoningBlock`), tool-schema translation, retries, and prompt cache breakpoints. Conformance tests: `test_reasoning_block_round_trip_byte_identical`, `test_stream_emits_exactly_one_usage_before_end`. The record/replay cassette implements this same Protocol. |
| **`PolicyEngine`** | Authorizes dispatches. Grants never leave the dispatch choke point (`kernel/dispatch.py`). Port methods are module-private to the kernel; authorization is enforced by reachability, not by token possession. Conformance test: `test_forged_grant_is_rejected_at_dispatch` |
| **`ResourceGovernor`** | Global admission control: concurrency, spend, rate limits, sandbox and server pool sizes. |

### Memory & Retrieval
| Port | Responsibility |
| :---- | :---- |
| `ShortTermMemory` | Append and retrieve trajectory steps for the active session. |
| **`Memory`** | Durable knowledge: `remember` / `recall` / `invalidate` with trust-provenance tagging. No raw vectors in the signature. |
| **`EmbeddingProvider`** | Text → vectors. Swappable independently of the store. |
| `Indexer` | **Query-shaped**: `find_symbols`, `get_skeleton`, `neighbors`. Returns ranked `RetrievalHit`. Never returns raw ASTs or bulk tables. |
| **`CodeGraph`** | Deterministic code structure from Tree-sitter and git; `upsert_edges`, `impacted_by`, `callers_of`, `co_changed_with`. |
| `LSPAdapter` | Diagnostics, definitions, references. Returns typed `Symbol` and `DiagnosticItem`. |

```python
class CodeGraph(Protocol):
    async def upsert_edges(self, edges: list[GraphEdge]) -> None: ...
    async def impacted_by(self, file_path: str, hops: int = 2) -> list[str]: ...
    async def callers_of(self, symbol: SymbolRef) -> list[SymbolRef]: ...
    async def co_changed_with(self, path: str, since: datetime) -> list[CoChange]: ...

class RetrievalHit(BaseModel):
    path: str
    chunk: str
    score: float  # backend-agnostic relevance score, normalized 0-1
    metadata: dict[str, Any] = {}
```

### Execution
| Port | Responsibility |
| :---- | :---- |
| **`Workspace`** | `read`, `write`, `apply_edit(self, request: EditRequest) -> EditResult`, `run`, `checkpoint`, `restore`. **No `get_path()`.** |
| `WorktreeManager` | `allocate`, **`materialize`**, `release`. Returns a `Workspace`, not a path. |
| `ToolRegistry` | Register schemas with an `EffectClass`; dispatch. Open tool namespace. |
| **`TrajectoryStore`** | Append-only steps and scores; source of truth for replay, audit, and training data. |
| **`Toolchain`** | `detect`, `test`, `typecheck`, `lint`, `coverage`. Python adapter is the only v1 implementation. The port exists so gates never hardcode pytest/pyright. |

```python
class Toolchain(Protocol):
    async def detect(self, root: Path) -> ToolchainInfo: ...
    async def test(self, selector: str | None = None, pristine: bool = True) -> TestReport: ...
    async def typecheck(self) -> list[Diagnostic]: ...
    async def lint(self) -> list[Diagnostic]: ...
    async def coverage(self) -> CoverageReport: ...
```

### Orchestration & Improvement
| Port | Responsibility |
| :---- | :---- |
| `Orchestrator` | Executes a `TaskSpec`, streaming events (`AsyncIterator[Event]`). |
| **`CandidateSearch`** | `propose` / `evaluate` / `select`. Best-of-N with sequential repair — deliberately not named MCTS. |
| `Evaluator` | Runs a `TaskSpec` against a **pristine injected** test suite, returning a `GateReport`. |
| `MetaImprover` | Proposes mutations restricted to the mutable surface, outside the trusted computing base. |

### Advisory (AOI)
`RewardPredictor`, `FailurePredictor`, `CostPerformanceEstimator` — all return a calibrated `Prediction`, all ship in shadow mode. Advisory only; they rank and filter but never admit or reject.
