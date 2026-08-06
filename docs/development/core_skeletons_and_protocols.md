---
status: rationale
updated: 2026-08-06
---

# CORE_SKELETONS_AND_PROTOCOLS — Pre-Phase 1 Engineering Specification

**Owners**: Tech Leads (Domain · Infrastructure · Measurement)
**Standing**: pseudocode-grade skeletons. When these land in `src/aether/`, **the code becomes the contract and this file stops being authoritative** (house rule: documents navigate, code defines).

> **Conformance note on the memo's port list.** The memo requested `Memory`, `CodeGraph`, and `EventBus` as core ports and a merged `WorkspaceManager`. This drifts from the ratified spec: `Memory`/`CodeGraph` are **growth-tier** (ADR-0005: no port without its first adapter — sketched in §6, not to be committed to `ports/`); `EventBus` is a **kernel component**, not an I/O boundary (§5); and the ratified boundary is `Workspace` + `WorktreeManager`, two protocols on one boundary. This file implements the ratified nine. If leadership wants the memo's list instead, that is an ADR-0005 amendment, not a silent skeleton change.

**Port rules enforced by the reflection meta-test (spec §4)**: every method `async`; payloads are frozen Pydantic models or scalars; no `Path`, file handle, callable, generator-as-argument, or live object; no `dict[str, Any]`; timezone-aware datetimes only; **no `Grant` in any public port signature** (authorization is kernel-internal).

---

## 0. Package scaffolding

```
src/aether/
├── domain/            # §1 — pure models, zero I/O (I1)
│   ├── ids.py         # NewType ids: RunId, TaskId, LeaseId, SpanId, NodeId
│   ├── task.py        # Task, TaskSource
│   ├── taint.py       # Provenance, TaintSpan
│   ├── budget.py      # BudgetDims, Lease, Actuals
│   ├── gate.py        # GateStatus, GateReport
│   ├── model_io.py    # ModelRequest, ModelStreamEvent union
│   ├── workspace.py   # WorktreeRef, PatchResult, FileSlice
│   ├── tools.py       # ToolSpec, ToolCall, ToolResult
│   └── events.py      # typed event catalog (generated docs; drift-checked)
├── ports/             # §2–§4 — the nine ratified protocols
├── kernel/            # §5 — dispatch, policy, governor, bus, shell_ast (TCB)
├── agency/            # loop, repair; context/{assembler,compactor,taint_gate}
├── adapters/          # concrete non-TCB implementations
├── measurement/       # §7 — evaluator, statistics, runner, HarnessUnderTest (TCB)
├── workflow/          # §8 — step, validator, executor
├── evolution/         # offline only; forbidden importer of TCB
├── engine.py
└── composition.py     # explicit wiring; entry points frozen here (I6)
```

---

## 1. Domain primitives (referenced by every port)

```python
# domain/ — all models: ConfigDict(frozen=True); pure stdlib + pydantic.
from __future__ import annotations
from datetime import datetime
from enum import StrEnum
from typing import Literal, NewType
from pydantic import BaseModel, ConfigDict, Field

RunId = NewType("RunId", str); TaskId = NewType("TaskId", str)
LeaseId = NewType("LeaseId", str); SpanId = NewType("SpanId", str)
NodeId = NewType("NodeId", str)

class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

class Provenance(StrEnum):
    """Taint labels (ADR-0015). Ordering is not trust ordering; the policy
    predicate names admissible sets explicitly."""
    TRUSTED_SYSTEM = "trusted-system"
    OPERATOR = "operator"
    AGENT = "agent"
    UNTRUSTED_EXTERNAL = "untrusted-external"
    UNTRUSTED_DERIVED = "untrusted-derived"

UNTRUSTED: frozenset[Provenance] = frozenset(
    {Provenance.UNTRUSTED_EXTERNAL, Provenance.UNTRUSTED_DERIVED}
)

class TaintSpan(Frozen):
    """A contiguous slice of context with a single provenance label.
    Spans are the atoms of the TaintGate; they are never merged across labels."""
    span_id: SpanId
    label: Provenance
    text: str
    source: str                      # e.g. "issue_body", "tool:pytest", "layer:L1"
    created_at: datetime             # tz-aware (reflection test enforces)

class GateStatus(StrEnum):
    """Tri-state (spec §7). NONE means *unmeasured / instrument error* and never
    silently passes — B4's typed distinction lives here."""
    PASSED = "passed"
    FAILED = "failed"
    NONE = "none"

class GateReport(Frozen):
    gate: str
    status: GateStatus
    detail: str = ""
    instrument_error: str | None = None   # populated iff status == NONE

class BudgetDims(Frozen):
    """Integer-only budget vector. Currency in micro-USD; floats are banned
    from budget arithmetic by type."""
    usd_micros: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    wall_clock_ms: int = 0
    concurrency_slots: int = 0

class Lease(Frozen):
    lease_id: LeaseId
    run_id: RunId
    reserved: BudgetDims
    parent: LeaseId | None = None    # fan-out: child leases carve a parent
    issued_at: datetime
```

