"""Per-invocation effect classification allowlist.

See docs/08-decisions/0020-per-invocation-effect-classification.md.

Lives in `kernel/policy` deliberately: the `tcb-isolation` import contract already forbids this
package from importing `agency`, `aoi`, or `adapters`, and CI's `tcb-check` already hard-fails an
agent-authored diff touching `kernel/policy/**`. Placement here makes the allowlist
agent-unwritable for free — no new gate, no new CI job, no new concept.

`classify_command` NEVER widens a declared effect. It narrows `DESTRUCTIVE` to `PURE` for
allowlisted read-only argv, or returns `declared` unchanged. `bash -lc` is never narrowed: the
argv of a shell invocation says nothing about what the shell will do.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from sagiha.domain.content import EffectClass

#: Binaries whose invocations MAY be pure, subject to further narrowing below.
PURE_ARGV: Final[frozenset[str]] = frozenset({"ls", "cat", "head", "tail", "wc", "git"})

#: `git` subcommands that are read-only. `git` itself is not blanket-pure — `git commit`,
#: `git push`, `git checkout` all mutate — so `git` requires this second check.
PURE_GIT_OPS: Final[frozenset[str]] = frozenset({"status", "diff", "log", "show", "blame"})

#: Tools whose declared effect this classifier is meaningfully invoked for.
MUTATION_TOOLS: Final[frozenset[str]] = frozenset({"apply_edit", "write_file", "run_command"})


def classify_command(argv: Sequence[str], declared: EffectClass) -> EffectClass:
    """Narrow a declared `DESTRUCTIVE` to `PURE` for allowlisted read-only argv.

    Never widens: anything not matched, or already narrower than `DESTRUCTIVE`, keeps
    `declared` unchanged.
    """
    if declared is not EffectClass.DESTRUCTIVE:
        return declared
    if not argv:
        return declared

    binary = argv[0]
    if binary not in PURE_ARGV:
        return declared

    if binary == "git":
        if len(argv) < 2 or argv[1] not in PURE_GIT_OPS:
            return declared

    return EffectClass.PURE
