"""Non-interactive subprocess environment (`TASK-062`).

An **allowlist**, not a copy of `os.environ`. An evaluation whose behaviour
can depend on the launching shell's environment cannot name its instrument
(`measurement.md` §6) — a benchmark run started from a developer's shell with
`OPENROUTER_API_KEY`, a personal `GIT_ASKPASS` helper, or a paging pager
configured for a terminal would silently vary the environment a candidate's
subprocess sees between two runs the harness otherwise treats as identical.

`CI=1` is deliberately absent here. It changes what test suites *do* — some
skip, some enable strict mode, some change output format — so it is part of
the *evaluation environment*, not spawn hygiene, and belongs in the
container's `--env` allowlist (`adapters/sandbox/podman.py`) as a declared,
pinned value instead.
"""

from __future__ import annotations

import os
from collections.abc import Mapping

NON_INTERACTIVE: dict[str, str] = {
    "GIT_TERMINAL_PROMPT": "0",  # git fails instead of prompting
    "GIT_ASKPASS": "",  # and does not fall back to an askpass helper
    "DEBIAN_FRONTEND": "noninteractive",
    "PAGER": "cat",
    "MANPAGER": "cat",  # git and pydoc read MANPAGER before PAGER
    "PYTHONUNBUFFERED": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
}


def spawn_env(*, extra: Mapping[str, str] = {}) -> dict[str, str]:
    """An ALLOWLIST, not a copy of os.environ."""
    base = {k: os.environ[k] for k in ("PATH", "HOME", "LANG") if k in os.environ}
    return {**base, **NON_INTERACTIVE, **extra}
