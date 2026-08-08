"""TCB Evaluator (TASK-019 + TASK-016) — runs the task's pinned test command
against the candidate worktree and returns a typed tri-state `GateReport`.

Must live here, in `measurement/`, never `adapters/` — this residency is what
makes the `aether-tcb-isolation` import-linter contract select it (spec.md
§4). `import-linter` proves this module cannot import `aether.agency`,
`aether.workflow` or `aether.adapters` (I7).

B4 contract: exit code 0 is PASSED, exit code 1 is FAILED (a real test
failure), and every other outcome — a `test_command_hash` mismatch, a missing
binary, a timeout, a container that never started, or any other nonzero exit
— is `GateStatus.NONE` with `instrument_error` set. NONE is never silently
reported as FAILED; it is excluded from the resolve-rate denominator
(measurement.md §2 B4).

**Two execution modes, one mapping.** With a `sandbox` injected the command
runs inside the B3 evaluation container (`adapters/sandbox/podman.py`); with
none it runs uncontained via `asyncio.subprocess`, which is what keeps the
conformance suite runnable on a machine with no container runtime. The
uncontained mode is a CI convenience and is **not** valid for a published
number: `measurement.md` §2 requires the B3 canary to pass in the floor
environment first, and the canary is meaningless without the container.

The sandbox arrives as a structural `SandboxRunner` (below), never as an
import of the adapter — the TCB contract forbids this module from importing
`aether.adapters`, and the layer contract forbids adapters importing
`aether.measurement`. A Protocol declared here, satisfied structurally there,
is the only shape that respects both.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import shlex
from collections.abc import Callable
from typing import Protocol, runtime_checkable

from aether.domain.gate import GateReport, GateStatus
from aether.domain.sandbox import ContainerLimits, ContainerResult, ContainerSpec
from aether.domain.workspace import WorktreeRef
from aether.ports.evaluator import EvalSpec

_TAIL_CHARS = 4000  # tail-biased truncation: keep the failure block, not the pass list

#: `PYTHONDONTWRITEBYTECODE=1` is a B3-class defence, not tidiness, and the
#: container path sets it too. CPython invalidates a cached `.pyc` on
#: (mtime seconds, source size); a repair iteration that edits a line without
#: changing the file's length, inside the same second, satisfies both — so the
#: interpreter reuses the *previous* candidate's bytecode and the gate scores a
#: diff it never ran. That is the B3 failure mode exactly: a candidate's change
#: invisible to the judge. Caught by tests/integration/test_repair_e2e.py, which
#: is why the repair edge is where it surfaced: nothing before it re-evaluated
#: the same worktree twice.
#:
#: TASK-062: this used to be `{**os.environ, ...}`, handing model-written code
#: the operator's full shell environment — including e.g. `OPENROUTER_API_KEY`
#: — on the uncontained path. `adapters/subprocess_env.py` is the canonical
#: allowlist (`NON_INTERACTIVE` + `spawn_env()`), but `aether-tcb-isolation`
#: (`.importlinter`) forbids this module from importing `aether.adapters` —
#: the same reason `SandboxRunner` above is a structural Protocol rather than
#: an import of `adapters/sandbox/podman.py`. So the allowlist is duplicated
#: here, minimally, rather than imported; keep it in sync with
#: `adapters/subprocess_env.py::NON_INTERACTIVE` by hand.
_NON_INTERACTIVE_ENV: dict[str, str] = {
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_ASKPASS": "",
    "DEBIAN_FRONTEND": "noninteractive",
    "PAGER": "cat",
    "MANPAGER": "cat",
    "PYTHONUNBUFFERED": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
}
_EVAL_ENV_BASE = {k: os.environ[k] for k in ("PATH", "HOME", "LANG") if k in os.environ}
_EVAL_ENV = {**_EVAL_ENV_BASE, **_NON_INTERACTIVE_ENV}


@runtime_checkable
class SandboxRunner(Protocol):
    """The container boundary the evaluator needs. Not a port (ADR-0005 rev. 2
    ratifies eight port areas); a structural collaborator of the TCB."""

    async def run(self, spec: ContainerSpec) -> ContainerResult: ...


def hash_command(command: str) -> str:
    return "sha256:" + hashlib.sha256(command.encode()).hexdigest()


def _worktree_path(worktrees_root: str, worktree: WorktreeRef) -> str:
    return os.path.join(worktrees_root, worktree.run_id, worktree.worktree_id)


def tail_biased(text: str, limit: int = _TAIL_CHARS) -> str:
    """Tail-biased truncation. Test output is failure-at-the-end shaped: the
    traceback is what a reader — and the repair edge (TASK-023) — needs, the
    pass list is what burns the budget. Public because the repair node feeds
    the same output into context and must not invent a second truncation
    strategy that disagrees with what the gate reported."""
    return text[-limit:]


async def _tests_unmodified(spec: EvalSpec, path: str) -> str | None:
    """None if clean; an instrument_error string if the candidate touched its judge.

    `--name-only` against the pinned base commit catches edits AND additions,
    which is why the manifest carries globs rather than a digest list. A
    subprocess, not `GitCliWorkspace`, because `aether-tcb-isolation` forbids
    this module from importing `aether.adapters` — spawning `git` is not an
    import.
    """
    if not spec.test_paths:
        return None
    proc = await asyncio.create_subprocess_exec(
        "git",
        "diff",
        "--name-only",
        spec.base_commit,
        "--",
        *spec.test_paths,
        cwd=path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        stdin=asyncio.subprocess.DEVNULL,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        # Cannot verify ⇒ cannot score. Failing open here would make the gate
        # decorative on exactly the runs where git is misbehaving.
        return f"tests_unmodified check failed: {stderr.decode(errors='replace')[:200]}"
    touched = [ln for ln in stdout.decode().splitlines() if ln.strip()]
    if touched:
        return f"candidate modified its own test files (I7): {', '.join(sorted(touched))}"
    return None


def _report_from_exit(exit_code: int, output: str) -> GateReport:
    """The single B4 mapping. Both execution modes route through it so the
    contained and uncontained paths cannot drift apart."""
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


class RealEvaluator:
    """TCB. `worktrees_root` mirrors `GitCliWorkspace`'s own convention for
    locating a worktree from `(run_id, worktree_id)` — no `Path` crosses the
    `EvalSpec` boundary (I3)."""

    def __init__(
        self,
        worktrees_root: str,
        resolve_command: Callable[[EvalSpec], str],
        sandbox: SandboxRunner | None = None,
        limits: ContainerLimits | None = None,
        layers_host_path: str | None = None,
    ) -> None:
        self._worktrees_root = worktrees_root
        self._resolve_command = resolve_command
        self._sandbox = sandbox
        self._limits = limits or ContainerLimits()
        self._layers_host_path = layers_host_path

    @property
    def is_contained(self) -> bool:
        """Whether this evaluator is the B3-isolated instrument. Read by the
        floor runner: a number taken with this False is not publishable."""
        return self._sandbox is not None

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
        tampered = await _tests_unmodified(spec, path)
        if tampered is not None:
            return GateReport(gate="tests", status=GateStatus.NONE, instrument_error=tampered)

        if self._sandbox is not None:
            return await self._evaluate_contained(spec, command, path)
        return await self._evaluate_uncontained(spec, command, path)

    async def _evaluate_contained(self, spec: EvalSpec, command: str, path: str) -> GateReport:
        assert self._sandbox is not None
        result = await self._sandbox.run(
            ContainerSpec(
                image_digest=spec.image_digest,
                command=command,
                worktree_host_path=path,
                layers_host_path=self._layers_host_path,
                timeout_ms=spec.timeout_ms,
                limits=self._limits,
            )
        )
        if result.launch_error is not None:
            return GateReport(
                gate="tests",
                status=GateStatus.NONE,
                instrument_error=f"container did not start: {result.launch_error}",
            )
        if result.timed_out:
            return GateReport(
                gate="tests",
                status=GateStatus.NONE,
                instrument_error=f"timed out after {spec.timeout_ms}ms",
            )
        return _report_from_exit(result.exit_code, tail_biased(result.stdout + result.stderr))

    async def _evaluate_uncontained(self, spec: EvalSpec, command: str, path: str) -> GateReport:
        try:
            proc = await asyncio.create_subprocess_exec(
                *shlex.split(command),
                cwd=path,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=_EVAL_ENV,
            )
        except FileNotFoundError as exc:
            return GateReport(
                gate="tests", status=GateStatus.NONE, instrument_error=f"test command not found: {exc}"
            )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=spec.timeout_ms / 1000)
        except TimeoutError:
            proc.kill()
            await proc.communicate()
            return GateReport(
                gate="tests", status=GateStatus.NONE, instrument_error=f"timed out after {spec.timeout_ms}ms"
            )

        exit_code = proc.returncode if proc.returncode is not None else -1
        return _report_from_exit(exit_code, tail_biased((stdout + stderr).decode(errors="replace")))