---

## 2. Core ports — model, workspace, tools, indexing

```python
# ports/model_provider.py
from typing import AsyncIterator, Protocol, runtime_checkable

class ModelMessage(Frozen):
    role: Literal["system", "user", "assistant", "tool"]
    spans: tuple[TaintSpan, ...]          # content carries provenance, always
    cache_breakpoint: bool = False        # ≤4 true across a request (I10)

class ModelRequest(Frozen):
    model: str
    messages: tuple[ModelMessage, ...]
    tools: tuple["ToolSpec", ...] = ()
    max_tokens: int
    temperature: float = 0.0
    seed: int | None = None

class TextDelta(Frozen):    kind: Literal["text"] = "text"; text: str
class ToolCallDelta(Frozen): kind: Literal["tool_call"] = "tool_call"; call_id: str; name: str; args_json_fragment: str
class UsageEvent(Frozen):   kind: Literal["usage"] = "usage"; prompt_tokens: int; completion_tokens: int; cached_prompt_tokens: int = 0
class StopEvent(Frozen):    kind: Literal["stop"] = "stop"; reason: Literal["end", "tool_use", "max_tokens", "provider_error"]
ModelStreamEvent = TextDelta | ToolCallDelta | UsageEvent | StopEvent

@runtime_checkable
class ModelProvider(Protocol):
    """One adapter per provider family; a RoutingModelProvider composite
    satisfies multi-model roles (ADR-0007). Adapters enforce the request's
    token ceilings — conservation is kernel policy, not adapter courtesy."""
    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelStreamEvent]: ...
    async def count_tokens(self, request: ModelRequest) -> int: ...
```

```python
# ports/workspace.py — two protocols, one boundary (ratified)
class WorktreeRef(Frozen):
    worktree_id: str; run_id: RunId; base_commit: str; abs_hint: str
    # abs_hint is a *string* description for logs — never a Path (I3)

class FileSlice(Frozen):
    repo_rel_path: str; start_line: int; end_line: int; text: str

class PatchResult(Frozen):
    applied: bool; rejected_hunks: int; detail: str = ""

@runtime_checkable
class Workspace(Protocol):
    """Read/write access to one worktree's files. All paths repo-relative strings."""
    async def read(self, worktree: WorktreeRef, repo_rel_path: str,
                   start_line: int = 1, end_line: int = -1) -> FileSlice: ...
    async def write(self, worktree: WorktreeRef, repo_rel_path: str, text: str) -> None: ...
    async def apply_patch(self, worktree: WorktreeRef, unified_diff: str) -> PatchResult: ...
    async def diff(self, worktree: WorktreeRef) -> str: ...

@runtime_checkable
class WorktreeManager(Protocol):
    """Worktree lifecycle. create() is timer-instrumented from day one (ADR-0001)."""
    async def create(self, run_id: RunId, base_commit: str) -> WorktreeRef: ...
    async def destroy(self, worktree: WorktreeRef) -> None: ...
    async def list_active(self, run_id: RunId) -> tuple[WorktreeRef, ...]: ...
```

```python
# ports/tool_registry.py
class ToolSpec(Frozen):
    name: str; description: str; params_json_schema: str   # schema as JSON string
    effect_class: Literal["read", "write", "shell", "network", "model"]

class ToolCall(Frozen):
    call_id: str; name: str; args_json: str
    justifying_spans: tuple[SpanId, ...]   # ← what the TaintGate audits (§5)

class ToolResult(Frozen):
    call_id: str
    spans: tuple[TaintSpan, ...]           # outputs are labeled at birth:
    exit_code: int | None = None           #   tool output ⇒ UNTRUSTED_EXTERNAL

@runtime_checkable
class ToolRegistry(Protocol):
    """Catalog frozen at composition (I6); MCP arrives later as one adapter
    of this same protocol (ADR-0016) — outputs labeled untrusted like any tool."""
    async def catalog(self) -> tuple[ToolSpec, ...]: ...
    async def execute(self, worktree: WorktreeRef, call: ToolCall) -> ToolResult: ...
```

