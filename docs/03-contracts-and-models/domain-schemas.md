# **Domain Schemas & Data Models**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

Frozen Pydantic v2 models used throughout the kernel. Full definitions in the [Architecture Specification Blueprint](../reference/SAGIHA2%20Architecture%20Specification%20Blueprint.md).

## **Identity & Time**

* **`utc_now()`** — the single source of time, returning **timezone-aware UTC**. A system-wide invariant, not a convention: bi-temporal memory compares valid-time against transaction-time across adapters, and mixing naive with aware datetimes raises at runtime or silently misorders across DST boundaries. The previous schema's `Field(default_factory=datetime.utcnow)` produced naive datetimes and is deprecated in Python 3.12.

* **`StepId`** — `(run_id, branch_id, seq, parent)`. **Trajectory identity is a DAG, not a counter.** The previous `step_id: int` could not represent a branching search, which made per-step scoring over parallel candidates unimplementable on the system's own schema.

## **Tools**

* **`ToolCall`** — `call_id`, **`tool_name: str`**, `arguments`, `effect`. The tool namespace is **open**, validated against the registry at dispatch. The previous closed `ActionType` enum (six fixed members) could not represent tools discovered dynamically from an MCP server, directly contradicting the premise that every capability is an MCP server.

* **`EffectClass`** — `PURE` / `IDEMPOTENT` / `DESTRUCTIVE`. Governs replay safety; without it, replaying a recorded trajectory re-executes `git push` and `rm`.

* **`ContentBlock`** — typed content (`text`, `image`, `resource`, `diagnostic`), mirroring MCP content blocks.

* **`ToolResult`** — `content: list[ContentBlock]` rather than a stringified `output`, plus **`truncated`** and **`full_output_uri`**. Tool output overflowing the context window is a top-tier practical failure mode, so truncation is explicit and the full payload stays addressable rather than silently vanishing.

## **Trajectory**

* **`ReasoningBlock`** — opaque provider-native reasoning, round-tripped **verbatim**. Extended-thinking blocks carry signatures that must be returned unmodified to continue a tool-use turn; the previous `thought: str` field would have broken the signature, forfeiting reasoning continuity and cache hits. A separate `summary` field carries the human-readable gloss.

* **`TrajectoryStep`** — frozen: `step_id`, `reasoning`, `summary`, `tool_calls`, `tool_results`, `timestamp`.

* **`StepScored`** — scores emitted as a **separate event**, not written back into a stored step. This is what makes the append-only claim true; the previous mutable `prm_score: float = 0.0` field, backfilled in place, contradicted the document's own event-sourcing guarantee.

## **Work & Evaluation**

* **`TaskSpec`** — `task_id`, `goal`, **`acceptance: list[AcceptanceCriterion]`**, `parent_task_id`, `status`. See [Task & Acceptance](./task-and-acceptance.md).

* **`GateReport`** — `tests_pass`, `no_new_suppressions`, **`tests_unmodified`**, `coverage_not_decreased`, `diff_within_bounds`, and an `admitted` property requiring all of them. **Hard gates are separate from soft scores**: diagnostic deltas and coverage are proxies gamed by deleting failing code, adding suppressions, widening types, or swallowing exceptions, so they may rank candidates but never admit one.

* **`EditResult`** — per-hunk outcomes plus a `syntax_valid` Tree-sitter check. Edit application is the highest-frequency operation in the system; the previous `apply_diff(...) -> bool` discarded which hunk failed and why, leaving the model unable to repair its own patch.

* **`Prediction`** — `value`, `confidence`, **`calibrated`**, **`shadow_mode`**. AOI outputs are never bare floats, because a scalar carries no way to express uncertainty and therefore no basis for deciding whether it may be acted upon.

## **Control**

* **`Grant`** — unforgeable capability token, scoped to tool and paths, with expiry. Minted only by `PolicyEngine`.
* **`Decision`** — `allowed`, `reason`, `requires_human`, optional `grant`.
* **`RunContext`** — `run_id`, `autonomy_level`, `workspace_root`, `budget_remaining_usd`.
* **`TaskStatus`** — `submitted`, `working`, `input-required`, `auth-required`, `completed`, `failed`, `canceled`. Now attached to `TaskSpec`; previously the enum existed but belonged to no model.
