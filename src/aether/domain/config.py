"""Named deviations from the pre-registered baseline (TASK-049b, measurement.md §4.1).

Scope discipline: `AblationFlags` only. The full `RunConfig` is `TASK-058`,
Sprint 5 — this module must not grow beyond this one type this sprint.
"""

from __future__ import annotations

import hashlib
import json

from aether.domain.ids import Frozen


class AblationFlags(Frozen):
    """Every field defaults to the pre-registered baseline. A run that
    deviates says so in its own config hash, which is what makes it a
    declared *arm* rather than a contaminated run."""

    #: Baseline is `False`: "no retrieval beyond benchmark-provided context."
    #: `True` embeds the pinned test file's full text in the task prompt —
    #: measuring assertion-fitting, not bug-fixing (measurement.md §4.1).
    inject_test_source: bool = False


def config_hash(flags: AblationFlags) -> str:
    """Same convention as `measurement/manifest.py::canonical_json` — sorted
    keys, no whitespace, so the hash is reproducible across processes."""
    canonical = json.dumps(flags.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()


__all__ = ["AblationFlags", "config_hash"]
