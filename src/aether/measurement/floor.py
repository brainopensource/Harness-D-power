"""`FloorNotPublished` & `published_floor()` — the holdout guard (T6, `TASK-058`).

Prevents holdout or sealed benchmark runs from executing before an A/A noise
floor has been measured and published (ADR-0002).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FLOOR_ARTIFACT = Path("docs/benchmarks/results/noise-floor.json")


class FloorNotPublished(RuntimeError):
    """A holdout or sealed run was requested while no A/A floor exists.

    ADR-0002, reversal conditions: none. Enforced in the engine and not in a
    client, because a config layer that makes runs easy to launch makes
    premature runs equally easy.
    """


def published_floor(repo_root: Path) -> dict[str, Any] | None:
    """Reads the A/A noise floor JSON artifact if it exists."""
    path = repo_root / FLOOR_ARTIFACT
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


__all__ = ["FLOOR_ARTIFACT", "FloorNotPublished", "published_floor"]
