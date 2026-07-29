---
status: normative
updated: 2026-07-29
---

# **Hexagonal Interface Ports**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

All kernel components interact exclusively via stable `typing.Protocol` interfaces.

> [!IMPORTANT]
> **This file and [Domain Schemas](./domain-schemas.md) are the contract.** There is no second copy —
> a contract stated in two places is a contradiction with a delay fuse, and the copy that retrieval
> surfaces is not reliably the correct one. `reference/` carries derivation and rationale only.
>
> When `src/sagiha/ports/` exists it supersedes this file, and these signatures are **deleted, not
> synced** — see [Contracts to Code](../implementation/contracts-to-code.md).

## **Five Contract Rules**

1. **No `Dict[str, Any]` crosses a port.** Every payload is a Pydantic model. Untyped dicts are *worse* coupling than a concrete class: consumers hardcode key names that no type checker can see, so contract drift is silent and unrefactorable. (Note: JSON Schema definitions and Tool arguments are explicitly exempted and allowed to use dicts).

2. **Ports speak domain language, never storage language.** `remember()` / `recall()`, not `store_vector(key, vector)`. A port phrased in storage terms is a driver wearing a Protocol; it welds one implementation class into the core and breaks at the first migration.

3. **All timestamps are timezone-aware UTC.** Naive datetimes are a schema violation, because bi-temporal comparison across adapters either raises or silently misorders.

4. **Every port must be implementable over a wire.** Payloads are Pydantic-serializable and every
   method is `async` — no `Path`, file handle, callable, generator, or live object crosses. This is
   what keeps a future compiled sidecar an adapter swap rather than a refactor of every consumer, and
   it costs nothing today. See [Remoteable Ports](../02-architecture/remoteable-ports.md).

5. **Verification is static plus conformance, never `isinstance`.** `@runtime_checkable` checks method *presence* only — an adapter whose method takes entirely different arguments passes it — so it provides false confidence at runtime cost. Ports are verified by `mypy`/`pyright` in strict mode plus a per-port behavioral suite in `tests/contracts/`, parametrized over every adapter. See [Port Conformance Testing](../06-guides-and-patterns/port-conformance-testing.md).

## **Port Index**

Ports marked **optional** may be left unbound by an
[execution profile](../02-architecture/execution-profiles.md) — a `chat` run mounts no `Workspace`
and no `Evaluator`. Every unmarked port is bound in **every** profile without exception: those are
the harness itself, not what it is pointed at.

### Model & Control
| Port | Responsibility |
| :---- | :---- |
| **`ModelProvider`** | Streaming (`AsyncIterator[StreamEvent]`) with token accounting on completion, completion dispatches, reasoning blocks (`ThinkingContent`/`ReasoningBlock`), tool-schema translation, retries, and prompt cache breakpoints. Conformance tests: `test_reasoning_block_round_trip_byte_identical`, `test_stream_emits_exactly_one_usage_before_end`. The record/replay cassette implements this same Protocol. |
| **`PolicyEngine`** | Authorizes dispatches. Grants never leave the dispatch choke point (`kernel/dispatch.py`). Port methods are module-private to the kernel; authorization is enforced by reachability, not by token possession. Conformance test: `test_forged_grant_is_rejected_at_dispatch` |
| **`ResourceGovernor`** | Global admission control: concurrency, spend, rate limits, sandbox and server pool sizes. |

