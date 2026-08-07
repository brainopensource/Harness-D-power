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


def test_every_declared_event_has_a_producer() -> None:
    """A catalog entry nothing emits is a contract no client can ever satisfy.

    Sprint 3.5 found three of eight in exactly that state — `EffectDispatched`,
    `GateReportEmitted` and `BudgetOverrunEmitted` were declared, documented,
    generated into the catalog, and emitted nowhere. The drift check above
    compares the *doc* to the code; this compares the code to *reality*.

    Deliberately a source scan rather than a runtime trace: an event emitted
    only on a path no test exercises would still pass a runtime check that
    happened not to hit it, and the failure mode here is "nobody wrote the
    emit", which is visible statically.
    """
    from aether.domain.events import EVENT_TYPES

    src = REPO_ROOT / "src" / "aether"
    sources = {
        path: path.read_text(encoding="utf-8")
        for path in src.rglob("*.py")
        if path.name != "events.py"
    }

    unproduced: list[str] = []
    for event_cls in EVENT_TYPES:
        name = event_cls.__name__
        if not any(f"{name}(" in text for text in sources.values()):
            unproduced.append(name)

    assert not unproduced, (
        f"declared in domain/events.py but emitted by nothing: {unproduced}. "
        "Either emit it where it happens or delete it from EVENT_TYPES — a catalog "
        "that advertises an event no client can receive is a contract with no producer."
    )
