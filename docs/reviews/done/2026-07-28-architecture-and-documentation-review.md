---
status: historical
updated: 2026-07-29
---

# SAGIHA — Architecture & Documentation Review

> [!NOTE]
> **Historical record, retained for its evidence.** Every finding below has been dispositioned in the
> Remediation Status table. Line citations were accurate at review time and many are now stale — in
> particular `reference/SAGIHA Architecture Specification Blueprint.md` has been renamed to
> `reference/design-derivation.md` and its interface section deleted. Grep the quoted strings rather
> than trusting the line numbers.

**Date**: 2026-07-28
**Reviewer**: Claude Opus 5 (adversarial architecture review, requested by the maintainer)
**Scope**: Complete read of the documentation tree — 56 modular markdown files (~3,600 lines) plus two long-form reference blueprints (1,472 lines) and the benchmarking teardown. No code exists to review.
**Status**: Advisory. Nothing in this report is binding; every item carries its own evidence so it can be accepted or rejected on the merits.

---

## Remediation Status

> [!NOTE]
> **Re-verified 2026-07-29** against the tree with the commands in Appendix B. The prior tracker had
> drifted in both directions: several items marked *Deprecated* had in fact shipped, and three marked
> *Done* were only partial. Corrected below. **Done** means verified present; **Partial** means the
> item is cited with what remains; **Deferred** means intentionally out of v1 behind a trigger.

| ID | Status | Notes |
| :--- | :--- | :--- |
| D1 | ✅ Done | Grant removed from port signatures; dispatch-only pattern adopted |
| D2 | ✅ Done | ContentBlock expanded to discriminated union with ReasoningBlock, ToolUseBlock, ToolResultBlock |
| D3 | ✅ Done | stream() returns AsyncIterator[StreamEvent] with terminal UsageReported |
| D4 | ✅ Done | CodeGraph.query() replaced with domain methods (callers_of, co_changed_with) |
| D5 | ✅ Done | GateReport now includes per-criterion CriterionResult tuple |
| D6 | ✅ Done | Provenance enum added; memory trust laundering path documented and mitigated |
| D7 | ✅ Done | EventBus adopted as single source of truth for traces across all docs |
| D8 | ✅ Done | Orchestrator.execute returns AsyncIterator[Event], not TrajectoryStep |
| D9 | ✅ Done | Edit, EditRequest, HunkResult models defined; Workspace.apply_edit updated |
| D10 | ✅ Done | git split into git_read (PURE) and git_commit (DESTRUCTIVE) |
| D11 | ✅ Done | policy, governor, evaluator, worktree, code_graph added to conformance matrix |
| D12 | ✅ Done | Python version normalized to >=3.13 across all files |
| D13 | ✅ Done | Unified to >0.80 alert threshold; unsourced 95%/96% competitive claims deleted from `reference/benchmarking-existing-harnesses.md` |
| D14 | ✅ Done | Rewritten as proposed analyses; difficulty-tier table and invented targets removed |
| D15 | ✅ Done | Superseded warnings added to contradicted reference passages |
| D16 | ✅ Done | Citation artifacts stripped (incl. residual `\[cite: …\]` markers at former `:71, :72, :106`); real citations preserved |
| G1 | ✅ Done | ADR-0014: dense tier deferred behind a recall@10 trigger; `sqlite-vec` and the embedding config keys removed so the deferral is real rather than prose-only |
| G2 | ✅ Done | Toolchain port added; gates call through protocol, not pytest/pyright literals |
| G3 | ✅ Done | UserMessageReceived event and TaskSpec revision contract specified |
| G4 | ✅ Done | SubagentReport model defined |
| G5 | 🔶 Deprecated | Edit-format ablation deferred to when benchmark suite exists |
| G6 | 🟡 Proposed | ADR-0015 written with a selection rubric and candidates; **requires maintainer sign-off to move to Accepted** |
| G7 | ✅ Done | schema_version added to events table and cassette headers |
| G8 | ✅ Done | `Reviewer` port added — independent-judge design-quality **soft score, never a gate** |
| G9 | 🔶 Deprecated | Velocity/adoption milestones deferred |
| G10 | ✅ Done | Sandbox timing unified: subprocess for dev only, container for autonomous/scheduled |
| C1 | 🔶 Deprecated | Best-of-N (N>1) deferred; sequential repair is v1 |
| C2 | 🔶 Deprecated | RHI outer loop deferred; substrate (A/A, harvester, trajectory store) kept |
| C3 | 🔶 Deprecated | AOI models deferred; trajectory labels logged for future training |
| C4 | 🔶 Deprecated | Dense retrieval deferred; lexical + graph is v1. Retrieval port returns scored results for future compatibility |
| C5 | ✅ Done | Toolchain port added to hexagonal-ports.md |
| C6 | ✅ Done | Grant parameter removed from port signatures (see D1) |
| C7 | ✅ Done | ADR-0016: rootless Podman, with the egress-allowlist mechanism specified |
| C8 | 🔶 Deprecated | mypy vs ty/pyrefly advisory slot deferred |
| C9 | ✅ Done | `dev` dependency group added to `pyproject.toml` (pytest, pytest-cov, ruff, pyright, import-linter, detect-secrets); embedding provider deferred per ADR-0014; `watchfiles` and a container SDK land with their features |
| C10 | ✅ Done | Storage layout and concurrency specified in `control-plane-python.md`: three named stores under `.sagiha/` at the repo root (never inside a worktree), WAL + `busy_timeout` as a connection-factory invariant, one writer per database, parallel worktrees are readers |
| C11 | 🔶 Deprecated | 'Dumb harness' reframing deferred |
| X1 | ✅ Done | Dual source of truth removed: the blueprint's ~500-line interface section **deleted** (not synced); `03-contracts-and-models/` is now the sole normative home; [Contracts to Code](../implementation/contracts-to-code.md) specifies the day-1 move into `src/` |
| X2 | ✅ Done | Revision autobiography moved to ADR `Context` sections |
| X3 | ✅ Done | Superseded passages in `reference/` marked or removed; file renamed `design-derivation.md` and marked non-normative |
| X4 | ✅ Done | metrics-analytics doc rewritten as proposed analyses |
| X5 | ✅ Done | `pyproject.toml`, `.importlinter`, `.pre-commit-config.yaml`, `config.example.toml`, `AGENTS.md` all committed at repo root |
| X6 | ✅ Done | [`01-executive/v0.1-user-guide.md`](../01-executive/v0.1-user-guide.md) |
| X7 | ✅ Done | Mechanical consistency pass completed |

---

## How to use this document

Findings are individually addressable and stable-numbered:

| Prefix | Meaning |
| :--- | :--- |
| `D1`–`D16` | **Defects** — contradictions, self-violations, or contracts that cannot be implemented as written. Each has a file:line citation that was verified during the review. |
| `G1`–`G10` | **Gaps** — things absent that the project's stated ambition (SOTA autonomous coding harness) requires. |
| `C1`–`C11` | **Changes** — decisions I would make differently on stack and architecture. |
| `X1`–`X7` | **Documentation remediation** — changes to the docs themselves. |

Part VIII sequences all of it into an actionable plan. If you read only one section, read Part VIII.

Citations are `path:line` relative to `docs/`. Line numbers were accurate at review time; if the file has moved, grep the quoted string.

---

# Part I — Verdict

This is genuinely above-average architecture writing. The A/A noise floor, `EffectClass` replay safety, the Trusted Computing Base, the `tests_unmodified` gate, worktree materialization, and the "what worktrees do *not* isolate" table are things most teams learn by getting burned in production. The suite consistently prefers falsifiable statements over aspirations, and the ADR log with reversal conditions is a discipline most projects never adopt.

Three things are true at once, and they need to be held together:

1. **The reasoning quality is high.** The arguments against LiteLLM, against MCTS naming, against `@runtime_checkable`, against per-turn context repartitioning, and against unified code+episodic graphs are all correct and well-argued. Preserve them.

2. **The contracts do not survive contact with implementation.** The port definitions — which live in a document explicitly marked *non-normative* — violate the project's own two headline rules, cannot transport reasoning blocks, cannot report token usage while streaming, and cannot express acceptance-criteria results. These are not cosmetic. `D1`–`D5` would each cost days-to-weeks if discovered during Sprint 2 instead of now.

3. **The ratio is the finding.** ~5,000 lines of documentation, zero lines of code, and no `pyproject.toml`, `.importlinter`, `.github/workflows/ci.yml`, or `.pre-commit-config.yaml` — despite all four being written out *verbatim* in the docs. The tree is finished. Further documentation revision now has negative expected value; most remaining open questions will be answered permanently by an hour of code.