```python
# ports/indexer.py
class SymbolHit(Frozen):
    repo_rel_path: str; line: int; kind: str; name: str; snippet: str

@runtime_checkable
class Indexer(Protocol):
    """Syntax-tier retrieval (tree-sitter adapter, ADR-0011). Semantic answers
    come from the project's own toolchain at T2 — deliberately not this port."""
    async def build(self, worktree: WorktreeRef) -> None: ...
    async def search(self, worktree: WorktreeRef, query: str, limit: int = 20) -> tuple[SymbolHit, ...]: ...
    async def outline(self, worktree: WorktreeRef, repo_rel_path: str) -> tuple[SymbolHit, ...]: ...
```

---

## 3. TCB ports — policy and evaluator

```python
# ports/policy_engine.py  (implementation resides in kernel/ — audit D8 rule)
class EffectRequest(Frozen):
    run_id: RunId
    effect_class: Literal["read", "write", "shell", "network", "model", "evaluate"]
    descriptor: str                        # e.g. shell string, path, model name
    justifying_spans: tuple[TaintSpan, ...]  # full spans: the gate audits labels
    widens_capability: bool                # classifier output (shell_ast / static)

class Decision(StrEnum):
    GRANT = "grant"; REJECT = "reject"
    ASK_RULE_MATCH = "ask_rule_match"; ASK_FAIL_CLOSED = "ask_fail_closed"

class PolicyDecision(Frozen):
    decision: Decision; rule_id: str; rationale: str

@runtime_checkable
class PolicyEngine(Protocol):
    """TCB. The taint predicate lives here (ADR-0015): a capability-widening
    request justified by any span in UNTRUSTED labels fails closed. Note the
    port returns a *decision*, never a Grant object — grants are kernel-internal
    (spec §4: no Grant in public signatures)."""
    async def authorize(self, request: EffectRequest) -> PolicyDecision: ...
```

```python
# ports/evaluator.py  (implementation resides in measurement/ — TCB)
class EvalSpec(Frozen):
    task_id: TaskId
    worktree: WorktreeRef
    image_digest: str                      # pinned in the task manifest (TCB data)
    test_command_hash: str                 # verified against manifest before run
    timeout_ms: int

@runtime_checkable
class Evaluator(Protocol):
    """TCB. Runs the task's real tests in the evaluation container
    (network none, digest-pinned). Exit-127 / uncollectable ⇒ GateStatus.NONE
    with instrument_error set — never FAILED (B4)."""
    async def evaluate(self, spec: EvalSpec) -> GateReport: ...
```

---

## 4. ResourceGovernor and TrajectoryStore

```python
# ports/resource_governor.py
class Actuals(Frozen):
    dims: BudgetDims

class ReservationDenied(Frozen):
    shortfall: BudgetDims; rationale: str

@runtime_checkable
class ResourceGovernor(Protocol):
    """Reserve-before-effect ledger (spec §5). The dispatcher refuses any effect
    without a live lease, which makes after-the-fact accounting structurally
    unrepresentable. Integer arithmetic only; atomic under one asyncio.Lock now,
    protocol unchanged if the governor ever moves out of process (I3)."""
    async def reserve(self, run_id: RunId, dims: BudgetDims,
                      parent: LeaseId | None = None) -> Lease | ReservationDenied: ...
    async def commit(self, lease_id: LeaseId, actuals: Actuals) -> None:
        """actuals ≤ reserved ⇒ remainder released; actuals > reserved ⇒ typed
        BudgetOverrun event emitted AND reality debited (the ledger never lies)."""
    async def release(self, lease_id: LeaseId) -> None:
        """Cancel path; idempotent. Child release refunds the parent lease,
        not the global pool — Best-of-N loser cancellation refunds correctly."""
    async def remaining(self, run_id: RunId) -> BudgetDims: ...
```

```python
# ports/trajectory_store.py
class StoredEvent(Frozen):
    seq: int; run_id: RunId; event_type: str; payload_json: str; at: datetime

@runtime_checkable
class TrajectoryStore(Protocol):
    """Durable append-only log; a bus consumer like any other. Replay for the
    prompt-cache CI floor (I10) and record/replay cassettes reads from here."""
    async def append(self, event: StoredEvent) -> None: ...
    async def replay(self, run_id: RunId, from_seq: int = 0) -> AsyncIterator[StoredEvent]: ...
    async def latest_seq(self, run_id: RunId) -> int: ...
```

