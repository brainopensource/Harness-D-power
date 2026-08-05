---
status: historical
updated: 2026-07-29
---
# **Domain Schemas & Data Models**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

Domain models in `src/sagiha/domain/` are frozen (`frozen=True`) Pydantic v2 schemas. Code is the authoritative contract; see [module mapping](../implementation/contracts-to-code.md#module-mapping).

## **Identity & Time**

* **`utc_now()`** (`domain/identity.py`): Returns timezone-aware UTC. Enforces system-wide temporal consistency across adapters.
* **`StepId`** (`domain/identity.py`): DAG identity representing branching trajectories.

## **Tools**

* **`ToolCall`** (`domain/content.py`): `call_id`, `tool_name: str` (open namespace), `arguments`, `effect`.
* **`EffectClass`** (`domain/content.py`): `PURE` | `IDEMPOTENT` | `DESTRUCTIVE`. Controls trajectory replay safety.
* **`ContentBlock`** (`domain/content.py`): Discriminated union (`text`, `reasoning`, `tool_use`, `tool_result`, `image`, `resource`, `diagnostic`).
* **`ReasoningBlock`**: Provider-native thinking returned verbatim. Includes extended-thinking signatures and `summary`.
* **`Message`**, **`ModelRequest`** (`domain/content.py`): Role-tagged `ContentBlock` list and request envelope for `ModelProvider`.
* **`ToolResult`** (`domain/content.py`): `content: list[ContentBlock]`, `truncated: bool`, `full_output_uri: str | None`. Explicit context truncation handling.
* **Tool Payloads** (`domain/content.py`): `DirEntry`, `Match`, `CommandResult`, `GitResult`, `SearchResult`, `Symbol` (referenced in [Tool Catalog](./tool-catalog.md)).

## **Trajectory**

* **`TrajectoryStep`** (`domain/trajectory.py`): Immutable step record (`step_id`, `reasoning`, `summary`, `tool_calls`, `tool_results`, `timestamp`).
* **`StepScored`** (`domain/trajectory.py`): Evaluation scores emitted as separate events to maintain append-only trajectories.
* **`Event`** (`domain/events.py`): Base bus event (`event`, `schema_version`, `run_id`, `step_id`, aware-UTC `timestamp`). See [Event Catalog](../04-workflows-and-loops/event-catalog.md).
* **`StreamEvent`** (`domain/trajectory.py`): Discriminated streaming union (`BlockStart`, `BlockDelta`, `BlockEnd`, `UsageReported`, `StreamEnd`). Adapters must emit exactly one `UsageReported` prior to `StreamEnd`.
* **`TokenUsage`** (`domain/trajectory.py`): `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_tokens`, `reasoning_tokens`.

## **Work & Evaluation**

* **`TaskSpec`** (`domain/work.py`): Immutable specification amended via revision (`revision + 1`). `profile` string selects [execution profile](../02-architecture/execution-profiles.md). See [Task & Acceptance](./task-and-acceptance.md).
* **`AcceptanceCriterion`** (`domain/work.py`): `description`, `check` (machine-executable command), `required` (boolean admittance gate).
* **`CostSummary`** (`domain/work.py`): `usd`, `input_tokens`, `output_tokens`, `wall_clock_s`, `model_calls`.
* **`CriterionResult`** (`domain/work.py`): Machine check outcome.
* **`GateReport`** (`domain/work.py`): `criteria`, `no_new_suppressions`, `tests_unmodified`, `coverage_not_decreased`, `diff_within_bounds`, and `admitted`/`acceptance_met` property requiring all gates. Ungated runs set `gate_report: None` (distinguishes absence of verdict from pass; see [Execution Profiles](../02-architecture/execution-profiles.md)).
* **`ReviewReport`**, **`ReviewFinding`** (`domain/work.py`): Soft design-quality assessment (ranks candidates, never enters `GateReport`).
* **`Edit`**, **`EditRequest`**, **`HunkResult`**, **`EditResult`** (`domain/work.py`): Per-hunk outcome payloads with Tree-sitter `syntax_valid` checks.
* **`Prediction`** (`domain/work.py`): Calibrated uncertainty outputs (`value`, `confidence`, `calibrated`, `shadow_mode`).
* **`SubagentReport`** (`domain/work.py`): Payload returned from sub-agent execution.

## **Memory**

* **`Provenance`** (`domain/memory.py`): Content origin tag: `OPERATOR` (authoritative), `HARNESS` (deterministic/trusted), `MODEL` (agent reasoning), `EXTERNAL` (untrusted repo/web/MCP data).
* **`MemoryRecord`** (`domain/memory.py`): `content`, `kind`, `provenance`, `source_uri`, `links`, `valid_from`, `valid_to` (bi-temporal limits).
* **`RecallQuery`**, **`Recall`** (`domain/memory.py`): Bi-temporal query (`as_of`) returning normalized scores (0–1). Prompt renderer wraps `EXTERNAL` records in `<untrusted-data>`.

## **Retrieval & Graph**

* **`RetrievalHit`** (`domain/graph.py`): `path`, `chunk`, `score` (0–1), `metadata` (open backend annotations).
* **`SymbolRef`**, **`GraphEdge`**, **`CoChange`**, **`DiagnosticItem`** (`domain/graph.py`): Deterministic structural objects emitted by indexer and LSP adapters.

## **Toolchain**

* Payloads in `domain/toolchain.py`: `ToolchainInfo`, `TestReport`, `CoverageReport`.

## **Control**

* **`Grant`** (`domain/control.py`): Time-bounded capability token for specific tools/paths. Issued by `PolicyEngine.authorize()`, evaluated at `verify_grant`, and confined to `kernel/dispatch.py`. See [CAR Model](../02-architecture/car-model.md).
* **`Decision`** (`domain/control.py`): `allowed`, `reason`, `requires_human`, `grant_id`.
* **`RunContext`** (`domain/control.py`): `run_id`, `autonomy_level`, `workspace_root`, `budget_remaining_usd`.
* **`TaskStatus`** (`domain/control.py`): Lifecycle status enum aligned with A2A protocol.
