"""The B3 canary (TASK-016) — *the* deliverable of Sprint 3 Task 1.

B3 is the only instrument defect in this project's history that produced
numbers: an editable install's `.pth` leaked the live `src/` tree into every
supposedly-isolated worktree, so candidate diffs were invisible to the gates
scoring them. `measurement.md` §2 therefore requires a canary asserting that
**a deliberately broken candidate fails evaluation**, run in the A/A floor
environment before the floor run. This module is that canary.

It is bidirectional on purpose. "A broken candidate fails" is vacuous on an
instrument where everything fails, so the good candidate must pass on the same
instrument, in the same container, in the same test session.

Skips when no container runtime is present; **fails hard** when
`AETHER_REQUIRE_CONTAINER=1` promised one (`tests/aether/container_support.py`).
"""

from __future__ import annotations

import asyncio
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest
from tests.aether.container_support import require_eval_image

from aether.adapters.sandbox.podman import ContainerSandbox, build_run_argv
from aether.domain.gate import GateStatus
from aether.domain.ids import RunId, TaskId
from aether.domain.sandbox import ContainerResult, ContainerSpec
from aether.domain.workspace import WorktreeRef
from aether.measurement.evaluator import RealEvaluator, hash_command
from aether.ports.evaluator import EvalSpec

pytestmark = pytest.mark.container

GOOD_CALC = "def add(a, b):\n    return a + b\n"
BROKEN_CALC = "def add(a, b):\n    return a - b\n"

RUN_TESTS = """\
import sys
from calc import add

if add(1, 2) != 3:
    print("FAIL: add(1, 2) != 3", file=sys.stderr)
    sys.exit(1)
print("ok")
sys.exit(0)
"""

TEST_COMMAND = "python3 run_tests.py"


@pytest.fixture
def instrument(tmp_path: Path):  # noqa: ANN201
    """A worktree plus the contained evaluator that will judge it."""
    runtime, digest = require_eval_image()

    worktrees_root = tmp_path / "worktrees"
    worktree_dir = worktrees_root / "run-canary" / "wt-1"
    worktree_dir.mkdir(parents=True)
    (worktree_dir / "run_tests.py").write_text(RUN_TESTS)

    worktree = WorktreeRef(
        worktree_id="wt-1",
        run_id=RunId("run-canary"),
        base_commit="0" * 40,
        abs_hint=str(worktree_dir),
    )
    evaluator = RealEvaluator(
        str(worktrees_root),
        resolve_command=lambda spec: TEST_COMMAND,
        sandbox=ContainerSandbox(runtime),
    )
    spec = EvalSpec(
        task_id=TaskId("b3-canary"),
        worktree=worktree,
        image_digest=digest,
        test_command_hash=hash_command(TEST_COMMAND),
        timeout_ms=120_000,
    )
    return worktree_dir, evaluator, spec, runtime, digest


async def test_a_good_candidate_passes(instrument) -> None:  # noqa: ANN001
    """Without this half, "the broken one fails" proves nothing."""
    worktree_dir, evaluator, spec, _runtime, _digest = instrument
    (worktree_dir / "calc.py").write_text(GOOD_CALC)

    report = await evaluator.evaluate(spec)

    assert report.status is GateStatus.PASSED, report.model_dump()


async def test_a_deliberately_broken_candidate_fails_evaluation(instrument) -> None:  # noqa: ANN001
    """**The B3 canary.** If this passes, the container is reading code from
    somewhere other than the candidate worktree and the floor is blocked."""
    worktree_dir, evaluator, spec, _runtime, _digest = instrument
    (worktree_dir / "calc.py").write_text(BROKEN_CALC)

    report = await evaluator.evaluate(spec)

    assert report.status is GateStatus.FAILED, report.model_dump()
    assert report.status is not GateStatus.PASSED


async def test_the_host_filesystem_outside_the_worktree_is_invisible(instrument, tmp_path) -> None:  # noqa: ANN001
    """The `.pth` leak's shape, probed directly: a file that exists on the host
    right next to the worktree must not exist inside the container."""
    worktree_dir, evaluator, spec, _runtime, _digest = instrument
    leaked = tmp_path / "host_only.py"
    leaked.write_text("SECRET = 1\n")

    probe = f"""\
import os, sys
sys.exit(1 if os.path.exists({str(leaked)!r}) else 0)
"""
    (worktree_dir / "run_tests.py").write_text(probe)

    report = await evaluator.evaluate(spec)

    assert report.status is GateStatus.PASSED, (
        f"host path {leaked} was visible inside the evaluation container: {report.model_dump()}"
    )


async def test_the_container_has_no_network(instrument) -> None:  # noqa: ANN001
    """`--network none`: the patch under evaluation never reaches a network.
    Model calls happen outside the sandbox, in the agent process."""
    worktree_dir, evaluator, spec, _runtime, _digest = instrument
    probe = """\
import socket, sys
try:
    socket.create_connection(("1.1.1.1", 80), timeout=3)
except OSError:
    sys.exit(0)          # egress refused — the perimeter holds
sys.exit(1)              # egress succeeded — the perimeter does not
"""
    (worktree_dir / "run_tests.py").write_text(probe)

    report = await evaluator.evaluate(spec)

    assert report.status is GateStatus.PASSED, f"egress succeeded from the container: {report.detail}"


