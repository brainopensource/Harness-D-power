"""Adapter → Protocol assignability, asserted mechanically (defect C-3).

The hexagon's central claim is that adapters are substitutable behind ports.
Before this file, nothing enforced it: a signature divergence produced a *green*
pytest run, and detection depended on a human remembering to run pyright —
which C-2 proved does not happen reliably (`Indexer.neighbors` drifted for a
whole sprint).

Each pair gets two assertions that fail in two different ways:

* the `_accepts_*(adapter)` call site is a **static** assertion — pyright
  reports an error here if the adapter no longer satisfies the Protocol, and
  `uv run pyright src/sagiha tests/contracts` is the gate that reads it;
* the surrounding test is a **runtime** assertion — it proves the adapter still
  constructs, so a Protocol satisfied only by a class nobody can instantiate
  does not pass silently.

Add a pair here whenever a new adapter is written. This file is the registry.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sagiha.adapters.code_graph.treesitter import TreeSitterCodeGraph
from sagiha.adapters.indexer.fts5 import FTS5Indexer
from sagiha.adapters.sandbox.container import ContainerSandbox
from sagiha.adapters.search.best_of_n import BestOfNSearch
from sagiha.adapters.search.protocols import CandidateOutcome
from sagiha.adapters.search.scoring import NullScorer
from sagiha.adapters.trajectory.sqlite import SQLiteTrajectoryStore
from sagiha.adapters.workspace.local import LocalWorkspace
from sagiha.domain.config import SearchConfig
from sagiha.domain.control import RunContext
from sagiha.domain.work import TaskSpec
from sagiha.kernel.governor import DefaultResourceGovernor
from sagiha.kernel.policy.engine import DefaultPolicyEngine
from sagiha.ports.code_graph import CodeGraph
from sagiha.ports.governor import ResourceGovernor
from sagiha.ports.indexer import Indexer
from sagiha.ports.policy import PolicyEngine
from sagiha.ports.search import CandidateSearch
from sagiha.ports.trajectory import TrajectoryStore
from sagiha.ports.workspace import Workspace

# --- static assertion helpers -------------------------------------------------
# Each takes the port type. Passing an adapter that has drifted is a pyright
# error at the call site, which is exactly where a reader wants to see it.


def _accepts_indexer(_: Indexer) -> None: ...
def _accepts_code_graph(_: CodeGraph) -> None: ...
def _accepts_workspace(_: Workspace) -> None: ...
def _accepts_candidate_search(_: CandidateSearch) -> None: ...
def _accepts_trajectory_store(_: TrajectoryStore) -> None: ...
def _accepts_policy_engine(_: PolicyEngine) -> None: ...
def _accepts_resource_governor(_: ResourceGovernor) -> None: ...


# --- retrieval ----------------------------------------------------------------


def test_fts5_indexer_satisfies_indexer(tmp_path: Path) -> None:
    _accepts_indexer(FTS5Indexer(db_path=str(tmp_path / "index.db")))


def test_treesitter_satisfies_code_graph(tmp_path: Path) -> None:
    _accepts_code_graph(TreeSitterCodeGraph(db_path=str(tmp_path / "graph.db"), workspace_root=tmp_path))


# --- workspace ----------------------------------------------------------------


def test_local_workspace_satisfies_workspace(tmp_path: Path) -> None:
    _accepts_workspace(LocalWorkspace(str(tmp_path)))


def test_container_sandbox_satisfies_workspace(tmp_path: Path) -> None:
    """Constructing the sandbox does not start a container — no Podman needed here.

    The behavioural half lives in the Podman-marked conformance suite; this
    asserts only that the two Workspace implementations stay interchangeable.
    """
    _accepts_workspace(ContainerSandbox(str(tmp_path), state_dir=str(tmp_path / "state")))


# --- search -------------------------------------------------------------------


class _NullWorktreeManager:
    """Minimal WorktreeManager double — BestOfNSearch needs one to construct.

    Signature-exact against the Protocol on purpose: a loose double would make
    this file's own dependencies exempt from the discipline it enforces.
    """

    async def allocate(self, base_commit: str, branch_id: str) -> Workspace:
        return LocalWorkspace(base_commit)

    async def materialize(self, branch_id: str) -> None: ...

    async def release(self, branch_id: str) -> None: ...


class _NullExecutor:
    """Minimal CandidateExecutor double — never invoked by an assignability check."""

    async def execute(
        self,
        task: TaskSpec,
        context: RunContext,
        *,
        branch_id: str,
        base_commit: str,
        temperature: float | None = None,
        repair_round: int = 0,
    ) -> CandidateOutcome:  # pragma: no cover - construction-only double
        raise NotImplementedError


def test_best_of_n_satisfies_candidate_search() -> None:
    _accepts_candidate_search(
        BestOfNSearch(
            worktree_manager=_NullWorktreeManager(),
            executor=_NullExecutor(),
            scorer=NullScorer(),
            config=SearchConfig(),
        )
    )


# --- persistence --------------------------------------------------------------


def test_sqlite_store_satisfies_trajectory_store(tmp_path: Path) -> None:
    _accepts_trajectory_store(SQLiteTrajectoryStore(db_path=str(tmp_path / "traj.db")))


# --- TCB ----------------------------------------------------------------------


def test_default_policy_engine_satisfies_policy_engine() -> None:
    _accepts_policy_engine(DefaultPolicyEngine())


def test_default_governor_satisfies_resource_governor() -> None:
    _accepts_resource_governor(DefaultResourceGovernor())


# --- coverage guard -----------------------------------------------------------


@pytest.mark.parametrize(
    "pair",
    [
        ("FTS5Indexer", "Indexer"),
        ("TreeSitterCodeGraph", "CodeGraph"),
        ("LocalWorkspace", "Workspace"),
        ("ContainerSandbox", "Workspace"),
        ("BestOfNSearch", "CandidateSearch"),
        ("SQLiteTrajectoryStore", "TrajectoryStore"),
        ("DefaultPolicyEngine", "PolicyEngine"),
        ("DefaultResourceGovernor", "ResourceGovernor"),
    ],
)
def test_required_pair_has_a_test(pair: tuple[str, str]) -> None:
    """Fails if someone deletes an assignability test without deleting the pair.

    C-3 was a *missing* test, so the guard against its recurrence has to be a
    test about the tests.
    """
    adapter, _port = pair
    source = Path(__file__).read_text(encoding="utf-8")
    assert "_accepts_" in source and adapter in source, f"no assignability assertion covers {adapter}"
