---
status: normative
updated: 2026-07-29
---

# **Domain Schemas & Data Models**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

Frozen Pydantic v2 models used throughout the kernel.

> [!IMPORTANT]
> **This file is the contract for domain models**, alongside [Hexagonal Ports](./hexagonal-ports.md)
> for the Protocols. There is no second copy. When `src/sagiha/domain/` exists it supersedes this
> file — see [Contracts to Code](../implementation/contracts-to-code.md).

Every model here is `frozen=True` unless explicitly noted otherwise: a mutated trajectory step or
gate report is an audit record that no longer reconstructs what happened.

## **Identity & Time**

* **`utc_now()`** — the single source of time, returning **timezone-aware UTC**. A system-wide invariant, not a convention: bi-temporal memory compares valid-time against transaction-time across adapters, and mixing naive with aware datetimes raises at runtime or silently misorders across DST boundaries.

* **`StepId`** — **Trajectory identity is a DAG, not a counter**: parallel candidates branch from a
  shared ancestor, and a monotonic integer cannot express that.

```python
class StepId(BaseModel):
    model_config = ConfigDict(frozen=True)
    run_id: str
    branch_id: str
    seq: int
    parent: str | None = None
```

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

class ImageBlock(BaseModel):
    kind: Literal["image"] = "image"
    mime_type: str
    data_uri: str                  # data: or a resource URI; never a filesystem path

class ResourceBlock(BaseModel):
    kind: Literal["resource"] = "resource"
    uri: str
    mime_type: str | None = None
    text: str | None = None        # inline when small; else fetch by uri

class DiagnosticBlock(BaseModel):
    kind: Literal["diagnostic"] = "diagnostic"
    diagnostics: tuple["DiagnosticItem", ...]

ContentBlock = Annotated[
    TextBlock | ReasoningBlock | ToolUseBlock | ToolResultBlock
    | ImageBlock | ResourceBlock | DiagnosticBlock,
    Field(discriminator="kind"),
]

class Message(BaseModel):
    role: str
    content: list[ContentBlock]

class ModelRequest(BaseModel):
    messages: list[Message]
```

Tool return payloads referenced by the [Tool Catalog](./tool-catalog.md). All are frozen:

```python
class DirEntry(BaseModel):
    path: str
    kind: Literal["file", "dir", "symlink"]
    size_bytes: int | None = None

class Match(BaseModel):
    path: str
    line: int
    text: str

class CommandResult(BaseModel):
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    truncated: bool = False
    full_output_uri: str | None = None

class GitResult(BaseModel):
    op: str
    output: str
    commit_sha: str | None = None

class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str

class Symbol(BaseModel):
    ref: SymbolRef
    signature: str
    docstring: str = ""
```

* **`ToolResult`** — `content: list[ContentBlock]` rather than a stringified `output`, plus **`truncated`** and **`full_output_uri`**. Tool output overflowing the context window is a top-tier practical failure mode, so truncation is explicit and the full payload stays addressable rather than silently vanishing.

## **Trajectory**

* **`ReasoningBlock`** — opaque provider-native reasoning, round-tripped **verbatim**. Extended-thinking blocks carry signatures that must be returned unmodified to continue a tool-use turn. A separate `summary` field carries the human-readable gloss.

* **`TrajectoryStep`** — frozen: `step_id`, `reasoning`, `summary`, `tool_calls`, `tool_results`, `timestamp`.

* **`StepScored`** — scores emitted as a **separate event**, not written back into a stored step. This is what makes the append-only claim true.

* **`Event`** — the base every bus event extends. The full registry is the
  [Event Catalog](../04-workflows-and-loops/event-catalog.md).

```python
class Event(BaseModel):
    model_config = ConfigDict(frozen=True)
    event: str                                  # discriminator, e.g. "tool.call_requested"
    schema_version: int = 1                     # bumped per event type, not globally
    run_id: str
    step_id: StepId | None = None
    timestamp: datetime = Field(default_factory=utc_now)
```

* **`StreamEvent`** — events emitted by the `ModelProvider` during streaming. Usage arrives as a
  terminal event rather than a return value, because a stream that cannot report tokens leaves spend
  enforcement, cost-per-success, and cache-hit ratio unmeasured on the default interactive path.

```python
class BlockStart(BaseModel):
    kind: Literal["block_start"] = "block_start"
    index: int
    block_kind: Literal["text", "reasoning", "tool_use"]

class BlockDelta(BaseModel):
    kind: Literal["block_delta"] = "block_delta"
    index: int
    text: str = ""                        # text/reasoning increments
    partial_json: str = ""                # tool_use argument increments

