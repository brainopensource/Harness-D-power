"""Evaluation container adapter (TASK-016, Blocker B3).

B3 is the one instrument defect in this project's history that *produced
numbers*: an editable install's `.pth` file leaked the live `src/` tree into
every supposedly-isolated worktree, so candidate diffs were invisible to the
gates scoring them. The fix is not "remember to avoid it" — it is a container
with **exactly two host mounts**, so there is no third path for host code to
arrive on.

The isolation contract (tech_stack_and_infra.md §3.1), each item a gate:

| Property | Flag |
| No network | `--network none` |
| No privilege | `--cap-drop all`, `--security-opt no-new-privileges`, `--read-only`, `--pids-limit` |
| No host filesystem | exactly two `--volume` flags: worktree RW, pinned layers RO |
| Deterministic env | image referenced **by digest, never by tag** |

`--tmpfs /tmp` is not a third mount: it is an empty, in-memory, host-invisible
filesystem, and a read-only root is unusable for a test runner without one.
`build_run_argv` is a pure function precisely so the contract above is
testable on a machine with no container runtime at all — the shape of the
command line is the gate, and it must be checkable in ordinary CI.

Runtime: rootless **Podman** is the ratified runner. `runtime="docker"` is the
documented one-flag fallback for Docker-only environments; it drops
`--userns=keep-id` (a Podman-only rootless flag) and nothing else.
"""

from __future__ import annotations

import asyncio
import re
import shlex
import shutil

from aether.domain.sandbox import CONTAINER_LAYERS, CONTAINER_WORKSPACE, ContainerResult, ContainerSpec

Runtime = str  # "podman" | "docker"

#: A digest reference is either a bare image ID (`sha256:<64 hex>`) or a
#: repository pinned by manifest digest (`repo/name@sha256:<64 hex>`). A tag —
#: `python:3.13-slim`, `aether/eval:latest` — is refused: a tag is a mutable
#: pointer, and an evaluation whose environment can be re-pointed under it is
#: not reproducible (measurement.md §6).
_DIGEST_RE = re.compile(r"^(?:[A-Za-z0-9][\w.\-/:]*@)?sha256:[0-9a-f]{64}$")


class ImageNotPinnedError(ValueError):
    """Raised when an image reference is not digest-pinned. No `--force`."""


def is_digest_reference(image: str) -> bool:
    return bool(_DIGEST_RE.match(image))


def runtime_available(runtime: Runtime = "podman") -> bool:
    return shutil.which(runtime) is not None


def build_run_argv(spec: ContainerSpec, runtime: Runtime = "podman") -> list[str]:
    """The exact command line for one evaluation. Pure — no I/O, no runtime
    required — so every clause of the isolation contract is unit-testable."""
    if not is_digest_reference(spec.image_digest):
        raise ImageNotPinnedError(
            f"image must be digest-pinned (sha256:… or repo@sha256:…), got {spec.image_digest!r}. "
            "Containers are created from digests, never tags (measurement.md §2 B3)."
        )

    argv: list[str] = [
        runtime,
        "run",
        "--rm",
        "--network",
        "none",
        "--cap-drop",
        "all",
        "--security-opt",
        "no-new-privileges",
        "--read-only",
        "--pids-limit",
        str(spec.limits.pids_limit),
        "--memory",
        f"{spec.limits.memory_mb}m",
        "--cpus",
        _cpus(spec.limits.cpu_millicores),
    ]
    if runtime == "podman":
        # Rootless uid/gid mapping so the RW worktree mount stays writable by
        # the invoking user. Docker has no equivalent for this rootless case.
        argv += ["--userns=keep-id"]

    argv += [
        # Writable scratch that is *not* a host mount: empty at start, gone at
        # exit, invisible to the host. Read-only root would otherwise fail
        # every test runner that touches a temp file.
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=256m",
        "--env",
        "TMPDIR=/tmp",
        # No .pyc writes into a read-only tree; also keeps the worktree clean
        # so `git diff` in the worktree stays the candidate's diff alone.
        "--env",
        "PYTHONDONTWRITEBYTECODE=1",
        "--workdir",
        spec.workdir,
        # Mount 1 of 2: the candidate worktree, read-write.
        "--volume",
        f"{spec.worktree_host_path}:{CONTAINER_WORKSPACE}:rw",
    ]
    if spec.layers_host_path is not None:
        # Mount 2 of 2: pinned image layers, read-only. There is no third.
        argv += ["--volume", f"{spec.layers_host_path}:{CONTAINER_LAYERS}:ro"]

    argv += [spec.image_digest, *shlex.split(spec.command)]
    return argv


def _cpus(millicores: int) -> str:
    """Integer millicores in, CLI-shaped decimal out. Budget arithmetic stays
    integer-only (I3); the float exists only in the argv string."""
    whole, frac = divmod(max(millicores, 1), 1000)
    return f"{whole}.{frac:03d}"


class ContainerSandbox:
    """Runs one evaluation per `run()` call, in a fresh disposable container.

    Structurally satisfies `measurement.evaluator.SandboxRunner`; it does not
    import it. `aether-tcb-isolation` forbids the evaluator from importing
    `aether.adapters`, and `aether-layers` forbids the reverse — a structural
    Protocol is what lets the TCB depend on this behaviour without either
    module importing the other.
    """

    def __init__(self, runtime: Runtime = "podman") -> None:
        self._runtime = runtime

    @property
    def runtime(self) -> Runtime:
        return self._runtime

    async def run(self, spec: ContainerSpec) -> ContainerResult:
        try:
            argv = build_run_argv(spec, self._runtime)
        except ImageNotPinnedError as exc:
            return ContainerResult(launch_error=str(exc))

        try:
            proc = await asyncio.create_subprocess_exec(
                *argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
        except FileNotFoundError as exc:
            return ContainerResult(
                launch_error=f"container runtime {self._runtime!r} not on PATH: {exc}",
                argv=tuple(argv),
            )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=spec.timeout_ms / 1000)
        except TimeoutError:
            proc.kill()
            await proc.communicate()
            return ContainerResult(timed_out=True, argv=tuple(argv))

        return ContainerResult(
            exit_code=proc.returncode if proc.returncode is not None else -1,
            stdout=stdout.decode(errors="replace"),
            stderr=stderr.decode(errors="replace"),
            argv=tuple(argv),
        )


__all__ = [
    "ContainerSandbox",
    "ImageNotPinnedError",
    "build_run_argv",
    "is_digest_reference",
    "runtime_available",
]
