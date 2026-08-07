"""Event-catalog drift check (TASK-022, spec.md §8): the generated doc must
match `aether.domain.events.EVENT_TYPES` — a hand-edited doc is a stale doc."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_aether_event_catalog_is_up_to_date() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "gen_aether_event_catalog.py"), "--check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_event_types_all_use_kind_discriminator() -> None:
    from aether.domain.events import EVENT_TYPES

    for event_cls in EVENT_TYPES:
        assert "kind" in event_cls.model_fields
        assert "run_id" in event_cls.model_fields
        assert "at" in event_cls.model_fields
