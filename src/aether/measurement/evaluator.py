"""TCB Evaluator (TASK-019) — runs the task's pinned test command in the
worktree and returns a typed tri-state `GateReport`.

Must live here, in `measurement/`, never `adapters/` — this residency is what
makes the `aether-tcb-isolation` import-linter contract select it (spec.md
§4). `import-linter` proves this module cannot import `aether.agency` or
`aether.workflow` (I7).

B4 contract: exit code 0 is PASSED, exit code 1 is FAILED (a real test
failure), and every other outcome — a `test_command_hash` mismatch, a missing
binary, a timeout, or any other nonzero exit — is `GateStatus.NONE` with
`instrument_error` set. NONE is never silently reported as FAILED; it is
excluded from the resolve-rate denominator (measurement.md §2 B4).

Ships uncontained this sprint — B3 containerization (TASK-016) is Sprint 3.
The pinned task manifest (TASK-014) doesn't exist yet either: `resolve_command`
is the seam a manifest-driven resolver plugs into later; for now callers (the
M1a smoke path, composition.py) supply one directly.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import shlex
from collections.abc import Callable

from aether.domain.gate import GateReport, GateStatus
from aether.domain.workspace import WorktreeRef
from aether.ports.evaluator import EvalSpec

_TAIL_CHARS = 4000  # tail-biased truncation: keep the failure block, not the pass list


def hash_command(command: str) -> str:
    return "sha256:" + hashlib.sha256(command.encode()).hexdigest()


def _worktree_path(worktrees_root: str, worktree: WorktreeRef) -> str:
    return os.path.join(worktrees_root, worktree.run_id, worktree.worktree_id)


def _tail(text: str, limit: int = _TAIL_CHARS) -> str:
    return text[-limit:]


class RealEvaluator:
    """TCB. `worktrees_root` mirrors `GitCliWorkspace`'s own convention for
    locating a worktree from `(run_id, worktree_id)` — no `Path` crosses the
    `EvalSpec` boundary (I3)."""

    def __init__(self, worktrees_root: str, resolve_command: Callable[[EvalSpec], str]) -> None:
        self._worktrees_root = worktrees_root
        self._resolve_command = resolve_command

    async def evaluate(self, spec: EvalSpec) -> GateReport:
        command = self._resolve_command(spec)
        actual_hash = hash_command(command)
        if actual_hash != spec.test_command_hash:
            return GateReport(
                gate="tests",
                status=GateStatus.NONE,
                instrument_error=(
                    f"test_command_hash mismatch: manifest={spec.test_command_hash} actual={actual_hash}"
                ),
            )

        path = _worktree_path(self._worktrees_root, spec.worktree)
        timeout_s = spec.timeout_ms / 1000

        try:
            proc = await asyncio.create_subprocess_exec(
                *shlex.split(command),
                cwd=path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            return GateReport(
                gate="tests", status=GateStatus.NONE, instrument_error=f"test command not found: {exc}"
            )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
        except TimeoutError:
            proc.kill()
            await proc.communicate()
            return GateReport(
                gate="tests", status=GateStatus.NONE, instrument_error=f"timed out after {spec.timeout_ms}ms"
            )

        exit_code = proc.returncode
        output = _tail((stdout + stderr).decode(errors="replace"))

        if exit_code == 0:
            return GateReport(gate="tests", status=GateStatus.PASSED, detail=output)
        if exit_code == 1:
            return GateReport(gate="tests", status=GateStatus.FAILED, detail=output)

        return GateReport(
            gate="tests",
            status=GateStatus.NONE,
            detail=output,
            instrument_error=f"exit {exit_code}: instrument/harness failure, not a test failure",
        )
