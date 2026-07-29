# **Domain Schemas & Data Models**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

Frozen Pydantic v2 models used throughout the kernel. Full definitions in the [Architecture Specification Blueprint](../reference/SAGIHA%20Architecture%20Specification%20Blueprint.md).

## **Identity & Time**

* **`utc_now()`** — the single source of time, returning **timezone-aware UTC**. A system-wide invariant, not a convention: bi-temporal memory compares valid-time against transaction-time across adapters, and mixing naive with aware datetimes raises at runtime or silently misorders across DST boundaries.

* **`StepId`** — `(run_id, branch_id, seq, parent)`. **Trajectory identity is a DAG, not a counter.**

## **Tools**

* **`ToolCall`** — `call_id`, **`tool_name: str`**, `arguments`, `effect`. The tool namespace is **open**, validated against the registry at dispatch.

* **`EffectClass`** — `PURE` / `IDEMPOTENT` / `DESTRUCTIVE`. Governs replay safety; without it, replaying a recorded trajectory re-executes `git push` and `rm`.

* **`ContentBlock`** — typed content (`text`, `image`, `resource`, `diagnostic`), mirroring MCP content blocks.

```python
class TextBlock(BaseModel):
    kind: Literal["text"] = "text"
    text: str

class ReasoningBlock(BaseModel):
    kind: Literal["reasoning"] = "reasoning"
    provider: str
    opaque: dict[str, Any]  # provider-native, round-tripped verbatim
    summary: str = ""
    redacted: bool = False

class ToolUseBlock(BaseModel):
    kind: Literal["tool_use"] = "tool_use"
    call_id: str
    tool_name: str
    arguments: dict[str, Any]

class ToolResultBlock(BaseModel):
    kind: Literal["tool_result"] = "tool_result"
    call_id: str
    content: list["ContentBlock"]
    is_error: bool = False

ContentBlock = Annotated[
    TextBlock | ReasoningBlock | ToolUseBlock | ToolResultBlock | ImageBlock | ResourceBlock,
    Field(discriminator="kind"),
]

class Message(BaseModel):
    role: str
    content: list[ContentBlock]

class ModelRequest(BaseModel):
    messages: list[Message]
```

* **`ToolResult`** — `content: list[ContentBlock]` rather than a stringified `output`, plus **`truncated`** and **`full_output_uri`**. Tool output overflowing the context window is a top-tier practical failure mode, so truncation is explicit and the full payload stays addressable rather than silently vanishing.

## **Trajectory**

* **`ReasoningBlock`** — opaque provider-native reasoning, round-tripped **verbatim**. Extended-thinking blocks carry signatures that must be returned unmodified to continue a tool-use turn. A separate `summary` field carries the human-readable gloss.

* **`TrajectoryStep`** — frozen: `step_id`, `reasoning`, `summary`, `tool_calls`, `tool_results`, `timestamp`.

* **`StepScored`** — scores emitted as a **separate event**, not written back into a stored step. This is what makes the append-only claim true.

* **`StreamEvent`** — events emitted by the ModelProvider during streaming.

```python
class UsageReported(BaseModel):
    kind: Literal["usage"] = "usage"
    usage: TokenUsage

StreamEvent = Annotated[
    BlockStart | BlockDelta | BlockEnd | UsageReported | StreamEnd,
    Field(discriminator="kind"),
]
```

## **Work & Evaluation**

* **`TaskSpec`** — `task_id`, `goal`, **`acceptance: list[AcceptanceCriterion]`**, `parent_task_id`, `status`. See [Task & Acceptance](./task-and-acceptance.md).

* **`CriterionResult`** — the outcome of a machine-checkable acceptance criterion.

```python
class CriterionResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    description: str
    check: str
    passed: bool
    required: bool
    output: str = ""
    duration_ms: float = 0.0
```

* **`GateReport`** — `criteria`, `no_new_suppressions`, **`tests_unmodified`**, `coverage_not_decreased`, `diff_within_bounds`, and an `admitted` / `acceptance_met` property requiring all of them. **Hard gates are separate from soft scores**: diagnostic deltas and coverage are proxies gamed by deleting failing code, adding suppressions, widening types, or swallowing exceptions, so they may rank candidates but never admit one.

```python
class GateReport(BaseModel):
    criteria: tuple[CriterionResult, ...]
    no_new_suppressions: bool
    tests_unmodified: bool
    coverage_not_decreased: bool
    diff_within_bounds: bool

    @property
    def acceptance_met(self) -> bool:
        return all(c.passed for c in self.criteria if c.required)

    @property
    def admitted(self) -> bool:
        return self.acceptance_met and self.no_new_suppressions and self.tests_unmodified and self.coverage_not_decreased and self.diff_within_bounds
```

* **`EditResult`** — per-hunk outcomes plus a `syntax_valid` Tree-sitter check. Edit application is the highest-frequency operation in the system.

```python
class Edit(BaseModel):
    model_config = ConfigDict(frozen=True)
    old_string: str  # unique anchor; empty == insert at start
    new_string: str
    expected_occurrences: int = 1

class EditRequest(BaseModel):
    path: str
    edits: tuple[Edit, ...]

class HunkResult(BaseModel):
    applied: bool
    index: int
    reason: Literal["ok", "anchor_not_found", "ambiguous_anchor",
                    "skipped_after_failure", "syntax_invalid"] | None = None
    nearest_match: str | None = None

class EditResult(BaseModel):
    hunks: tuple[HunkResult, ...]
    syntax_valid: bool
```

* **`Prediction`** — `value`, `confidence`, **`calibrated`**, **`shadow_mode`**. AOI outputs are never bare floats, because a scalar carries no way to express uncertainty and therefore no basis for deciding whether it may be acted upon.

* **`SubagentReport`** — result payload from a sub-agent execution.

```python
class SubagentReport(BaseModel):
    model_config = ConfigDict(frozen=True)
    goal: str
    outcome: Literal["success", "failure", "partial", "timeout"]
    diff_summary: str
    artifacts: tuple[str, ...] = ()
    cost: CostSummary
    gate_result: GateReport | None = None
```

## **Control**

* **`Grant`** — unforgeable capability token, scoped to tool and paths, with expiry. Minted only by `PolicyEngine`.
* **`Decision`** — `allowed`, `reason`, `requires_human`, optional `grant`.
* **`RunContext`** — `run_id`, `autonomy_level`, `workspace_root`, `budget_remaining_usd`.
* **`TaskStatus`** — `submitted`, `working`, `input-required`, `auth-required`, `completed`, `failed`, `canceled`.
