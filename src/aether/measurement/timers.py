"""F1 performance timers (TASK-021) — worktree creation and AST parse-and-
validate.

These two numbers decide ADR-0001's Python-vs-Rust (F1) fork against its
RT-1/RT-2/RT-3 trigger table. Hardware and method are recorded alongside every
number — a bare number with no method is not a result here. Run as a script
to produce `docs/rationale/benchmarks/performance_timers.md`'s inputs:

    python -m aether.measurement.timers
"""

from __future__ import annotations

import asyncio
import os
import platform
import statistics
import subprocess
import tempfile
import time
from dataclasses import dataclass

from aether.adapters.indexer.tree_sitter import TreeSitterIndexer
from aether.adapters.workspace.git_cli import GitCliWorktreeManager
from aether.domain.ids import RunId
from aether.domain.workspace import WorktreeRef


@dataclass
class TimingResult:
    operation: str
    reps: int
    durations_ms: list[float]
    hardware: str

    @property
    def mean_ms(self) -> float:
        return statistics.mean(self.durations_ms)

    @property
    def p95_ms(self) -> float:
        if len(self.durations_ms) < 20:
            return max(self.durations_ms)
        return statistics.quantiles(self.durations_ms, n=20)[18]


def hardware_description() -> str:
    return (
        f"{platform.processor() or platform.machine()}, {os.cpu_count()} logical CPUs, "
        f"{platform.system()} {platform.release()}"
    )


async def time_worktree_creation(
    repo_path: str, worktrees_root: str, base_commit: str, reps: int = 10
) -> TimingResult:
    manager = GitCliWorktreeManager(repo_path, worktrees_root)
    durations: list[float] = []
    for i in range(reps):
        await manager.create(RunId(f"timing-run-{i}"), base_commit)
        assert manager.last_create_duration_ms is not None
        durations.append(manager.last_create_duration_ms)
    return TimingResult(
        operation="worktree_creation", reps=reps, durations_ms=durations, hardware=hardware_description()
    )


async def time_ast_parse_and_validate(
    worktrees_root: str, worktree: WorktreeRef, reps: int = 10
) -> TimingResult:
    indexer = TreeSitterIndexer(worktrees_root)
    durations: list[float] = []
    for _ in range(reps):
        start = time.perf_counter()
        await indexer.build(worktree)
        durations.append((time.perf_counter() - start) * 1000)
    return TimingResult(
        operation="ast_parse_and_validate", reps=reps, durations_ms=durations, hardware=hardware_description()
    )


def _git(*args: str, cwd: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _seed_throwaway_repo(repo_path: str) -> str:
    """Blocking setup (subprocess + file I/O) — run via `asyncio.to_thread`
    from the async report so it doesn't block the event loop (ASYNC221/230)."""
    os.makedirs(repo_path)
    _git("init", "-q", cwd=repo_path)
    _git("config", "user.email", "timer@example.com", cwd=repo_path)
    _git("config", "user.name", "Timer", cwd=repo_path)

    domain_src = os.path.join(os.path.dirname(__file__), "..", "domain")
    for fname in os.listdir(domain_src):
        if fname.endswith(".py"):
            with open(os.path.join(domain_src, fname), "rb") as src:
                content = src.read()
            with open(os.path.join(repo_path, fname), "wb") as dst:
                dst.write(content)
    _git("add", ".", cwd=repo_path)
    _git("commit", "-q", "-m", "init", cwd=repo_path)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_path, check=True, capture_output=True, text=True
    ).stdout.strip()


async def _run_report(reps: int = 10) -> tuple[TimingResult, TimingResult]:
    """Sets up a small throwaway repo (this project's own domain/ package,
    copied in, gives a realistic file count) and times both operations."""
    with tempfile.TemporaryDirectory() as tmp:
        repo_path = os.path.join(tmp, "repo")
        base_commit = await asyncio.to_thread(_seed_throwaway_repo, repo_path)

        worktrees_root = os.path.join(tmp, "worktrees")
        worktree_timing = await time_worktree_creation(repo_path, worktrees_root, base_commit, reps=reps)

        manager = GitCliWorktreeManager(repo_path, worktrees_root)
        worktree = await manager.create(RunId("ast-timing-run"), base_commit)
        parse_timing = await time_ast_parse_and_validate(worktrees_root, worktree, reps=reps)

        return worktree_timing, parse_timing


def main() -> None:
    worktree_timing, parse_timing = asyncio.run(_run_report())
    for result in (worktree_timing, parse_timing):
        print(f"## {result.operation}")
        print(f"- hardware: {result.hardware}")
        print(f"- reps: {result.reps}")
        print(f"- mean: {result.mean_ms:.2f}ms")
        print(f"- p95: {result.p95_ms:.2f}ms")
        print()


if __name__ == "__main__":
    main()