**Bottom line**: the thinking is ready. The contracts are not. The correct next commit is `src/`, preceded by a focused fix pass on `D1`–`D5`.

---

# Part II — What is strong (preserve; do not relitigate)

These are the assets. Any refactor of the documentation must carry them forward intact.

| Asset | Where | Why it holds up |
| :--- | :--- | :--- |
| **A/A noise floor before any comparison** | `04-workflows-and-loops/rhi-outer-loop.md:32-36` | The single most-skipped step in agent evaluation. Without it, "accept if the score improved" ratchets permanently on noise. Most harness work in this space is an undiagnosed random walk. |
| **`EffectClass` gating replay** | `02-architecture/microkernel-and-bus.md:27-37`, ADR-0012 | Correct and rarely specified anywhere. Time-travel debugging over a filesystem-touching agent is unsound without it. |
| **Domain-language ports + conformance suites** | ADR-0002, ADR-0003, `06-guides-and-patterns/port-conformance-testing.md` | The only mechanism that makes "swappable" falsifiable rather than aspirational. Correctly identified as a Day-0 deliverable rather than a later refinement. |
| **Native SDKs, no universal abstraction layer** | ADR-0008, `05-tech-stack/dependencies-and-versions.md:56-75` | Right call for the right reasons: cache breakpoints, reasoning-signature round-trip, and per-provider tool semantics are exactly what universal layers flatten. The `openai` `base_url` observation correctly collapses the long-tail argument. |
| **Commit-replay benchmark harvesting** | `06-guides-and-patterns/benchmark-curation.md:24-39` | Strictly better than hand-authored synthetic bugs on realism, volume, maintenance cost, and contamination resistance. |
| **Trigger conditions instead of phase numbers** | ADR-0010, `07-roadmap/phased-migration-matrix.md:26-41` | Converts a roadmap from fiction into policy. |
| **Cost per *successful* task** | `05-tech-stack/llm-providers-and-economics.md:10-18` | Correct economic objective. Optimizing cost-per-run is how a harness gets cheaper while getting worse. |
| **Hard gates vs. soft scores** | `04-workflows-and-loops/dmartic-inner-loop.md:59-67` | "Proxies may rank; only gates may admit" is the correct formulation and is applied consistently (except in `D14`). |
| **Error taxonomy with four dispositions** | `03-contracts-and-models/error-taxonomy.md` | `RETRY`/`DEGRADE`/`SURFACE`/`ABORT` with no fifth option, plus "a silent degradation is a correctness bug," is unusually rigorous. `EditRejected` as an ordinary event rather than an exception is exactly right. |
| **Worktree isolation table** | `04-workflows-and-loops/git-worktree-branching.md:21-35` | Honest about what worktrees don't isolate. The observation that this forces containers earlier is the correct conclusion. |
| **Reversal Conditions on every ADR** | `08-decisions/README.md` | Rare, and it is what separates an engineering decision from an ideological one. |
| **Observer/Interceptor split** | `02-architecture/event-bus-and-hooks.md:46-70` | "Observers cannot influence execution; interceptors may deny but never mutate" is the right invariant, and the audit-log rationale for forbidding mutation is correct. |

---

# Part III — Defects

Each entry: what is wrong, the evidence, why it matters, and a concrete fix.

---

## D1 — `Grant` is forgeable; the capability model is not enforced *[Critical]*

**Claim under test**: "an unforgeable token minted only by `PolicyEngine.authorize()`. Code holding no Grant cannot act, so authorization cannot be forgotten at a call site" (`02-architecture/car-model.md:51-53`).

**Evidence**:
- `Grant` is a plain frozen Pydantic model — `reference/SAGIHA Architecture Specification Blueprint.md:431-443`. It has no signature, no nonce, no run binding, and a public constructor.
- The import-linter `layers` contract places `sagiha.domain` at the bottom, importable by every layer — `06-guides-and-patterns/ci-and-quality-gates.md:74-83`.
- The only enforced restriction is `agency/ ↛ runtime/, adapters/` — `ci-and-quality-gates.md:32-41`.
- The RHI mutable surface explicitly includes **"non-Control adapter code"** — `04-workflows-and-loops/rhi-outer-loop.md:21`.

**Why it matters**: any module that can reach a Runtime method can also write `Grant(grant_id="x", tool_name="run_command", scope_paths=["/"], expires_at=<far future>)` and call it directly. `import-linter` stops Agency, but adapters and runtime code are unconstrained — and adapters are inside the outer loop's writable surface. So the self-improvement loop can author code that bypasses `PolicyEngine` entirely, which is the exact failure ADR-0007 exists to prevent, one level down. "Non-bypassable by construction" is currently false; it is bypassable by import.

**Fix — Option A (preferred): never pass a Grant to a caller.**

Make the dispatch choke point the sole holder. Runtime methods become module-private to the kernel; nothing outside `kernel/dispatch.py` can invoke them.

```python
# kernel/dispatch.py — the ONLY place that touches Runtime
async def dispatch(call: ToolCall, ctx: RunContext) -> ToolResult:
    decision = await policy.authorize(call, ctx)
    if not decision.allowed:
        return _denied(call, decision)
    async with governor.lease(kind=call.tool_name) as lease:
        result = await registry.dispatch(call, decision.grant)  # grant never escapes
        await policy.record_outcome(decision.grant.grant_id, result)
        return result
```

The grant parameter disappears from every public signature. Forgery becomes irrelevant because possession confers nothing — reachability is the control, and reachability is enforced by module structure plus `import-linter`.

**Fix — Option B (if the parameter must stay): sign it.**

```python
class Grant(BaseModel):
    model_config = ConfigDict(frozen=True)
    grant_id: str
    tool_name: str
    scope_paths: tuple[str, ...]
    run_id: str  # binds to one run; prevents cross-run replay
    issued_at: datetime
    expires_at: datetime
    nonce: str
    signature: str  # HMAC-SHA256 over canonical serialization
```

The signing key is generated per process, held only by `PolicyEngine`, and verified inside `ToolRegistry.dispatch` before any effect. Add a conformance test asserting that a hand-constructed `Grant` is rejected.

**Also add**: an `.importlinter` contract forbidding `sagiha.adapters` and `sagiha.agency` from importing `sagiha.runtime` directly, and a test that constructs a forged grant and asserts denial. Right now no test in the suite would catch this.

---

## D2 — `ModelProvider` cannot return reasoning blocks *[Critical]*

**Evidence**:
- `ContentBlock.kind: Literal["text", "image", "resource", "diagnostic"]` — Blueprint `:215-223`.
- `ModelProvider.stream() -> AsyncIterator[ContentBlock]`, `complete() -> tuple[list[ContentBlock], TokenUsage]` — Blueprint `:412-420`.
- `ReasoningBlock` is a **separate** model with `provider`, `opaque`, `redacted` — Blueprint `:248-258`.
- `TrajectoryStep.reasoning: list[ReasoningBlock]` — Blueprint `:274-281`.

**Why it matters**: there is no path for a `ReasoningBlock` to travel through the port. The verbatim-signature round-trip that `02-architecture/context-and-cache-engineering.md:40-42`, `prompt-architecture.md:75`, and ADR-0008 all rest on is unimplementable on this contract. Separately, there is no `tool_use` or `tool_result` block kind either — so tool calls can only cross the boundary as untyped dicts in `ModelRequest.messages: list[dict[str, Any]]` (Blueprint `:397`), which violates contract rule 1 in the same file that declares it (`:157`).

**Fix**: replace `ContentBlock` at the model boundary with a discriminated union covering everything the providers actually emit.

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
    arguments: dict[str, Any]  # validated against the registered JSON Schema


class ToolResultBlock(BaseModel):
    kind: Literal["tool_result"] = "tool_result"
    call_id: str
    content: list["ContentBlock"]
    is_error: bool = False


