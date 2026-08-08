"""B3 isolation contract as a unit test over the command line (TASK-016).

`build_run_argv` is pure so every clause of tech_stack_and_infra.md §3.1 is
checkable on a machine with no container runtime — the shape of the command
line *is* the perimeter, and a perimeter only enforced where Podman happens to
be installed is the M-2 defect wearing a different hat. The canary that runs a
real container lives in `tests/integration/test_b3_canary.py`.
"""

from __future__ import annotations

import pytest

from aether.adapters.sandbox.podman import (
    ImageNotPinnedError,
    build_run_argv,
    is_digest_reference,
)
from aether.domain.sandbox import ContainerLimits, ContainerSpec

DIGEST = "sha256:" + "a" * 64


def _spec(**overrides: object) -> ContainerSpec:
    base: dict[str, object] = {
        "image_digest": DIGEST,
        "command": "python3 -m pytest -q",
        "worktree_host_path": "/run/worktrees/run-1/wt-1",
        "timeout_ms": 60_000,
    }
    base.update(overrides)
    return ContainerSpec(**base)  # type: ignore[arg-type]


def _flag_values(argv: list[str], flag: str) -> list[str]:
    return [argv[i + 1] for i, token in enumerate(argv[:-1]) if token == flag]


def test_network_is_none() -> None:
    argv = build_run_argv(_spec())
    assert _flag_values(argv, "--network") == ["none"]


def test_all_capabilities_dropped_and_no_new_privileges() -> None:
    argv = build_run_argv(_spec())
    assert _flag_values(argv, "--cap-drop") == ["all"]
    assert "no-new-privileges" in _flag_values(argv, "--security-opt")


def test_root_filesystem_is_read_only_and_pids_are_bounded() -> None:
    argv = build_run_argv(_spec(limits=ContainerLimits(pids_limit=128)))
    assert "--read-only" in argv
    assert _flag_values(argv, "--pids-limit") == ["128"]


def test_memory_and_cpu_limits_are_applied() -> None:
    argv = build_run_argv(_spec(limits=ContainerLimits(memory_mb=512, cpu_millicores=1500)))
    assert _flag_values(argv, "--memory") == ["512m"]
    assert _flag_values(argv, "--cpus") == ["1.500"]


def test_exactly_two_mounts_and_no_others() -> None:
    """The `.pth` leak is fixed by construction: there is no third host path
    for host code to arrive on. No home, no sockets, no repo root."""
    argv = build_run_argv(_spec(worktree_host_path="/wt", layers_host_path="/layers"), runtime="podman")
    mounts = _flag_values(argv, "--volume")
    assert mounts == ["/wt:/workspace:rw", "/layers:/opt/aether/layers:ro"]
    assert not _flag_values(argv, "--mount")


def test_only_one_mount_when_no_layers_are_pinned() -> None:
    argv = build_run_argv(_spec())
    assert _flag_values(argv, "--volume") == ["/run/worktrees/run-1/wt-1:/workspace:rw"]


def test_tmpfs_is_not_a_host_mount() -> None:
    """A read-only root needs writable scratch; `--tmpfs` is in-memory and
    host-invisible, so it does not widen the two-mount contract."""
    argv = build_run_argv(_spec())
    assert any(v.startswith("/tmp:") for v in _flag_values(argv, "--tmpfs"))


@pytest.mark.parametrize(
    "image",
    [
        "python:3.13-slim",
        "aether/eval:latest",
        "aether/eval",
        "sha256:tooshort",
        "sha256:" + "A" * 64,  # uppercase hex is not a digest we emit
    ],
)
def test_a_tag_is_refused(image: str) -> None:
    """The negative test the gate needs: this check can fail, and there is no
    `--force`. A tag is a mutable pointer to an environment."""
    assert not is_digest_reference(image)
    with pytest.raises(ImageNotPinnedError):
        build_run_argv(_spec(image_digest=image))


@pytest.mark.parametrize(
    "image",
    ["sha256:" + "0" * 64, "ghcr.io/aether/eval@sha256:" + "f" * 64],
)
def test_digest_references_are_accepted(image: str) -> None:
    assert is_digest_reference(image)
    argv = build_run_argv(_spec(image_digest=image))
    assert image in argv


def test_docker_fallback_drops_the_podman_only_userns_flag() -> None:
    podman_argv = build_run_argv(_spec(), runtime="podman")
    docker_argv = build_run_argv(_spec(), runtime="docker")
    assert "--userns=keep-id" in podman_argv
    assert "--userns=keep-id" not in docker_argv
    # Everything else about the perimeter is identical.
    assert [t for t in podman_argv if t != "--userns=keep-id"][1:] == docker_argv[1:]


def test_command_is_argv_not_a_shell_string() -> None:
    argv = build_run_argv(_spec(command="python3 -m pytest -q tests/x.py"))
    assert argv[-4:] == ["python3", "-m", "pytest", "-q", "tests/x.py"][-4:]
    assert "sh" not in argv