class _WeakenedSandbox:
    """A sandbox with one clause of the perimeter deliberately removed.

    The house rule (`vision.md` §4) is that every gate ships with a test
    proving it can fail — applied here to the canary itself. Without this,
    "the broken candidate failed" and "the probes are green" could both be
    artefacts of a container that never ran what we think it ran. This class
    exists only in the test tree: production `ContainerSandbox` has no hook
    for weakening the argv, by design (there is no `--force`).
    """

    def __init__(self, runtime: str, transform: Callable[[list[str]], list[str]]) -> None:
        self._runtime = runtime
        self._transform = transform

    async def run(self, spec: ContainerSpec) -> ContainerResult:
        argv = self._transform(build_run_argv(spec, self._runtime))
        proc = await asyncio.create_subprocess_exec(
            *argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        return ContainerResult(
            exit_code=proc.returncode if proc.returncode is not None else -1,
            stdout=stdout.decode(errors="replace"),
            stderr=stderr.decode(errors="replace"),
            argv=tuple(argv),
        )


def _add_third_mount(host_path: str, container_path: str) -> Callable[[list[str]], list[str]]:
    """Splice a third `--volume` in immediately before the image reference —
    everything after it is the container's argv, not runtime flags."""

    def transform(argv: list[str]) -> list[str]:
        image_idx = next(i for i, token in enumerate(argv) if token.startswith("sha256:"))
        return [
            *argv[:image_idx],
            "--volume",
            f"{host_path}:{container_path}:ro",
            *argv[image_idx:],
        ]

    return transform


def _drop_network_none(argv: list[str]) -> list[str]:
    out = list(argv)
    idx = out.index("--network")
    del out[idx : idx + 2]
    return out


async def test_the_leak_probe_can_fail_when_a_third_mount_is_added(instrument, tmp_path) -> None:  # noqa: ANN001
    """Negative test for the host-visibility canary: add a third host mount —
    exactly the shape of the `.pth` leak, a second path for host code to
    arrive on — and the probe must go red."""
    worktree_dir, _evaluator, spec, runtime, _digest = instrument
    # World-readable on purpose: `tmp_path` itself is 0700, and a container
    # that fails to read it would make this test green for a reason that has
    # nothing to do with mounts. The variable under test is the mount.
    host_side = tmp_path / "host_side"
    host_side.mkdir(mode=0o755)
    (host_side / "host_only.py").write_text("SECRET = 1\n")
    (host_side / "host_only.py").chmod(0o644)
    (worktree_dir / "run_tests.py").write_text(
        f"import os, sys\nsys.exit(1 if os.path.exists({'/leak/host_only.py'!r}) else 0)\n"
    )

    leaky = RealEvaluator(
        str(tmp_path / "worktrees"),
        resolve_command=lambda s: TEST_COMMAND,
        sandbox=_WeakenedSandbox(runtime, _add_third_mount(str(host_side), "/leak")),
    )

    report = await leaky.evaluate(spec)

    assert report.status is GateStatus.FAILED, (
        "the host-visibility probe stayed green with a third host mount present — "
        f"it cannot detect the defect it exists for: {report.model_dump()}"
    )


async def test_the_network_probe_can_fail_when_network_none_is_removed(instrument, tmp_path) -> None:  # noqa: ANN001
    """Negative test for the egress canary. Skips (does not fail) when the
    host itself has no egress — an unreachable internet makes the probe
    unfalsifiable here, and recording that is honest; claiming a green
    perimeter from it would not be."""
    worktree_dir, _evaluator, spec, runtime, _digest = instrument
    (worktree_dir / "run_tests.py").write_text(
        "import socket, sys\n"
        "try:\n"
        '    socket.create_connection(("1.1.1.1", 80), timeout=5)\n'
        "except OSError:\n"
        "    sys.exit(0)\n"
        "sys.exit(1)\n"
    )

    open_net = RealEvaluator(
        str(tmp_path / "worktrees"),
        resolve_command=lambda s: TEST_COMMAND,
        sandbox=_WeakenedSandbox(runtime, _drop_network_none),
    )

    report = await open_net.evaluate(spec)

    if report.status is GateStatus.PASSED:
        pytest.skip("host has no egress to 1.1.1.1:80 — the network probe is unfalsifiable here")
    assert report.status is GateStatus.FAILED, report.model_dump()


def test_the_image_is_referenced_by_digest_not_tag(instrument) -> None:  # noqa: ANN001
    """The digest the canary just ran under is a real, resolvable one — the
    argv-level rule is enforced in tests/aether/adapters/test_sandbox_argv.py."""
    _worktree_dir, _evaluator, spec, runtime, digest = instrument
    assert digest.startswith("sha256:")
    resolved = subprocess.run(
        [runtime, "image", "inspect", "-f", "{{.Id}}", digest], capture_output=True, text=True
    )
    assert resolved.returncode == 0, resolved.stderr