ContentBlock = Annotated[
    TextBlock | ReasoningBlock | ToolUseBlock | ToolResultBlock | ImageBlock | ResourceBlock,
    Field(discriminator="kind"),
]
```

`ModelRequest.messages` becomes `list[Message]` where `Message = {role, content: list[ContentBlock]}` — no raw dicts.

**Conformance test to add**: round-trip a recorded Anthropic extended-thinking response through the port and assert the `opaque` payload is byte-identical on the way back out. This is the test that keeps the cache and reasoning continuity honest.

---

## D3 — Streaming loses token accounting, breaking cost, cache metrics, and the budget *[Critical]*

**Evidence**:
- `stream()` returns no `TokenUsage`; only `complete()` does — Blueprint `:419-420`.
- `ModelCallCompleted` is specified to carry `TokenUsage` "including cache hit counts" — `02-architecture/event-bus-and-hooks.md:33`.
- `sagiha.cost_usd` is derived per `gen_ai.chat` span from reported usage — `05-tech-stack/observability-and-telemetry.md:38`.
- `ResourceGovernor` enforces `max_spend_usd_per_run` / `_per_hour` "against the same figures" — `05-tech-stack/llm-providers-and-economics.md:130`.
- `sagiha.cache.hit_ratio` is a headline alert metric with a `> 0.80` threshold — `observability-and-telemetry.md:55, 116`.

**Why it matters**: streaming is the default path for any interactive agent (the TUI, SSE remote pilots, and `ModelDelta` events all require it). If usage is unavailable on that path, then spend enforcement, cost-per-success, and the cache-hit ratio — the three numbers the entire economics argument rests on — are unmeasured in normal operation. The budget becomes exactly what `car-model.md:77` warns against: "a budget stated in a document but never enforced at a call site."

**Fix**: make the stream yield events, not content blocks, and emit usage as a terminal event.

```python
class UsageReported(BaseModel):
    kind: Literal["usage"] = "usage"
    usage: TokenUsage


StreamEvent = Annotated[
    BlockStart | BlockDelta | BlockEnd | UsageReported | StreamEnd,
    Field(discriminator="kind"),
]


class ModelProvider(Protocol):
    def stream(self, request: ModelRequest) -> AsyncIterator[StreamEvent]: ...
    async def complete(self, request: ModelRequest) -> ModelResponse: ...
```

Add a conformance test asserting every adapter emits exactly one `UsageReported` before `StreamEnd`, with `cache_read_tokens` populated where the provider supplies it. Without that test, an adapter can silently report zeros and the governor will never fire.

---

## D4 — `CodeGraph.query()` violates both headline contract rules *[High]*

**Evidence**: `async def query(self, cypher_or_sql: str, params: dict[str, Any]) -> list[dict[str, Any]]: ...` — Blueprint `:378`.

The same file states at `:156-164`:
> 1. No `Dict[str, Any]` crosses a port boundary. Every payload is a Pydantic model.
> 2. Ports speak domain language, never storage language.

`cypher_or_sql` is storage language *by name*, and the return is exactly the untyped dict the rule forbids. `03-contracts-and-models/hexagonal-ports.md:10-12` repeats both rules as normative.

**Why it matters**: this welds each adapter's query dialect into every consumer. The SQLite→Kùzu migration that ADR-0011 promises would require rewriting every call site — which is precisely the failure ADR-0002 was written to prevent, reproduced in the flagship artifact.

**Fix**: delete `query()`. The port already has the one domain method that matters (`impacted_by`). Add named domain queries as they are actually needed:

```python
class CodeGraph(Protocol):
    async def upsert_edges(self, edges: list[GraphEdge]) -> None: ...
    async def impacted_by(self, file_path: str, hops: int = 2) -> list[str]: ...
    async def callers_of(self, symbol: SymbolRef) -> list[SymbolRef]: ...
    async def co_changed_with(self, path: str, since: datetime) -> list[CoChange]: ...
```

If an escape hatch is genuinely needed for exploration, put it on the *adapter* (not the port) and forbid consumers from depending on it.

**Related, lower severity**: `ToolRegistry.register(schema: dict[str, Any])` and `ToolCall.arguments: dict[str, Any]` also carry dicts, but those are defensible — JSON Schema and tool arguments genuinely are open-shaped. Document the exemption explicitly so the rule stays credible; an unstated exception erodes a rule faster than a stated one.

---

## D5 — Acceptance criteria never reach the gate report *[High]*

**Evidence**:
- `TaskSpec.acceptance: list[AcceptanceCriterion]` where each has `description`, `check`, `required` — Blueprint `:579-595`.
- `GateReport` is five fixed booleans: `tests_pass`, `no_new_suppressions`, `tests_unmodified`, `coverage_not_decreased`, `diff_within_bounds` — Blueprint `:537-553`.
- `Evaluator.evaluate(task, branch_id) -> GateReport` — Blueprint `:598-601`.

**Why it matters**: `03-contracts-and-models/task-and-acceptance.md:8` calls the task model "the deepest missing primitive for autonomy," and the whole point of authoring criteria before execution is that the model "sees exactly what it will be graded on" (`:63`). But the grading output has nowhere to record *which criterion* passed. `tests_pass` is a single boolean that cannot represent three criteria where one is `required: false`. The benchmark task format (`06-guides-and-patterns/benchmark-curation.md:58-82`) lists three separate acceptance checks per task with no corresponding result structure.

**Fix**:

```python
class CriterionResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    description: str
    check: str
    passed: bool
    required: bool
    output: str = ""
    duration_ms: float = 0.0


class GateReport(BaseModel):
    model_config = ConfigDict(frozen=True)
    criteria: tuple[CriterionResult, ...]  # per-criterion, from TaskSpec.acceptance
    tests_unmodified: bool
    no_new_suppressions: bool
    coverage_not_decreased: bool
    diff_within_bounds: bool

    @property
    def acceptance_met(self) -> bool:
        return all(c.passed for c in self.criteria if c.required)

    @property
    def admitted(self) -> bool:
        return (
            self.acceptance_met
            and self.tests_unmodified
            and self.no_new_suppressions
            and self.coverage_not_decreased
            and self.diff_within_bounds
        )