> [!IMPORTANT]
> **Model routing is composition, not a port method.** The harness uses several models per run —
> frontier for planning, workhorse for edits, fast for compaction
> ([Model Tiering](../05-tech-stack/llm-providers-and-economics.md#2-model-tiering)). The composition
> root binds **one `ModelProvider` per role**, and callers request a *role*, never a model name.
>
> Adding `route()` or a `tier=` parameter to `ModelProvider` is the tempting wrong turn: it moves
> policy inside an adapter, makes every adapter responsible for a decision that belongs to config, and
> breaks the cassette substitution that lets the whole kernel run in CI with zero API calls — a
> recording satisfies a narrow port, not a router.

Protocol definitions: `ports/model.py`, `ports/policy.py`, `ports/governor.py`.

### Memory & Retrieval
| Port | Responsibility |
| :---- | :---- |
| `ShortTermMemory` | Append and retrieve trajectory steps for the active session. |
| **`Memory`** | Durable knowledge: `remember` / `recall` / `invalidate` with trust-provenance tagging. No raw vectors in the signature. |
| **`EmbeddingProvider`** | Text → vectors. Swappable independently of the store. |
| `Indexer` | **Query-shaped**: `find_symbols`, `get_skeleton`, `neighbors`. Returns ranked `RetrievalHit`. Never returns raw ASTs or bulk tables. |
| **`CodeGraph`** | Deterministic code structure from Tree-sitter and git; `upsert_edges`, `impacted_by`, `callers_of`, `co_changed_with`. |
| `LSPAdapter` | Diagnostics, definitions, references. Returns typed `Symbol` and `DiagnosticItem`. |

Protocol definitions: `ports/memory.py` (`ShortTermMemory`, `Memory`), `ports/embedding.py`,
`ports/indexer.py`, `ports/code_graph.py`, `ports/lsp.py`. Payload models —
including `RetrievalHit` — live in `domain/graph.py` and `domain/content.py`.

### Execution
| Port | Responsibility |
| :---- | :---- |
| **`Workspace`** *(optional)* | `read`, `write`, `apply_edit(self, request: EditRequest) -> EditResult`, `run`, `checkpoint`, `restore`. **No `get_path()`.** |
| `WorktreeManager` *(optional)* | `allocate`, **`materialize`**, `release`. Returns a `Workspace`, not a path. |
| `ToolRegistry` | Register schemas with an `EffectClass`; dispatch. Open tool namespace. |
| **`TrajectoryStore`** | Append-only steps and scores; source of truth for replay, audit, and training data. |
| **`Toolchain`** *(optional)* | `detect`, `test`, `typecheck`, `lint`, `coverage`. Python adapter is the only v1 implementation. The port exists so gates never hardcode pytest/pyright. `detect(root: str)` is workspace-relative — never a `Path`. |

Protocol definitions: `ports/workspace.py` (`Workspace`, `WorktreeManager`), `ports/tool_registry.py`,
`ports/trajectory.py`, `ports/toolchain.py`.

### Orchestration & Improvement
| Port | Responsibility |
| :---- | :---- |
| `Orchestrator` | Executes a `TaskSpec`, streaming events (`AsyncIterator[Event]`). |
| **`CandidateSearch`** | `propose` / `evaluate` / `select`. Best-of-N with sequential repair — deliberately not named MCTS. |
| `Evaluator` *(optional)* | Runs a `TaskSpec` against a **pristine injected** test suite, returning a `GateReport`. Unbound under `gates = "none"`, in which case **no `GateReport` exists** — not an empty one. |
| **`Reviewer`** *(optional)* | Design-quality assessment from an independent judge. Returns a `ReviewReport` — a **soft score that ranks, never a gate that admits**. |
| `MetaImprover` | Proposes mutations restricted to the mutable surface, outside the trusted computing base. |

Protocol definitions: `ports/orchestrator.py`, `ports/search.py`, `ports/evaluator.py`,
`ports/reviewer.py`, `ports/meta_improver.py`.

**Why a port and not a gate.** Every hard gate in this system rewards *tests pass, nothing regressed,
diff bounded* — all mechanical, all satisfiable by code no engineer would merge. Nothing measures
whether the design is any good, which is precisely the part "senior engineer" refers to.

The instinct to make it a gate must be resisted. An LLM judge is a proxy, and proxies are gameable; a
gate that can be talked out of a denial is not a gate. `Reviewer` therefore ranks candidates and
surfaces findings to the human, and its output never appears in `GateReport`. Two constraints keep it
honest: the judge is a **frontier model, and never the model that generated the candidate**, and its
scores are logged against eventual human accept/reject so the rubric's calibration is itself
measurable.

### Advisory (AOI)
`RewardPredictor`, `FailurePredictor`, `CostPerformanceEstimator` — all return a calibrated `Prediction`, all ship in shadow mode. Advisory only; they rank and filter but never admit or reject.

Protocol definitions: `ports/advisory.py`. `Prediction` lives in `domain/work.py`.
