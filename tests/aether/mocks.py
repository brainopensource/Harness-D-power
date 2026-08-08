"""In-memory test doubles for all 9 aether ports.

These are test fixtures, not adapters: they live under tests/, never under
src/aether/adapters/. Per ADR-0005 rev. 2, ports/*.py's "mock adapter" entry
requirement is satisfied by these, while the *first real* adapter for each
port is a separately named, out-of-scope backlog task (TASK-011/017/018/
019/026 for the non-TCB ports; PolicyEngine's and ResourceGovernor's real
implementations are TASK-003 (kernel/, in scope) and TASK-034 respectively).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime

from aether.domain.budget import Actuals, BudgetDims, Lease
from aether.domain.gate import GateReport, GateStatus
from aether.domain.ids import LeaseId, RunId
from aether.domain.model_io import ModelRequest, ModelStreamEvent, StopEvent, TextDelta, UsageEvent
from aether.domain.tools import ToolCall, ToolResult, ToolSpec
from aether.domain.workspace import FileSlice, PatchResult, WorktreeRef
from aether.ports.evaluator import EvalSpec
from aether.ports.indexer import SymbolHit
from aether.ports.resource_governor import ReservationDenied
from aether.ports.trajectory_store import StoredEvent


class FakeModelProvider:
    """Yields a canned two-delta-plus-stop stream; never calls a real endpoint."""

    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelStreamEvent]:
        yield TextDelta(text="ok")
        yield UsageEvent(prompt_tokens=1, completion_tokens=1)
        yield StopEvent(reason="end")

    async def count_tokens(self, request: ModelRequest) -> int:
        return sum(len(m.spans) for m in request.messages) or 1


class InMemoryWorkspace:
    def __init__(self) -> None:
        self._files: dict[str, str] = {}

    async def read(
        self, worktree: WorktreeRef, repo_rel_path: str, start_line: int = 1, end_line: int = -1
    ) -> FileSlice:
        text = self._files.get(repo_rel_path, "")
        return FileSlice(repo_rel_path=repo_rel_path, start_line=start_line, end_line=end_line, text=text)

    async def write(self, worktree: WorktreeRef, repo_rel_path: str, text: str) -> None:
        self._files[repo_rel_path] = text

    async def apply_patch(self, worktree: WorktreeRef, unified_diff: str) -> PatchResult:
        return PatchResult(applied=True, rejected_hunks=0)

    async def diff(self, worktree: WorktreeRef) -> str:
        return ""


class InMemoryWorktreeManager:
    def __init__(self) -> None:
        self._active: dict[RunId, list[WorktreeRef]] = {}

    async def create(self, run_id: RunId, base_commit: str) -> WorktreeRef:
        ref = WorktreeRef(
            worktree_id=f"wt-{len(self._active.get(run_id, []))}",
            run_id=run_id,
            base_commit=base_commit,
            abs_hint=f"/tmp/{run_id}",
        )
        self._active.setdefault(run_id, []).append(ref)
        return ref

    async def destroy(self, worktree: WorktreeRef) -> None:
        refs = self._active.get(worktree.run_id, [])
        self._active[worktree.run_id] = [r for r in refs if r.worktree_id != worktree.worktree_id]

    async def list_active(self, run_id: RunId) -> tuple[WorktreeRef, ...]:
        return tuple(self._active.get(run_id, []))


class FixedCatalogToolRegistry:
    def __init__(self, catalog: tuple[ToolSpec, ...] = ()) -> None:
        self._catalog = catalog

    async def catalog(self) -> tuple[ToolSpec, ...]:
        return self._catalog

    async def execute(self, worktree: WorktreeRef, call: ToolCall) -> ToolResult:
        return ToolResult(call_id=call.call_id, spans=(), exit_code=0)


class InMemoryIndexer:
    async def build(self, worktree: WorktreeRef) -> None:
        return None

    async def search(self, worktree: WorktreeRef, query: str, limit: int = 20) -> tuple[SymbolHit, ...]:
        return ()

    async def outline(self, worktree: WorktreeRef, repo_rel_path: str) -> tuple[SymbolHit, ...]:
        return ()


class InMemoryResourceGovernor:
    """Integer-only reserve/commit/release ledger. Doubles as TASK-002's
    ResourceGovernor mock and TASK-003's Dispatcher test double."""

    def __init__(self) -> None:
        self._reserved: dict[LeaseId, Lease] = {}
        self._spent: dict[RunId, BudgetDims] = {}
        self._next_id = 0

    async def reserve(
        self, run_id: RunId, dims: BudgetDims, parent: LeaseId | None = None
    ) -> Lease | ReservationDenied:
        self._next_id += 1
        lease = Lease(
            lease_id=LeaseId(f"lease-{self._next_id}"),
            run_id=run_id,
            reserved=dims,
            parent=parent,
            issued_at=datetime.now(UTC),
        )
        self._reserved[lease.lease_id] = lease
        return lease

    async def commit(self, lease_id: LeaseId, actuals: Actuals) -> None:
        lease = self._reserved.pop(lease_id, None)
        if lease is None:
            return
        prior = self._spent.get(lease.run_id, BudgetDims())
        self._spent[lease.run_id] = BudgetDims(
            usd_micros=prior.usd_micros + actuals.dims.usd_micros,
            prompt_tokens=prior.prompt_tokens + actuals.dims.prompt_tokens,
            completion_tokens=prior.completion_tokens + actuals.dims.completion_tokens,
            wall_clock_ms=prior.wall_clock_ms + actuals.dims.wall_clock_ms,
            concurrency_slots=prior.concurrency_slots,
        )

    async def release(self, lease_id: LeaseId) -> None:
        self._reserved.pop(lease_id, None)

    async def spent(self, run_id: RunId) -> BudgetDims:
        return self._spent.get(run_id, BudgetDims())

    async def remaining(self, run_id: RunId) -> BudgetDims | None:
        return None  # this double seeds no ceiling, so the run is unbounded


class InMemoryTrajectoryStore:
    def __init__(self) -> None:
        self._events: dict[RunId, list[StoredEvent]] = {}

    async def append(self, event: StoredEvent) -> None:
        self._events.setdefault(event.run_id, []).append(event)

    async def replay(self, run_id: RunId, from_seq: int = 0) -> AsyncIterator[StoredEvent]:
        for event in self._events.get(run_id, []):
            if event.seq >= from_seq:
                yield event

    async def latest_seq(self, run_id: RunId) -> int:
        events = self._events.get(run_id, [])
        return events[-1].seq if events else 0


class FakeEvaluator:
    """Always PASSED — a test double, not the real TCB Evaluator (TASK-019)."""

    async def evaluate(self, spec: EvalSpec) -> GateReport:
        return GateReport(gate="tests_unmodified", status=GateStatus.PASSED)