```

This also fixes the benchmark reporting format, which currently has no way to say *which* acceptance check failed.

---

## D6 — Memory is an untrusted-data laundering path *[High]*

**Evidence**:
- `remember` and `recall` have **no Grant requirement** (Grant column is `—`) and `recall` output is marked **`trusted`** — `03-contracts-and-models/tool-catalog.md:87-88`.
- `web_fetch` / `web_search` output is marked **untrusted** and wrapped in `<untrusted-data>` envelopes — `tool-catalog.md:98-99, 111-121`.
- `MemoryRecord` has a `source_uri` field that is never used for trust computation — Blueprint `:298-304`.
- T1 names indirect prompt injection as the primary threat — `02-architecture/security-and-threat-model.md:10-20`.

**Attack path**: agent fetches a poisoned page (correctly labelled untrusted) → summarizes it → calls `remember(content, kind="decision")` with no authorization check → next run calls `recall()` → the same attacker-controlled text re-enters context **labelled trusted**, stripped of its envelope. It now persists across sessions and, since `Memory` is repo-scoped by config, potentially across repositories. The `docs/decisions/*.md` write-back path (`02-architecture/neural-symbolic-memory.md:51-53`) compounds this: poisoned content lands in a file that `prompt-architecture.md:59` injects into layer 4 of the *stable prefix*.

**Why the current mitigation doesn't cover it**: the untrusted-data envelope is applied at tool-output time based on a static per-tool flag. Trust is assigned at registration, not carried by the content. Any store-and-retrieve cycle launders it.

**Fix**: make trust a property of content provenance rather than of the tool that emitted it.

```python
class Provenance(str, Enum):
    OPERATOR = "operator"  # the human's turn — authoritative
    HARNESS = "harness"  # tree-sitter, LSP, git — deterministic, trusted
    MODEL = "model"  # the agent's own reasoning
    EXTERNAL = "external"  # repo content, web, MCP servers — untrusted


class MemoryRecord(BaseModel):
    content: str
    kind: Literal["episode", "decision", "preference", "artifact"]
    provenance: Provenance  # required, not inferred
    source_uri: str | None = None
    valid_from: datetime = Field(default_factory=utc_now)
```

Rules:
1. `remember` requires a `memory-write` grant and records provenance. Content derived from an `EXTERNAL` observation inherits `EXTERNAL` — the tool layer propagates it; the model does not get to declare it.
2. `Recall` results carry provenance, and the prompt assembler wraps anything `EXTERNAL` in `<untrusted-data>` at render time.
3. Writes to `docs/decisions/` in the target repo require `provenance in {OPERATOR, MODEL}` and go through the normal approval gate — they are out-of-worktree-durability writes and should be treated as such.

Add this to the `Memory` conformance suite: `test_external_provenance_survives_roundtrip`.

---

## D7 — Three normative docs disagree on who owns the trace *[High]*

**Evidence**:

| File | Claim |
| :--- | :--- |
| `02-architecture/microkernel-and-bus.md:13` | "the span log and the Trajectory Store are not two parallel records… **One is derived from the other**" |
| `05-tech-stack/control-plane-python.md:32` | "The Trajectory Store is **derived from the span log**" |
| `05-tech-stack/observability-and-telemetry.md:10` | "The **EventBus is the single source**. The TrajectoryStore and the OTel exporter are both subscribers. **Neither is derived from the other**" |

All three are marked normative. `implementation/development-plan-and-prompts.md:73` instructs the implementer to "derive the trajectory view from them rather than storing both" — i.e. it encodes the *wrong* one.

**Fix**: `observability-and-telemetry.md` is architecturally correct — the EventBus is the source, both are subscribers, and deriving a durable audit log from a sampled telemetry pipeline is a bad idea (`sample_rate` exists in config at `configuration-reference.md:116`, and a sampled trajectory is a corrupt trajectory). Adopt that version, correct the other two, and fix the Sprint 2 prompt.

---

## D8 — `Orchestrator.execute` has two different signatures *[High]*

**Evidence**:
- `async def execute(task: TaskSpec, context: RunContext) -> AsyncIterator[Event]` — `02-architecture/entry-points-and-piloting.md:11-15`.
- `async def execute(self, task: TaskSpec, context: RunContext) -> AsyncIterator[TrajectoryStep]` — Blueprint `:575-576`.

**Why it matters**: this is *the* headline boundary. The entire "one core, many cockpits — adding a channel requires zero core changes" claim (`entry-points-and-piloting.md:27`) depends on the return type being the event stream that the TUI, SSE streamer, TTS narrator, and hooks all subscribe to. `TrajectoryStep` is a coarser, persistence-shaped type that cannot carry `ApprovalRequested`, `ModelDelta`, `GateEvaluated`, or `BudgetWarning`.

**Fix**: `AsyncIterator[Event]` wins. `TrajectoryStep` is what the `TrajectoryStore` observer *builds* from events; it is not the streaming unit.

---

## D9 — Edit contract mismatch, and the `Edit` model is never defined *[High]*

**Evidence**:
- Tool: `edit_file(path, edits: Edit[]) -> EditResult`, described as "a list of anchored search/replace edits" — `03-contracts-and-models/tool-catalog.md:55, 58`.
- Port: `async def apply_edit(self, diff_text: str, grant: Grant) -> EditResult` — Blueprint `:506`.
- `Edit` appears in **no** schema definition anywhere in the tree. `domain-schemas.md` defines `EditResult` but not its input.

**Why it matters**: the docs correctly identify this as the highest-impact empirical choice in a coding harness (Blueprint `:372`, "settled by measurement, not assumption") and dashboard `sagiha.edit.hunk_failure_ratio` as a top-tier quality signal (`observability-and-telemetry.md:59`). Then the input type is undefined and the two specified forms are incompatible. Nothing in the tree specifies anchor-matching semantics, whitespace normalization, fuzzy-match fallback, or what happens when an anchor matches twice.

**Fix**: define the model, pick search/replace as the default, and make the format measurable.

```python
class Edit(BaseModel):
    model_config = ConfigDict(frozen=True)
    old_string: str  # unique anchor; empty == insert at start
    new_string: str
    expected_occurrences: int = 1  # explicit; ambiguity is an error, not a guess


class EditRequest(BaseModel):
    path: str
    edits: tuple[Edit, ...]


class HunkResult(BaseModel):
    applied: bool
    index: int
    reason: (
        Literal["ok", "anchor_not_found", "ambiguous_anchor", "skipped_after_failure", "syntax_invalid"]
        | None
    ) = None
    nearest_match: str | None = None  # what the model should have written
```

`Workspace.apply_edit(request: EditRequest, ...) -> EditResult`. Reserve unified-diff application for a separate `apply_patch` method if it is ever needed.

**And schedule the measurement.** The docs say the format choice is empirical; add it to the S0 benchmark as an explicit ablation (search/replace vs. whole-file rewrite) so the claim is settled with a number rather than left permanently open.

---

## D10 — `EffectClass` is per-tool, but `git` needs it per-operation *[Medium]*

**Evidence**:
- Registration takes exactly one effect per tool name: `registry.register(name=..., schema=..., effect=EffectClass.DESTRUCTIVE, ...)` — `tool-catalog.md:126-132`; Blueprint `:522`.
- The catalog lists `git` with effect "**P for read ops, D for `commit`**" — `tool-catalog.md:79`.

**Why it matters**: replay dispatches on `EffectClass`. Registered as `PURE`, replay re-executes `git commit`. Registered as `DESTRUCTIVE`, `git status` and `git diff` can never be re-executed and every replay must serve them from cassettes — which makes `sagiha replay --verify-all` (`ci-and-quality-gates.md:118-124`) strictly weaker.

**Fix (cheapest)**: split into `git_read` (ops: `status`, `diff`, `log`, `show`, `blame`; `PURE`) and `git_commit` (`DESTRUCTIVE`). Two tools, still well inside the 20-tool budget, and the `op`-enum consolidation argument is preserved for the read side where it actually applies.

**Fix (more general)**: allow the registry to take `effect: EffectClass | Callable[[ToolCall], EffectClass]`. Adds flexibility, but also adds a code path that replay correctness depends on — the split is safer.

Note the same issue applies to `run_command` (registered `DESTRUCTIVE`), which is correct but means `ls`, `cat`, and `pytest --collect-only` are never re-executed in replay. Acceptable — but state it, because it affects what replay actually proves.

---

## D11 — `PolicyEngine` and `Evaluator` have no conformance suite *[Medium]*

**Evidence**:
- CI matrix: `port: [model, memory, indexer, workspace, lsp, tool_registry, trajectory]` — `06-guides-and-patterns/ci-and-quality-gates.md:108-111`.
- The port index lists ~20 ports — `03-contracts-and-models/hexagonal-ports.md:18-54`.
- Coverage requirement is "≥ 95% on `sagiha/kernel/policy`" — `ci-and-quality-gates.md:128`.

**Missing from the matrix**: `PolicyEngine`, `ResourceGovernor`, `Evaluator`, `CodeGraph`, `EmbeddingProvider`, `WorktreeManager`, `Orchestrator`, `CandidateSearch`, `ShortTermMemory`, `MetaImprover`, and all three AOI ports.

**Why it matters**: `PolicyEngine` and `Evaluator` are the two TCB components. `port-conformance-testing.md:81` calls the conformance suites "the architecture's load-bearing guarantees, checked mechanically" — and the two components whose failure is a security incident are the ones not mechanically checked. Line coverage at 95% measures that policy code *ran*, not that it *denied the right things*.

**Fix**: add `policy`, `governor`, `evaluator`, `worktree`, and `code_graph` to the matrix, and write the behavioral tests that matter most:

```python
# tests/contracts/test_policy_conformance.py
async def test_denies_write_outside_worktree_at_every_autonomy_level(policy): ...
async def test_forged_grant_is_rejected_at_dispatch(policy, registry): ...  # covers D1
async def test_expired_grant_is_rejected(policy): ...
async def test_grant_scope_is_path_bounded_not_prefix_matched(policy): ...  # ../ escapes
async def test_always_gate_list_cannot_be_bypassed_by_autonomy_level(policy): ...


# tests/contracts/test_evaluator_conformance.py
async def test_candidate_modification_of_tests_fails_the_gate(evaluator): ...
async def test_evaluator_uses_injected_suite_not_worktree_copy(evaluator): ...
async def test_evaluator_has_no_degraded_mode(evaluator): ...  # per error-taxonomy:90
```

---

## D12 — Python version drift, 5 sites *[Medium]*

ADR-0009 and `dependencies-and-versions.md:12, 36` pin `>=3.13`. These say 3.12+:

| File | Line |
| :--- | :--- |
| `02-architecture/microkernel-and-bus.md` | 7 |
| `05-tech-stack/control-plane-python.md` | 8 |
| `06-guides-and-patterns/getting-started.md` | 8 (stated as a user-facing prerequisite) |
| `reference/SAGIHA Conceptual Design.md` | 149 |
| `reference/SAGIHA Architecture Specification Blueprint.md` | 149, 154 |
| `reference/benchmarking-existing-harnesses.md` | 80 |

Fix: global replace to `>=3.13`. The quickstart one matters most — it tells users to install the wrong runtime.

---

## D13 — Cache-hit target stated three incompatible ways *[Medium]*

| Value | Where | Role |
| :--- | :--- | :--- |
| `> 0.80` | `observability-and-telemetry.md:116`; `llm-providers-and-economics.md:132` | Alert threshold |
| `≥ 95%` | `06-guides-and-patterns/metrics-analytics-and-self-improvement.md:33` | **Conformance gate** for `ModelProvider` |
| `95%+` | `reference/benchmarking-existing-harnesses.md:85` | Competitive claim |
| `96%+` | `reference/benchmarking-existing-harnesses.md:22` | Attributed to Claude Code |

**Why it matters**: a conformance test asserting ≥95% will fail against a correct implementation on a short run, and it is not a *contract* property anyway — cache hit rate is a function of workload, not of adapter conformance. The 95%/96% competitive figures are unsourced and shouldn't appear in a document tree that elsewhere refuses to tabulate numbers it hasn't measured (`llm-providers-and-economics.md:34`).

**Fix**: single value, `> 0.80`, as an alert threshold only. Remove it from the conformance table entirely. Delete or source the 95%/96% claims.

---

## D14 — `metrics-analytics-and-self-improvement.md` is an unrevised earlier draft *[High]*

This file is materially off-posture from the rest of the suite and contradicts its most-repeated principles.

| Line | Problem |
| :--- | :--- |
| `:96-101` | A "Task Complexity Difficulty Scale" asserting **100% / 95% / 80–88% / <15%** feasibility by tier. These are invented, unfalsifiable capability claims — exactly what `README.md:14` forbids ("stated as benchmarks with thresholds, not as unfalsifiable end-states") and what `llm-providers-and-economics.md:34` explicitly refuses to do ("a stale table in a normative document is worse than none — it gets trusted"). |
| `:23` | "assigned a hard score of **`0.0`** (admissions failure)" for test modification. The gates-are-not-scores distinction is the suite's single most repeated principle (`dmartic-inner-loop.md:59-67`, `security-and-threat-model.md:34`: "a hard gate failure, **not a scored penalty**"). |
| `:33` | Prompt cache hit ratio ≥95% as a conformance metric — see D13. |
| `:35` | "Diagnostic Latency (<100ms)" — invented, uncalibrated, and in tension with the 30s+ cold-start reality documented at `lsp-interface.md:28`. |
| `:21` | Holdout path `/benchmarks/holdout/` vs `benchmarks/definitions/` everywhere else (`benchmark-curation.md:100`). |
| `:13` | "From Sprint 3 onward, SAGIHA is used to build its own future modules" — but Sprint 3 *is* the sandbox sprint, and the TCB CI protections don't land until Sprint 5. Self-hosting is scheduled before the mechanisms that make it safe. |
| `:44-54` | LaTeX `$$` blocks, stylistically inconsistent with the rest of the tree. |

**Fix**: rewrite or delete. If you keep the useful parts — the failure-taxonomy clustering (`:56-61`) and the locality ratio (`:52-54`) are genuinely good ideas — move them into `06-guides-and-patterns/` as clearly-labelled *proposed* analyses with no numeric targets attached. The difficulty-tier table in particular is the one thing in this tree a skeptical reader will screenshot; it undercuts the credibility the other 55 files worked to build.

---

## D15 — Reference blueprints contain un-revised passages that reverse accepted ADRs *[High]*

`README.md:57-58` designates `reference/` as "long-form derivation and rationale," but these passages are written in the present indicative and describe the system as shipped:

| Passage | Contradicts |
| :--- | :--- |
| "SAGIHA unifies four distinct structural topologies into a single property graph deployed on **Neo4j or FalkorDB**" — Blueprint `:34` | ADR-0011, `neural-symbolic-memory.md:24` ("a Neo4j daemon would break the local-first principle"), `dependencies-and-versions.md:95` |
| "the harness utilizes **tqdb** memory-mapped quantization storage" — Blueprint `:72`. tqdb is **pure Go**, per the table at `:69` | ADR-0010 (Go vector sidecar **dropped**), `performance-sidecars.md:36-38`, and the quantization deferral at `indexing-and-retrieval.md:32` |
| "SAGIHA implements a hybrid retrieval engine combining… dense **TurboQuant-compressed** vectors" — Blueprint `:72` | The entire "quantization solves a problem this system does not have" argument |
| "SAGIHA utilizes high-performance **gRPC** over Unix domain sockets with shared memory buffers" — Blueprint `:815` | ADR-0010, plus three separate docs saying prefer msgpack/JSON-RPC over UDS and defer gRPC (`performance-sidecars.md:53`, `protocols-mcp-a2a.md:32`, `sidecar-development.md:33`) — and Blueprint `:904` in the *same file* lists gRPC as deferred |
| "**Plugins** — full adapters that can **register new Ports** or replace existing ones **at runtime**… **Discovery is automatic** via the Plugin Discovery component already present in the Kernel" — `Conceptual Design.md:329-332` | ADR-0004, `control-plane-python.md:14-22`, and `event-bus-and-hooks.md:122` ("None of the three may register new ports") |

**Why it matters**: the maintainer of this codebase is stated to be an LLM navigating the tree. An agent doing retrieval over `docs/` will surface these passages with no signal that they are superseded. "Rationale, not normative" is a distinction that survives a careful human reader and does not survive a vector search.

**Fix**: for each contradicted section, either delete it or prepend an explicit block:

```markdown
> [!WARNING]
> **Superseded by [ADR-0010](../08-decisions/0010-defer-exotic-components.md).**
> The passage below describes an approach that was evaluated and rejected. Retained for
> the reasoning only. Do not implement.
```

---

## D16 — Citation artifacts throughout the blueprint *[Low]*

Leftover research-report markers: `Neo4j or FalkorDB4` (`:34`), `SQ8 achieves 4x memory compression8` (`:43`), `\[cite: 9, 10\]` (`:67`), `HTTP-SSE17` (`:814`), and a `Referências citadas` section in Portuguese (`:914`) listing 22 URLs including Reddit threads and a Product Hunt page (`:916-918`) that support nothing in the text.

**Fix**: strip the inline markers, keep the ~8 citations that support real technical claims (the Graphiti, TurboQuant, Qdrant, and A2A references), delete the rest, and translate the heading.

---

# Part IV — Gaps

Things absent that the "SOTA autonomous coding harness" claim requires.

## G1 — No embedding provider anywhere in the dependency set

`sqlite-vec>=0.1` is pinned as the "dense retrieval tier, Day 0" (`dependencies-and-versions.md:46`) and `configuration-reference.md:81-82` has `embedding_model` and `embedding_dims = 1024`. **Nothing generates the vectors.** There is an `EmbeddingProvider` port with no adapter and no dependency behind it.

Both resolutions carry real cost that no budget in the tree accounts for:
- **Local** (`sentence-transformers`, `fastembed`, ONNX): pulls torch or onnxruntime — hundreds of MB, GPU/CPU contention with the agent's own workload, and a large addition to an otherwise lean dependency list.
- **API** (`voyage-code-3`, OpenAI embeddings): per-index cost and network latency on every re-index, and it breaks the local-first / air-gapped operation that `llm-providers-and-economics.md:48-55` promises.

This blocks Sprint 4 on day one. Decide now, and record it as an ADR.

## G2 — Python-only stack against a multi-language ambition

- Gates hardcode `pytest` and `pyright` (`configuration-reference.md:102-107`, `ci-and-quality-gates.md:10-20`).
- `run_tests(selector?, pristine=true) -> TestReport` has no ecosystem abstraction (`tool-catalog.md:67`).
- `coverage_not_decreased` assumes a Python coverage tool.
- There is **no `TestRunner` or `Toolchain` port** in the 20-port index.

Yet `tree-sitter-language-pack` is pinned for multi-language parsing, Multi-SWE-bench is named as the preferred public suite (`running-benchmarks.md:33`), and the roadmap promises "more languages — *per language actually used*" (`phased-migration-matrix.md:38`).

A harness whose differentiator is a first-class diagnostic gate, that can only gate Python, is not SOTA in 2026. **Add a `Toolchain` port** (`detect`, `install`, `test`, `typecheck`, `lint`, `coverage`) with a Python adapter first, and express gates against it.

## G3 — No mid-run steering

The entry point is `TaskSpec` in, events out. `ApprovalRequested`/`ApprovalResolved` is the only human→agent channel. There is no contract for *"the user amends the goal at step 40."*

This is the dominant interaction mode in every harness you're competing with, and it has direct architectural consequences: a new operator turn appends to the tail (fine for cache) but may invalidate the `TaskSpec`, the active plan, and the retrieval set (not fine). Specify it now — retrofitting an input channel into a one-shot pipeline is expensive.

Minimum: a `UserMessageReceived` event, a rule for how it amends `TaskSpec` (new revision, not mutation — `TaskSpec` is frozen), and a statement of what it does to cached layers.

## G4 — Sub-agent results have no re-entry contract

`spawn_subagent(task, budget) -> AsyncIterator[Event]` (`tool-catalog.md:107`). `prompt-architecture.md:85` correctly says the child does not inherit the parent's tail. But nothing specifies **what comes back**: a summary? the diff? the child's `GateReport`? In what shape does it enter the parent's context, and at which prompt layer?

This is precisely where delegation architectures fail in practice — the child does good work and the parent can't use it. Specify a `SubagentReport` model (goal, outcome, diff summary, artifacts, cost, gate result) and state which prompt layer it lands in.

## G5 — Edit application is named the top variable, then left unspecified

Covered structurally in D9. The gap beyond the type mismatch: the docs say the edit-format choice "is settled by measurement, not assumption" (Blueprint `:372`) and dashboard `edit.hunk_failure_ratio` with a `< 0.15` target (`observability-and-telemetry.md:119`) — but there is **no measurement plan**, no ablation in the benchmark suite, and no decision procedure that turns the metric into a choice. Add the ablation to the S0 suite.

## G6 — Benchmark chicken-and-egg is unacknowledged

`README.md:105` calls the pinned 30-task S0 suite "the one artifact remaining to be curated," and `benchmark-curation.md:8` says it "must be harvested from a real repository." But:

- Commit-replay harvesting requires a repo with history **and** tests **and** a base commit to revert against.
- SAGIHA has no code, so it cannot harvest from itself at S0.
- Therefore an **unnamed external repository is a hard dependency of your first gate**, and its characteristics (language, test framework, size, flakiness) will silently determine what "≥70% resolved" means.

Name the repo now. Its properties should be an explicit, recorded decision, because every number the project ever reports is relative to it.

## G7 — No trajectory schema versioning or migration path

The `events` table (`observability-and-telemetry.md:83-96`) stores `payload TEXT` — serialized event models. The store is append-only, is the source of truth for replay/audit/RHI training, and is expected to outlive months of harness change. `sagiha replay --verify-all` asserts byte-for-byte step-sequence equality against recorded cassettes (`ci-and-quality-gates.md:118-124`).

The first change to any event model orphans every cassette and fails CI with no migration path. Add `schema_version` to the events table and to cassettes, plus a documented upgrade policy (replay compatibility window, migration script, or explicit re-record).

## G8 — Nothing measures whether the code is *good*

Every hard gate rewards "tests pass, nothing regressed, diff bounded." The docs are admirably honest that soft scores are gameable — but the consequence is a harness that optimizes for green with **no design-quality signal at all**. The soft score is "PRM value from diagnostic deltas, efficiency, coverage gain," all of which are also mechanical.

"Senior software engineer" is exactly the part not being evaluated. `llm-providers-and-economics.md:106` reserves a row for an LLM judge ("Frontier, and never the model that generated the candidate") and that is the right instinct — but there is no rubric, no port, and no place in `GateReport` for its output. Either add a review-quality dimension (as a soft score with an independent judge, never a gate), or drop "senior" from the positioning.

## G9 — No velocity or staffing assumption anywhere

Five sprints spanning: ports + conformance → kernel + replay + MCP → worktrees + container sandbox + LSP supervisor → AST chunking + hybrid retrieval + code graph + cache-aware context → best-of-N + gates + harvester + AOI + Meta-Improver.

For a small team this is 12–18 months, not five sprints. Separately, **S0's deliverable ("agent resolves a failing test in one file") is far below the threshold at which anyone would choose this over an existing tool** — so there is no adoption milestone anywhere in the plan, and no point at which the project gets external feedback. Add one: the first version a real user would pick, and why.

## G10 — Sandbox timing contradicts itself in three places

| Source | Claim |
| :--- | :--- |
| `phased-migration-matrix.md:39` | Sandbox **Day 0** = "Local subprocess + worktree"; container at Day 1 |
| ADR-0006 | Container "required from slice **S1**" |
| `getting-started.md:8` | Container runtime is a hard **prerequisite**, "an agent with shell access runs inside one **from the first slice**" |

`configuration-reference.md:148` resolves it partially (subprocess "permitted for local development only; refused when autonomy is `autonomous` or `scheduled`") — adopt that as the single answer and correct the other three.

---

# Part V — Decisions I would make differently

## C1 — Cut best-of-N (S3) from v1; ship sequential repair only

System 2 is, by the project's own analysis, the most expensive machinery in the system: N parallel worktrees × N containers × N LSP server sets × N full test runs per task. `performance-sidecars.md:46` flags "server explosion under parallel search" as a direct and unaddressed consequence.

By ADR-0010's own test — *is this an advanced component that should sit behind a measured trigger?* — best-of-N qualifies, and it is the one exotic component that got exempted. **Sequential repair against a strong verifier captures most of the value at 1/N the cost**, and the docs already say repair has better yield per dollar than widening N (`glossary.md:36`).

Ship N=1 + repair. Add N behind a trigger: *"single-candidate repair plateaus below the S0 target on multi-file tasks."*

## C2 — Cut the RHI outer loop (S4) from v1; keep its substrate

The statistical discipline around RHI is the best content in the tree. The loop itself, at "thousands of dollars per iteration" (`rhi-outer-loop.md:59`), is not affordable for this project's apparent scale.

Apply the doc's own test to itself: *"An outer loop that cannot pay for itself is a research project, not a feature."*

**Keep**: A/A noise floor, commit-replay harvester, paired statistics with multiple-comparison correction, trajectory store, `degradations = 0` validity precondition. These are independently valuable and are the actual moat (see Part VII). **Defer**: MetaImprover, AOI models, PRM, automated mutation proposal.

## C3 — Delete `aoi/` from v1 entirely

Three model families, four ports, offline + online training pipelines, feature extraction, model registry — across two documents. Trained "exclusively on data generated by SAGIHA itself" (`Conceptual Design.md:457`), which on day one is zero rows.

The cold-start analysis is correct (`aoi-coprocessors.md:46-48`): the deterministic ladder generates the labels. So **ship the ladder and log the labels**, and revisit AOI when there are thousands of trajectories. Everything written about calibration, shadow mode, exploration fractions, and censored outcomes is worth keeping — as a design note for when the data exists.

## C4 — Ship lexical + graph retrieval only in S2; gate the dense tier

`indexing-and-retrieval.md:22` states that for code, exact-symbol lexical matching is "the single strongest signal and is **never demoted below dense retrieval**." Combine that with G1 (no embedding provider exists) and the cost of adding one, and the sequencing is clear:

**S2 = AST-bounded chunking + BM25/FTS5 + code-graph expansion.** Measure recall@10. Add the dense tier only if the lexical+graph baseline misses target — which is exactly the trigger-condition discipline ADR-0010 applies everywhere else.

This removes the heaviest new dependency from the critical path and makes S2 shippable in a fraction of the time.

## C5 — Add a `Toolchain` port before writing any gate

Per G2. Gates should be expressed against `Toolchain.test()` / `.typecheck()` / `.coverage()`, not against `pytest` and `pyright` literals. Python adapter first; the port costs almost nothing to add now and is very expensive to retrofit after gates, benchmarks, and the Evaluator all hardcode Python.

## C6 — Grants: remove the parameter rather than sign it

Per D1 Option A. `Workspace.write(path, content, grant)` looks like enforcement and isn't. Making dispatch the sole caller of Runtime is simpler, faster, and actually enforced by module structure — and it removes a parameter from the highest-traffic signatures in the system.

## C7 — Pin the container mechanism now, and write the egress allowlist

`sandbox.runtime = "container"` and `egress_allowlist = [...]` (`configuration-reference.md:64-67`) are one line each in config and roughly a week of work in reality: rootless Podman vs. Docker socket access, per-branch volumes, DNS-level vs. iptables-level allowlisting, and how an allowlist of *hostnames* is enforced at a network namespace when the traffic is TLS to an IP.

This is an S1 hard gate ("no credential reachable inside the sandbox") with no implementation detail behind it. Decide and write an ADR: Podman rootless is the likely right answer for local-first.

## C8 — Type checkers: keep pyright blocking, swap the advisory slot

The rationale for pyright as canonical is genuinely good (`dependencies-and-versions.md:25`: same engine the agent consumes through `LSPAdapter`, so self-check and agent-visible diagnostics can never disagree). Keep it.

For the advisory second opinion, `ty` or `pyrefly` are the stronger 2026 choices — dramatically faster, so they can run on every keystroke-adjacent loop rather than only in CI. mypy's variance/overload coverage is real but is the weaker half of the pair given the cost.

## C9 — Dependencies missing from a list that claims zero open questions

`dependencies-and-versions.md:6` says "Sprint 1 should open zero of these questions." These are open:

| Missing | Needed for |
| :--- | :--- |
| An embedding provider | Dense retrieval, Day 0 (G1) |
| A container SDK / CLI contract | S1 sandbox — the hard gate |
| `pytest-cov` | `coverage_not_decreased` gate |
| `watchfiles` | "File-watch driven, per-file re-index" (`indexing-and-retrieval.md:41`) |
| `detect-secrets` | Referenced in pre-commit (`ci-and-quality-gates.md:148`) |
| `import-linter`, `pyright`, `ruff`, `mypy` | Named in the toolchain table but absent from any dependency group |
| **A dev-dependency group at all** | There is none in the `pyproject.toml` block |

## C10 — Reconsider the `sqlite-vec` → LanceDB → quantization ladder

Three storage layers are specified for a tier that C4 defers. When the dense tier does arrive, `sqlite-vec` alongside an already-present SQLite trajectory store and SQLite code graph is the right *first* answer — but note that three logically distinct SQLite databases with different write patterns (append-only events, rebuildable graph cache, vector index) under WAL and parallel worktrees is a concurrency design that no doc addresses. Specify one writer per database and where each file lives.

## C11 — Reframe the "dumb harness" thesis

`vision-and-philosophy.md:7`: "The harness stays deliberately dumb; the models stay in charge."

This is not quite true, and the docs know it: the harness encodes real intelligence in retrieval ranking, escalation thresholds, compaction policy, chunk boundaries, and gate design. The proof is that the RHI mutable surface is *exactly that list* (`rhi-outer-loop.md:21`).

Restate as: **"No model-shaped intelligence in the harness."** The harness owns policy, structure, and verification; it never owns reasoning, planning, or code generation. That version is defensible, is what the architecture actually does, and is stronger than claiming a dumbness the design contradicts.

---

# Part VI — Documentation remediation

## X1 — Move port and schema definitions out of prose and into code

**The single highest-leverage change in this report.**

`README.md:57-58` designates `01`–`07` as normative and `reference/` as rationale. But `hexagonal-ports.md:6` and `domain-schemas.md:6` both say "full signatures/definitions live in the Architecture Specification Blueprint" — making the explicitly **non-normative** document the only place the actual contracts exist. Every one of D1, D2, D4, D5, D8, D9 lives there.

A `Protocol` is code, not prose. Move them:

```
src/sagiha/ports/*.py       # the Protocols — normative, type-checked, LSP-navigable
src/sagiha/domain/*.py      # the Pydantic models — normative, validated
docs/03-contracts-and-models/*.md   # the *rules* and rationale, linking to the code
```

This makes the contracts type-checkable on day one, kills an entire class of drift, and gives the LLM maintainer real "go to definition" — which the tree argues is a first-class architectural requirement (ADR-0004). It also converts the review of D1–D9 from a documentation edit into a compile-checked change.

## X2 — Move the revision autobiography into ADR Context sections

**44 occurrences** of "the previous revision / the prior specification / earlier drafts / was withdrawn" across **15 of 56 files** — verified by grep. Nearly every normative module spends its best paragraphs arguing against a document that no longer exists and that no reader will ever see.

`executive-summary.md:29` is an entire section titled "What This Revision Corrected." `hexagonal-ports.md:56-69` has two tables devoted to it. `context-and-cache-engineering.md:8` opens by withdrawing a scheme from a document nobody has.

This is context debt. Every token of it is loaded by the agent that reads this tree, and it will be stale the moment code exists.

**Fix**: the ADRs already have exactly the right shape — a `Context` section for "what forced this decision." Move it all there. Normative modules state the contract; ADRs carry the history. Conservatively this removes ~20–25% of the tree's token count with zero information loss.

## X3 — Neutralize the superseded passages in `reference/`

Per D15. Either delete them or add the `> [!WARNING] Superseded by ADR-XXXX` block. A "this is rationale not spec" note in the README does not survive retrieval, and retrieval is how this tree will actually be read.

## X4 — Rewrite or delete `metrics-analytics-and-self-improvement.md`

Per D14. Salvage the failure-taxonomy clustering and locality ratio into a clearly-marked *proposed analyses* doc with no numeric targets. Delete the difficulty-tier table.

## X5 — Commit the files the docs already contain

These are written out verbatim in the documentation and absent from the repository:

| File | Source |
| :--- | :--- |
| `pyproject.toml` | `05-tech-stack/dependencies-and-versions.md:34-63` |
| `.importlinter` | `06-guides-and-patterns/ci-and-quality-gates.md:28-83` |
| `.github/workflows/ci.yml` | `ci-and-quality-gates.md:91-111, 158-162` |
| `.pre-commit-config.yaml` | `ci-and-quality-gates.md:134-150` |
| `config.example.toml` | `05-tech-stack/configuration-reference.md:12-137` |

Also add a root `AGENTS.md` — the project builds a harness that reads one, and dogfooding starts with having one.

Zero design cost. It converts a specification into a project.

## X6 — Add a "v0.1 for a real user" page

The roadmap's terminal state is a benchmark score. There is no point at which someone outside the project would choose to use this. Add one page: what the first genuinely-useful version does, who would use it, and what it does better than the alternative they're using today. This is what turns the sequencing decisions in Part V from arbitrary into justified.

## X7 — Fix the cross-cutting inconsistencies as a single pass

D7 (trace ownership), D8 (`Orchestrator.execute`), D12 (Python version × 6), D13 (cache target × 4), G10 (sandbox timing × 3). All mechanical, all cheap, all currently capable of sending an implementer down the wrong path.

---

# Part VII — Strategic position

## The claimed differentiators are thin

`README`/positioning claims the edge over Claude Code / Aider / OpenHands is: a first-class LSP diagnostic gate, best-of-N over parallel worktrees, pristine read-only test gates, and zero provider lock-in.

| Claim | Honest assessment |
| :--- | :--- |
| First-class LSP diagnostic gate | **Real, but narrow.** And Python-only as specified (G2). It is a good feature, not a moat. |
| Best-of-N across worktrees | Worktree parallelism ships in competing harnesses today. Also the most expensive machinery you have (C1). |
| Pristine read-only test gates | **Genuinely good and underrated** — but it is a property of an *evaluation* system, not a coding system. See below. |
| Zero provider lock-in | A weekend of adapter work. Not defensible. |

## Where the actual moat is

**The measurement layer.** Record/replay determinism + A/A noise floor + commit-replay harvesting + paired statistics with multiple-comparison correction + `degradations = 0` and `tests_unmodified = 0` as *validity preconditions rather than scores*.

Almost nobody in this space does this rigorously. It is the only asset in the tree that makes every other claim provable, and it is the part of the design that is clearly ahead of the field rather than level with it.

## The strategic recommendation

**Build the evaluation harness first, and build it as a standalone that can grade other harnesses — not only SAGIHA.**

| Why | Detail |
| :--- | :--- |
| It is weeks, not quarters | Commit-replay harvester + task runner + A/A + paired stats + reporting. No sandbox, no LSP pool, no candidate search, no embeddings required. |
| It produces the S0 suite as a byproduct | Closes G6 directly — the chicken-and-egg dissolves because the harvester *is* the first deliverable. |
| It is independently useful | "Grade any coding agent on your own repository's real commit history, with a measured noise floor" is a product on its own, and one nobody ships well today. |
| It gets external feedback early | Closes G9. Someone can use it before SAGIHA can resolve a single task. |
| It makes the rest credible | Every subsequent architectural claim becomes a number instead of an argument. That is the difference between a design doc and a SOTA project. |

Then build the harness that wins on your own benchmark — with the sequencing from Part V (sequential repair before best-of-N, lexical before dense, no AOI, no RHI in v1).

---

# Part VIII — Prioritized action plan

## Tier 0 — Before writing any implementation code (days)

| # | Action | Refs |
| :--- | :--- | :--- |
| 1 | Move ports and domain models into `src/sagiha/ports/` and `src/sagiha/domain/` as real, type-checked Python. Fix D1–D5, D9, D10 **as code**, not as prose. | X1, D1–D5, D9, D10 |
| 2 | Commit `pyproject.toml`, `.importlinter`, `ci.yml`, `.pre-commit-config.yaml`, `config.example.toml`, `AGENTS.md` — all already written in the docs. | X5 |
| 3 | Run the mechanical consistency pass: trace ownership, `Orchestrator.execute`, Python version, cache target, sandbox timing. | X7, D7, D8, D12, D13, G10 |
| 4 | Decide and record as ADRs: embedding provider (or defer per C4), container runtime, target benchmark repository. | G1, C7, G6 |
| 5 | Add `policy`, `governor`, `evaluator`, `worktree`, `code_graph` to the conformance matrix and write the forged-grant and grader-editing tests first. | D11 |

## Tier 1 — Documentation hygiene (days, parallelizable)

| # | Action | Refs |
| :--- | :--- | :--- |
| 6 | Move the revision autobiography into ADR Context sections; strip it from the 15 affected modules. | X2 |
| 7 | Add superseding warnings to (or delete) the contradicted passages in `reference/`. | X3, D15 |
| 8 | Rewrite or delete `metrics-analytics-and-self-improvement.md`. | X4, D14 |
| 9 | Strip citation artifacts from the blueprint. | D16 |
| 10 | Write the "v0.1 for a real user" page. | X6, G9 |

## Tier 2 — Specify before you need it (days)

| # | Action | Refs |
| :--- | :--- | :--- |
| 11 | Add the `Toolchain` port before any gate hardcodes pytest/pyright. | C5, G2 |
| 12 | Specify the trust-provenance model for memory. | D6 |
| 13 | Specify mid-run steering and the sub-agent result contract. | G3, G4 |
| 14 | Add `schema_version` to events and cassettes plus an upgrade policy. | G7 |
| 15 | Add the edit-format ablation to the S0 benchmark design. | G5, D9 |

## Tier 3 — Revised build sequence

Replacing the current S0–S4:

| Slice | Deliverable | Rationale |
| :--- | :--- | :--- |
| **E0** | **Evaluation harness, standalone.** Commit-replay harvester, task runner, A/A noise floor, paired stats, reporting. Grades any agent, not just SAGIHA. | Part VII. Produces the S0 suite, closes G6, ships in weeks, independently useful. |
| **S0** | Agent resolves a failing test in one file — verified, logged, replayable. `ModelProvider` + cassettes, dispatch choke point, `PolicyEngine`, trajectory store, structured edits, commit-per-step. | Unchanged. Graded by E0 from day one. |
| **S1** | Materialized worktree inside a container, grants enforced, warm LSP supervisor. | Unchanged, with the container mechanism decided up front (C7). |
| **S2** | AST chunking + BM25/FTS5 + code-graph expansion. **Dense tier deferred behind a recall@10 trigger.** | C4. Removes the embedding dependency from the critical path. |
| **S3** | **Sequential repair only.** Hard gates, pristine injection, escalation ladder. Best-of-N deferred behind a plateau trigger. | C1. |
| **—** | AOI, MetaImprover, RHI: **out of v1.** Keep the ladder's label logging so the data accrues. | C2, C3. |

---

# Appendix A — Repository state at review time

```
docs/
├── 01-executive/          3 files    (executive-summary, vision-and-philosophy, glossary)
├── 02-architecture/       9 files    (car-model, microkernel, event-bus, entry-points,
│                                      prompt, context-cache, memory, security, sidecars)
├── 03-contracts-and-models/ 7 files  (ports, schemas, tools, task-acceptance, errors,
│                                      lsp, protocols)
├── 04-workflows-and-loops/ 3 files   (dmartic, worktrees, rhi)
├── 05-tech-stack/         7 files    (control-plane, deps, llm-economics, config,
│                                      indexing, telemetry, aoi)
├── 06-guides-and-patterns/ 8 files   (getting-started, adapters, conformance, metrics,
│                                      ci-gates, bench-curation, running-bench, sidecar-dev)
├── 07-roadmap/            1 file
├── 08-decisions/          13 files   (README + ADR-0001..0012)
├── implementation/        1 file
├── reference/             3 files    (Conceptual Design 533L, Blueprint 939L, benchmarking 86L)
└── README.md

Modular tree:  ~3,600 lines
Reference:     ~1,560 lines
Code:          0 lines
Build files:   none (pyproject.toml, .importlinter, ci.yml, .pre-commit-config.yaml all absent)
```

# Appendix B — Verification commands used

Every cross-document contradiction in this report was confirmed with these. Re-run after remediation.

```bash
cd docs

# D12 — Python version drift
grep -rn "Python 3\.1[23]\|>=3\.13" --include="*.md" . | grep -v "deprecated in Python 3.12"

# D13 — cache hit targets
grep -rn -iE "cache.*(hit|ratio)" --include="*.md" . | grep -E "0\.8|9[0-9]%"

# D15 — reversed decisions surviving in reference/
grep -rn "Neo4j\|FalkorDB\|tqdb\|tq_vector_go" --include="*.md" .
grep -rn "gRPC" --include="*.md" .
grep -rn -i "plugin discovery\|discovery is automatic\|register new ports" --include="*.md" .

# X2 — revision autobiography volume
grep -rioE "the previous (revision|specification|design|documentation|schema|roadmap|matrix|port|drafts?)|earlier (revisions?|drafts?)|prior (revision|specification)" \
  --include="*.md" . | wc -l          # was: 44
grep -rliE "previous (revision|specification)|earlier (revisions?|drafts?)|prior revision" \
  --include="*.md" . | wc -l          # was: 15 of 56 files

# D7 — trace ownership
grep -rn -A2 "derived from\|single source" --include="*.md" \
  02-architecture/microkernel-and-bus.md \
  05-tech-stack/control-plane-python.md \
  05-tech-stack/observability-and-telemetry.md

# G1 — embedding provider
grep -rn "sentence-transformers\|fastembed\|onnx\|voyage\|embed" --include="*.md" 05-tech-stack/
```

# Appendix C — Finding index

| ID | Title | Severity |
| :--- | :--- | :--- |
| D1 | `Grant` is forgeable; capability model not enforced | Critical |
| D2 | `ModelProvider` cannot return reasoning blocks | Critical |
| D3 | Streaming loses token accounting | Critical |
| D4 | `CodeGraph.query()` violates both contract rules | High |
| D5 | Acceptance criteria never reach `GateReport` | High |
| D6 | Memory is an untrusted-data laundering path | High |
| D7 | Three docs disagree on trace ownership | High |
| D8 | `Orchestrator.execute` has two signatures | High |
| D9 | Edit contract mismatch; `Edit` undefined | High |
| D10 | `EffectClass` per-tool vs. `git` per-op | Medium |
| D11 | `PolicyEngine`/`Evaluator` lack conformance suites | Medium |
| D12 | Python 3.12/3.13 drift, 6 sites | Medium |
| D13 | Cache-hit target stated 3 ways | Medium |
| D14 | `metrics-analytics…md` is an unrevised draft | High |
| D15 | Reference blueprints reverse accepted ADRs | High |
| D16 | Citation artifacts | Low |
| G1 | No embedding provider | Blocker (S2/S4) |
| G2 | Python-only stack vs. multi-language ambition | High |
| G3 | No mid-run steering | High |
| G4 | No sub-agent result contract | Medium |
| G5 | Edit format never measured | Medium |
| G6 | Benchmark chicken-and-egg | High |
| G7 | No trajectory schema versioning | Medium |
| G8 | Nothing measures code quality | High |
| G9 | No velocity or adoption milestone | Medium |
| G10 | Sandbox timing contradicts itself | Medium |
| C1 | Cut best-of-N from v1 | — |
| C2 | Cut RHI from v1, keep its substrate | — |
| C3 | Delete `aoi/` from v1 | — |
| C4 | Lexical + graph retrieval only in S2 | — |
| C5 | Add a `Toolchain` port | — |
| C6 | Remove the Grant parameter | — |
| C7 | Pin container mechanism; write egress allowlist | — |
| C8 | Swap mypy for `ty`/`pyrefly` in the advisory slot | — |
| C9 | Seven missing dependencies | — |
| C10 | Concurrency design for three SQLite stores | — |
| C11 | Reframe the "dumb harness" thesis | — |
| X1 | Ports/schemas into code | — |
| X2 | Autobiography into ADR Context | — |
| X3 | Neutralize superseded reference passages | — |
| X4 | Rewrite/delete metrics doc | — |
| X5 | Commit the already-written build files | — |
| X6 | Add a "v0.1 for a real user" page | — |
| X7 | Single mechanical consistency pass | — |
