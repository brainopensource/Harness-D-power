"""Container availability gate for the B3 canary (TASK-016).

Direct descendant of `tests/podman_support.py`'s hard-fail-if-promised
pattern, and of the defect that produced it: a perimeter test that *skips*
when the runtime is absent reports a green perimeter that was never tested.
Skipping locally is fine; skipping on a runner that promised a container
runtime is the same class of bug as a contract selecting zero modules.

Set `AETHER_REQUIRE_CONTAINER=1` — as the B3 perimeter job and the A/A floor
environment do — and an absent runtime or an unbuildable image becomes a hard
failure instead of a skip.
"""

from __future__ import annotations

import os
import subprocess

import pytest

from aether.adapters.sandbox.podman import runtime_available

EVAL_TAG = "aether/eval:build"
BUILD_HINT = "python3 scripts/build_eval_image.py --runtime {runtime}   # builds and prints the digest"


def detect_runtime() -> str | None:
    """Podman is the ratified runner; Docker is the documented one-flag
    fallback (tech_stack_and_infra.md §3)."""
    for runtime in ("podman", "docker"):
        if runtime_available(runtime):
            return runtime
    return None


def image_digest(runtime: str, tag: str = EVAL_TAG) -> str | None:
    result = subprocess.run(
        [runtime, "image", "inspect", "-f", "{{.Id}}", tag], capture_output=True, text=True
    )
    if result.returncode != 0:
        return None
    digest = result.stdout.strip()
    if digest and not digest.startswith("sha256:"):
        digest = f"sha256:{digest}"
    return digest or None


def require_eval_image() -> tuple[str, str]:
    """Return `(runtime, image_digest)` or skip — unless the environment
    promised a container runtime, in which case fail loudly."""
    runtime = detect_runtime()
    digest = image_digest(runtime) if runtime else None

    if runtime is not None and digest is not None:
        return runtime, digest

    reason = (
        f"container runtime + {EVAL_TAG} required "
        f"(runtime={runtime or 'absent'}, image={'absent' if digest is None else 'present'})"
    )
    if os.environ.get("AETHER_REQUIRE_CONTAINER") == "1":
        pytest.fail(
            f"AETHER_REQUIRE_CONTAINER=1 but {reason}. This environment is supposed to enforce "
            f"the B3 perimeter; skipping here would report an isolated evaluator that was never "
            f"isolated (measurement.md §2 B3). Build it with: "
            + BUILD_HINT.format(runtime=runtime or "podman")
        )
    pytest.skip(reason)