---

## 5. Kernel — choke point, TaintGate, bus (not ports; TCB classes)

```python
# kernel/dispatch.py — THE single choke point (I5). Architecture test proves
# no adapter is invoked outside this module (import graph + call audit).
class Dispatcher:
    """authorize → verify grant → acquire lease → dispatch → release.

    Grants are internal: issued by policy, held in _grants, re-VERIFIED against
    the *current* request immediately before the effect (arguments can change
    between issuance and use; a resumed run can carry a stale grant)."""

    def __init__(self, policy: PolicyEngine, governor: ResourceGovernor,
                 bus: "EventBus", adapters: "AdapterTable") -> None: ...

    async def dispatch(self, request: EffectRequest,
                       cost_estimate: BudgetDims) -> "EffectOutcome":
        decision = await self._policy.authorize(request)          # 1 authorize
        if decision.decision is not Decision.GRANT:
            self._deny_ledger.record(request)                     # 3/20 bound (ADR-0008)
            return EffectOutcome.denied(decision)
        grant = self._grants.issue(request, decision)             # internal only
        self._verify(grant, request)                              # 2 verify @ effect-time
        lease = await self._governor.reserve(request.run_id, cost_estimate)  # 3 lease
        if isinstance(lease, ReservationDenied):
            return EffectOutcome.budget_denied(lease)
        try:
            outcome = await self._route_to_adapter(request, lease)  # 4 dispatch
            await self._governor.commit(lease.lease_id, outcome.actuals)
            return outcome
        except Exception as exc:                                    # stubs raise;
            await self._governor.release(lease.lease_id)            # 5 release
            raise                                                   # never swallowed to []
```

```python
# agency/context/taint_gate.py — deterministic propagation (ADR-0015)
def propagate(consumed: Sequence[TaintSpan]) -> Provenance:
    """Output label for a completion given the spans it consumed.
    Deterministic and monotone: any untrusted input ⇒ UNTRUSTED_DERIVED output."""
    labels = {s.label for s in consumed}
    return Provenance.UNTRUSTED_DERIVED if labels & UNTRUSTED else Provenance.AGENT
# The *enforcement* predicate is in kernel PolicyEngine (§3), not here: the gate
# labels; the policy decides. Red-team CI gate: pinned injection corpus ⇒ 0 grants.
```

```python
# kernel/bus.py — append-only typed bus. Kernel component, NOT a port:
# it never crosses the process boundary as a dependency; remote surfaces
# consume the TrajectoryStore or an engine-exposed stream instead.
class EventBus:
    def emit(self, event: DomainEvent) -> None: ...        # validated vs catalog
    def subscribe(self, consumer_id: str, *,
                  drop_policy: Literal["never", "drop_oldest"]) -> AsyncIterator[DomainEvent]: ...
    # "never" reserved for TrajectoryStore + measurement harvester;
    # display consumers are drop_oldest. Events never schedule nodes (ADR-0013).
```

---

## 6. Growth-tier sketches — NOT to be committed to `ports/` (ADR-0005)

```python
# Reference shapes only. Each enters ports/ in the same change as its first
# adapter + conformance test, or (amended ADR-0005) a mock adapter with the
# first real adapter *named*. Committing these earlier repeats the
# seventeen-ports failure this project exists to not repeat.

@runtime_checkable
class Memory(Protocol):                       # growth tier
    """Long-term memory. Content is meta-loop-mutable state (ADR-0006 table
    amendment); retrieved memories re-enter context as UNTRUSTED_DERIVED —
    memory must not launder injected content into authority."""
    async def store(self, run_id: RunId, spans: tuple[TaintSpan, ...], tags: tuple[str, ...]) -> None: ...
    async def recall(self, query: str, limit: int = 8) -> tuple[TaintSpan, ...]: ...

@runtime_checkable
class CodeGraph(Protocol):                    # growth tier
    """Cross-file structural queries above Indexer's syntax tier. Admitted only
    if its retrieval ablation clears the noise floor — same bar as everything."""
    async def build(self, worktree: WorktreeRef) -> None: ...
    async def neighbors(self, symbol: str, depth: int = 1) -> tuple[SymbolHit, ...]: ...
```

---

## 7. Measurement & runner seams (TCB)