class BlockEnd(BaseModel):
    kind: Literal["block_end"] = "block_end"
    index: int
    block: ContentBlock                   # the assembled, complete block

class UsageReported(BaseModel):
    kind: Literal["usage"] = "usage"
    usage: TokenUsage

class StreamEnd(BaseModel):
    kind: Literal["stream_end"] = "stream_end"
    stop_reason: Literal["end_turn", "tool_use", "max_tokens", "stop_sequence", "error"]

StreamEvent = Annotated[
    BlockStart | BlockDelta | BlockEnd | UsageReported | StreamEnd,
    Field(discriminator="kind"),
]

class TokenUsage(BaseModel):
    model_config = ConfigDict(frozen=True)
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int = 0            # populated where the provider supplies it
    cache_write_tokens: int = 0
    reasoning_tokens: int = 0
```

**Conformance requirement**: every adapter emits exactly one `UsageReported` before `StreamEnd`.
Without that test an adapter can silently report zeros and the `ResourceGovernor` never fires.

## **Work & Evaluation**

* **`TaskSpec`** — frozen. Amended by **revision**, never mutation: a mid-run goal change produces a
  new `TaskSpec` with `revision + 1` and the prior `task_id`, so the trajectory records what the agent
  was actually graded against at each step. `profile` selects the
  [execution profile](../02-architecture/execution-profiles.md) — a `str` rather than an enum, so
  third-party profiles need no contract change. See [Task & Acceptance](./task-and-acceptance.md).

```python
class AcceptanceCriterion(BaseModel):
    model_config = ConfigDict(frozen=True)
    description: str               # human-readable; enters the prompt
    check: str                     # machine-executable, run via Toolchain
    required: bool = True          # non-required criteria rank but never admit

class TaskSpec(BaseModel):
    model_config = ConfigDict(frozen=True)
    task_id: str
    revision: int = 0
    goal: str
    acceptance: tuple[AcceptanceCriterion, ...]
    profile: str = "coding"        # execution profile; resolved at composition, not an enum
    parent_task_id: str | None = None
    status: "TaskStatus" = "submitted"

class CostSummary(BaseModel):
    model_config = ConfigDict(frozen=True)
    usd: float
    input_tokens: int
    output_tokens: int
    wall_clock_s: float
    model_calls: int
```

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
    # Code-specific gates. None means "not applicable under this profile" —
    # never defaulted to True, which would read as "passed".
    no_new_suppressions: bool | None = None
    tests_unmodified: bool | None = None
    coverage_not_decreased: bool | None = None
    diff_within_bounds: bool | None = None

    @property
    def acceptance_met(self) -> bool:
        return all(c.passed for c in self.criteria if c.required)

    @property
    def admitted(self) -> bool:
        return self.acceptance_met and all(
            g is not False for g in (self.no_new_suppressions, self.tests_unmodified,
                                     self.coverage_not_decreased, self.diff_within_bounds)
        )
```

> [!IMPORTANT]
> **A run with no gates produces no `GateReport`** — `run.completed` carries `gate_report: None` and
> `gate.evaluated` is never emitted. `acceptance_met` is vacuously `True` over an empty `criteria`
> tuple, so an empty report would claim `admitted=True` and a benchmark reporter or the outer loop
> would count an ungated chat turn as a passed coding task. **Absence of a verdict and a verdict of
> "pass" must never share a representation.** See [Execution Profiles](../02-architecture/execution-profiles.md).

* **`ReviewReport`** — design-quality assessment. **Never enters `GateReport`**: it ranks candidates
  and informs the human, and a soft score that can admit is not a soft score.

```python
class ReviewFinding(BaseModel):
    model_config = ConfigDict(frozen=True)
    path: str
    line: int | None = None
    severity: Literal["blocker", "major", "minor", "nit"]
    category: Literal["correctness", "design", "readability", "test-quality", "security"]
    summary: str

class ReviewReport(BaseModel):
    model_config = ConfigDict(frozen=True)
    score: float                      # 0–1, ranks only
    findings: tuple[ReviewFinding, ...]
    judge_model: str                  # must differ from the generating model
    rubric_version: str
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

## **Memory**

Trust is a property of **content provenance**, not of the tool that emitted it. A static per-tool
trust flag is launderable: fetch a poisoned page (untrusted), summarize it, `remember` it, and it
returns from `recall` labelled trusted. Provenance travels with the record and is propagated by the
tool layer — the model does not get to declare it.

```python
class Provenance(str, Enum):
    OPERATOR = "operator"          # the human's turn — authoritative
    HARNESS  = "harness"           # tree-sitter, LSP, git — deterministic, trusted
    MODEL    = "model"             # the agent's own reasoning
    EXTERNAL = "external"          # repo content, web, MCP servers — untrusted

class MemoryRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    content: str
    kind: Literal["episode", "decision", "preference", "artifact", "note"]
    provenance: Provenance                      # required, never inferred
    source_uri: str | None = None
    links: tuple[str, ...] = ()                 # memory_ids — the knowledge net
    valid_from: datetime = Field(default_factory=utc_now)
    valid_to: datetime | None = None            # bi-temporal invalidation

class RecallQuery(BaseModel):
    text: str
    kinds: tuple[str, ...] = ()
    limit: int = 10
    as_of: datetime | None = None               # bi-temporal: recall what was believed then
    min_provenance: Provenance | None = None

class Recall(BaseModel):
    memory_id: str
    record: MemoryRecord
    score: float                                # normalized 0–1
```

Anything returning `Provenance.EXTERNAL` is wrapped in `<untrusted-data>` by the prompt assembler at
render time — not at storage time, so the label cannot be stripped by a round trip.

## **Retrieval & Graph**

```python
class RetrievalHit(BaseModel):
    path: str
    chunk: str
    score: float                   # backend-agnostic relevance, normalized 0–1
    metadata: dict[str, Any] = {}  # exempt: open-shaped backend annotations

class SymbolRef(BaseModel):
    model_config = ConfigDict(frozen=True)
    path: str
    name: str
    kind: Literal["function", "class", "method", "module", "variable"]
    line: int

class GraphEdge(BaseModel):
    model_config = ConfigDict(frozen=True)
    src: str
    dst: str
    kind: Literal["imports", "calls", "defines", "inherits", "owns", "co_changed"]
    weight: float = 1.0

class CoChange(BaseModel):
    path: str
    commits: int                   # how often it changed alongside the query path
    last_seen: datetime

class DiagnosticItem(BaseModel):
    model_config = ConfigDict(frozen=True)
    path: str
    line: int
    column: int
    severity: Literal["error", "warning", "information", "hint"]
    code: str | None = None
    message: str
    source: str                    # which server or tool produced it
```

## **Toolchain**

The port exists so gates never hardcode `pytest` and `pyright`. These are its payloads.

```python
class ToolchainInfo(BaseModel):
    model_config = ConfigDict(frozen=True)
    language: str
    test_runner: str
    type_checker: str | None = None
    linter: str | None = None
    package_manager: str | None = None

class TestReport(BaseModel):
    model_config = ConfigDict(frozen=True)
    passed: int
    failed: int
    skipped: int
    duration_s: float
    failures: tuple[str, ...] = ()   # node ids, not free text
    exit_code: int

class CoverageReport(BaseModel):
    model_config = ConfigDict(frozen=True)
    line_rate: float                 # 0–1
    branch_rate: float | None = None
    by_file: dict[str, float] = {}   # exempt: keyed by path, open-shaped
```

## **Control**

* **`Grant`** — unforgeable capability token, scoped to tool and paths, with expiry. Minted only by `PolicyEngine`.
  **It never crosses a public signature** — it is held only inside `kernel/dispatch.py`. Possession
  confers nothing; reachability is the control, and reachability is enforced by module structure plus
  `import-linter`. See [CAR Model](../02-architecture/car-model.md).
```python
class Grant(BaseModel):
    model_config = ConfigDict(frozen=True)
    grant_id: str
    tool_name: str
    scope_paths: tuple[str, ...]
    run_id: str                       # binds to one run; prevents cross-run reuse
    issued_at: datetime
    expires_at: datetime

class Decision(BaseModel):
    model_config = ConfigDict(frozen=True)
    allowed: bool
    reason: str
    requires_human: bool = False
    grant_id: str | None = None       # correlation only — the Grant itself never leaves dispatch

class RunContext(BaseModel):
    model_config = ConfigDict(frozen=True)
    run_id: str
    autonomy_level: Literal["interactive", "hybrid", "autonomous", "scheduled"]
    workspace_root: str               # opaque identifier, not a Path
    budget_remaining_usd: float

TaskStatus = Literal["submitted", "working", "input-required",
                     "auth-required", "completed", "failed", "canceled"]
```

`TaskStatus` mirrors the A2A task lifecycle so a remote pilot needs no translation layer.
