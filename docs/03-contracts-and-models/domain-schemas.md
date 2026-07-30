---
status: normative
updated: 2026-07-29
---

# **Domain Schemas & Data Models**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

Frozen Pydantic v2 models used throughout the kernel.

> [!IMPORTANT]
> **The code is the contract.** The models described here live in `src/sagiha/domain/` — see the
> [module mapping](../implementation/contracts-to-code.md#module-mapping) for exactly which file
> defines what. This document keeps the *rules and rationale* — why a field exists, why it is
> shaped the way it is — not a second copy of the Python. Once a symbol exists in `src/`, its
> markdown definition is deleted, not synced.

Every model is `frozen=True` unless explicitly noted otherwise: a mutated trajectory step or gate
report is an audit record that no longer reconstructs what happened.

## **Identity & Time**

* **`utc_now()`** (`domain/identity.py`) — the single source of time, returning **timezone-aware UTC**. A system-wide invariant, not a convention: bi-temporal memory compares valid-time against transaction-time across adapters, and mixing naive with aware datetimes raises at runtime or silently misorders across DST boundaries.

* **`StepId`** (`domain/identity.py`) — **Trajectory identity is a DAG, not a counter**: parallel candidates branch from a shared ancestor, and a monotonic integer cannot express that.

## **Tools**

* **`ToolCall`** (`domain/content.py`) — `call_id`, **`tool_name: str`**, `arguments`, `effect`. The tool namespace is **open**, validated against the registry at dispatch.

* **`EffectClass`** (`domain/content.py`) — `PURE` / `IDEMPOTENT` / `DESTRUCTIVE`. Governs replay safety; without it, replaying a recorded trajectory re-executes `git push` and `rm`.

* **`ContentBlock`** (`domain/content.py`) — typed content (`text`, `reasoning`, `tool_use`, `tool_result`, `image`, `resource`, `diagnostic`), a discriminated union mirroring MCP content blocks.

* **`ReasoningBlock`** — opaque provider-native reasoning, round-tripped **verbatim**. Extended-thinking blocks carry signatures that must be returned unmodified to continue a tool-use turn. A separate `summary` field carries the human-readable gloss.

* **`Message`**, **`ModelRequest`** (`domain/content.py`) — a role-tagged list of `ContentBlock`s, and the request envelope sent to a `ModelProvider`.

Tool return payloads referenced by the [Tool Catalog](./tool-catalog.md) — `DirEntry`, `Match`,
`CommandResult`, `GitResult`, `SearchResult`, `Symbol` — all live in `domain/content.py` and are
all frozen.

* **`ToolResult`** (`domain/content.py`) — `content: list[ContentBlock]` rather than a stringified `output`, plus **`truncated`** and **`full_output_uri`**. Tool output overflowing the context window is a top-tier practical failure mode, so truncation is explicit and the full payload stays addressable rather than silently vanishing.

## **Trajectory**

* **`ReasoningBlock`** — opaque provider-native reasoning, round-tripped **verbatim** (see above).

* **`TrajectoryStep`** (`domain/trajectory.py`) — frozen: `step_id`, `reasoning`, `summary`, `tool_calls`, `tool_results`, `timestamp`.

* **`StepScored`** (`domain/trajectory.py`) — scores emitted as a **separate event**, not written back into a stored step. This is what makes the append-only claim true.

* **`Event`** (`domain/events.py`) — the base every bus event extends: `event`, `schema_version`, `run_id`, `step_id`, aware-UTC `timestamp`. The full registry is the [Event Catalog](../04-workflows-and-loops/event-catalog.md), itself generated from `domain/events.py`.

* **`StreamEvent`** (`domain/trajectory.py`) — events emitted by the `ModelProvider` during streaming: `BlockStart`, `BlockDelta`, `BlockEnd`, `UsageReported`, `StreamEnd` — a discriminated union. Usage arrives as a terminal event rather than a return value, because a stream that cannot report tokens leaves spend enforcement, cost-per-success, and cache-hit ratio unmeasured on the default interactive path.

* **`TokenUsage`** (`domain/trajectory.py`) — `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_tokens`, `reasoning_tokens`.

**Conformance requirement**: every adapter emits exactly one `UsageReported` before `StreamEnd`.
Without that test an adapter can silently report zeros and the `ResourceGovernor` never fires.

## **Work & Evaluation**

* **`TaskSpec`** (`domain/work.py`) — frozen. Amended by **revision**, never mutation: a mid-run
  goal change produces a new `TaskSpec` with `revision + 1` and the prior `task_id`, so the
  trajectory records what the agent was actually graded against at each step. `profile` selects
  the [execution profile](../02-architecture/execution-profiles.md) — a `str` rather than an enum,
  so third-party profiles need no contract change. See [Task & Acceptance](./task-and-acceptance.md).

* **`AcceptanceCriterion`** (`domain/work.py`) — `description` (human-readable; enters the prompt), `check` (machine-executable, run via `Toolchain`), `required` (non-required criteria rank but never admit).

* **`CostSummary`** (`domain/work.py`) — `usd`, `input_tokens`, `output_tokens`, `wall_clock_s`, `model_calls`.

* **`CriterionResult`** (`domain/work.py`) — the outcome of a machine-checkable acceptance criterion.

* **`GateReport`** (`domain/work.py`) — `criteria`, `no_new_suppressions`, **`tests_unmodified`**, `coverage_not_decreased`, `diff_within_bounds`, and an `admitted` / `acceptance_met` property requiring all of them. **Hard gates are separate from soft scores**: diagnostic deltas and coverage are proxies gamed by deleting failing code, adding suppressions, widening types, or swallowing exceptions, so they may rank candidates but never admit one.

> [!IMPORTANT]
> **A run with no gates produces no `GateReport`** — `run.completed` carries `gate_report: None` and
> `gate.evaluated` is never emitted. `acceptance_met` is vacuously `True` over an empty `criteria`
> tuple, so an empty report would claim `admitted=True` and a benchmark reporter or the outer loop
> would count an ungated chat turn as a passed coding task. **Absence of a verdict and a verdict of
> "pass" must never share a representation.** See [Execution Profiles](../02-architecture/execution-profiles.md).

* **`ReviewReport`**, **`ReviewFinding`** (`domain/work.py`) — design-quality assessment. **Never enters `GateReport`**: it ranks candidates and informs the human, and a soft score that can admit is not a soft score.

* **`Edit`**, **`EditRequest`**, **`HunkResult`**, **`EditResult`** (`domain/work.py`) — per-hunk outcomes plus a `syntax_valid` Tree-sitter check. Edit application is the highest-frequency operation in the system.

* **`Prediction`** (`domain/work.py`) — `value`, `confidence`, **`calibrated`**, **`shadow_mode`**. AOI outputs are never bare floats, because a scalar carries no way to express uncertainty and therefore no basis for deciding whether it may be acted upon.

* **`SubagentReport`** (`domain/work.py`) — result payload from a sub-agent execution.

## **Memory**

Trust is a property of **content provenance**, not of the tool that emitted it. A static per-tool
trust flag is launderable: fetch a poisoned page (untrusted), summarize it, `remember` it, and it
returns from `recall` labelled trusted. Provenance travels with the record and is propagated by the
tool layer — the model does not get to declare it.

* **`Provenance`** (`domain/memory.py`) — `OPERATOR` (the human's turn — authoritative), `HARNESS` (tree-sitter, LSP, git — deterministic, trusted), `MODEL` (the agent's own reasoning), `EXTERNAL` (repo content, web, MCP servers — untrusted).

* **`MemoryRecord`** (`domain/memory.py`) — `content`, `kind`, `provenance` (required, never inferred), `source_uri`, `links` (memory_ids — the knowledge net), `valid_from`, `valid_to` (bi-temporal invalidation).

* **`RecallQuery`**, **`Recall`** (`domain/memory.py`) — `as_of` supports bi-temporal reads (recall what was believed then); `score` is normalized 0–1.

Anything returning `Provenance.EXTERNAL` is wrapped in `<untrusted-data>` by the prompt assembler at
render time — not at storage time, so the label cannot be stripped by a round trip.

## **Retrieval & Graph**

* **`RetrievalHit`** (`domain/graph.py`) — `path`, `chunk`, `score` (backend-agnostic relevance, normalized 0–1), `metadata` (exempt from contract rule 1 — open-shaped backend annotations).

* **`SymbolRef`**, **`GraphEdge`**, **`CoChange`**, **`DiagnosticItem`** (`domain/graph.py`) — deterministic structural facts, produced by the indexer and LSP adapter, never by LLM extraction.

## **Toolchain**

The port exists so gates never hardcode `pytest` and `pyright`. `ToolchainInfo`, `TestReport`,
`CoverageReport` (`domain/toolchain.py`) are its payloads.

## **Control**

* **`Grant`** (`domain/control.py`) — capability token scoped to tool and paths, with expiry. Minted only by `PolicyEngine.authorize()`, never crosses a port signature, and is re-verified at the point of effect (`verify_grant`) rather than trusted at issuance.
  **It never crosses a public signature** — it is held only inside `kernel/dispatch.py`. Possession
  confers nothing; reachability is the control, and reachability is enforced by module structure plus
  `import-linter`. See [CAR Model](../02-architecture/car-model.md).

* **`Decision`** (`domain/control.py`) — `allowed`, `reason`, `requires_human`, `grant_id` (correlation only — the `Grant` itself never leaves dispatch).

* **`RunContext`** (`domain/control.py`) — `run_id`, `autonomy_level`, `workspace_root` (opaque identifier, not a `Path`), `budget_remaining_usd`.

* **`TaskStatus`** (`domain/control.py`) — mirrors the A2A task lifecycle so a remote pilot needs no translation layer.