```python
# measurement/runner.py
class ArmOutcome(Frozen):
    task_id: TaskId; resolved: bool | None      # None = instrument error (excluded
    cost: BudgetDims; instrument_error: str | None = None   # from denominator, B4)

class PairedRun(Frozen):
    manifest_hash: str; model_fingerprint: str; seed: int
    arm_a: str; arm_b: str
    outcomes: tuple[tuple[ArmOutcome, ArmOutcome], ...]   # paired by task, in order

@runtime_checkable
class HarnessUnderTest(Protocol):
    """The comparative-lift seam. Arms: bare-model baseline, AETHER,
    OpenHands (OSS), others as licensing permits — same model, same manifest,
    same Evaluator. This is measurement tooling, not a port in ports/
    (ADR-0005: 'measurement is a tool'); it lives in measurement/ (TCB)."""
    @property
    def harness_id(self) -> str: ...
    async def attempt(self, task_id: TaskId, model_fingerprint: str,
                      budget: BudgetDims, seed: int) -> ArmOutcome: ...

class PairedRunner:
    """Executes two HarnessUnderTest arms task-paired (same order, same seeds),
    routes every outcome through the one Evaluator, hands PairedRun to
    statistics.py (exact McNemar + Holm–Bonferroni + bootstrap CI, ADR-0003
    rev.2: tiered N from the pre-registered family file — family declared
    BEFORE any arm runs; statistics module refuses undeclared families)."""
    async def run(self, family_id: str, manifest_hash: str,
                  a: HarnessUnderTest, b: HarnessUnderTest) -> PairedRun: ...
```

---

## 8. Workflow executor & node engine (ADR-0013/0014)

```python
# workflow/step.py
from typing import Generic, TypeVar
In = TypeVar("In", bound=Frozen); Out = TypeVar("Out", bound=Frozen)

class StepContext(Frozen):
    run_id: RunId; node_id: NodeId; lease: LeaseId
    # Steps receive NO adapter handles: all effects go through a dispatch
    # facade injected by the executor — the choke point is unavoidable by type.

class WorkflowStep(Generic[In, Out]):
    """Abstract node. Concrete steps are registered at composition (I6) under a
    stable string id; topologies (YAML) reference ids, never classes."""
    node_kind: str                                   # e.g. "retrieve", "repair"
    input_type: type[In]; output_type: type[Out]     # socket types — the schema
                                                     # validator checks edges with these
    async def run(self, ctx: StepContext, payload: In) -> Out:
        raise NotImplementedError                    # stubs raise (spec §7)

    def input_digest(self, payload: In) -> str:
        """M2 memoization key = sha256(node_kind, impl_version, payload json).
        Deterministic serialization via pydantic; digest recorded in node events."""
        ...
```

```python
# workflow/validator.py — TCB
class TopologyValidationError(Exception):
    """Names the failed check: socket_mismatch | no_evaluator_termination |
    unbounded_iteration | undeclared_fanout | missing_budget_annotation."""

class TopologyValidator:
    """jsonschema (Draft 2020-12) structural pass, then the five static checks
    of Diagram 5. The validator, schema, and executor are TCB; topologies are
    mutable-surface data. The executor refuses any graph this class rejects —
    there is no --force flag, by design."""
    def validate(self, topology_yaml: str,
                 registry: Mapping[str, WorkflowStep]) -> "ValidatedTopology": ...

# workflow/executor.py
class WorkflowExecutor:
    """M1a: unconditional linear order. M2: memoized subtree re-execution.
    M3: fan-out (child leases) + conditional edges. Repair loops execute as
    statically unrolled bounded iterations (max_iterations from the topology).
    Emits node start/finish/skip(memo-hit) events; NEVER consumes events to
    schedule (ADR-0013)."""
    async def execute(self, topo: "ValidatedTopology", task: Task,
                      budget: BudgetDims) -> "RunResult": ...
```

---

## 9. Conformance meta-suite (I4 enforcement — TASK-005)

```python
# tests/conformance/ — ONE parametrized suite, N adapters. An adapter is not
# "done" until it appears in the params list; a port with an empty params list
# fails the meta-test (a contract that selects nothing forbids nothing).
@pytest.fixture(params=registered_adapters("ModelProvider"))
def model_provider(request): ...

class TestModelProviderConformance:
    async def test_all_methods_async_and_wire_serializable(self, model_provider): ...
    async def test_stream_terminates_with_stop_event(self, model_provider): ...
    async def test_token_ceiling_enforced(self, model_provider): ...
    async def test_provider_error_is_typed_never_empty_list(self, model_provider): ...
# Reflection meta-test over ports/: async-only, payload rules, no Grant,
# tz-aware datetimes — asserted generically for every protocol in one place.
```
