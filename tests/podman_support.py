"""Shared Podman availability gate for `@pytest.mark.podman` suites.

The M-2 defect is a perimeter that is enforced nowhere: the eleven container
tests pass locally and no CI job runs them. Half of that defect is the missing
job; the other half is that these tests **skip** when Podman is absent, so a
misconfigured runner would report green while testing nothing. A perimeter test
that silently skips is an unenforced perimeter wearing a green checkmark.

Set `SAGIHA_REQUIRE_PODMAN=1` — as the CI perimeter job does — and an absent
Podman or a missing runtime image becomes a hard failure instead.
"""

from __future__ import annotations

import os
import subprocess

import pytest

from sagiha.adapters.sandbox.container import podman_available

RUNTIME_IMAGE = "sagiha/runtime:latest"


def podman_ready() -> bool:
    """Whether rootless Podman *and* the runtime image are both present."""
    if not podman_available():
        return False
    return subprocess.run(["podman", "image", "exists", RUNTIME_IMAGE], capture_output=True).returncode == 0


def require_podman() -> None:
    """Skip locally, but fail hard when the environment promised Podman."""
    if podman_ready():
        return

    reason = f"podman + {RUNTIME_IMAGE} required"
    if os.environ.get("SAGIHA_REQUIRE_PODMAN") == "1":
        pytest.fail(
            f"SAGIHA_REQUIRE_PODMAN=1 but {reason}. This runner is supposed to enforce the "
            f"container perimeter; skipping here would report a green perimeter that was "
            f"never tested (defect M-2). Build the image with: podman build -t "
            f"{RUNTIME_IMAGE} -f containers/runtime/Containerfile containers/runtime"
        )
    pytest.skip(reason)
