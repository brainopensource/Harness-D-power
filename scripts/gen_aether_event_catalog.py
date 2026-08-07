#!/usr/bin/env python3
"""Generate docs/architecture/generated/aether_event_catalog.md from
aether.domain.events.EVENT_TYPES.

A hand-maintained event registry drifts from the code within a sprint (the
sagiha predecessor's own `scripts/gen_event_catalog.py` exists for the same
reason) — this generates the doc from the single source of truth instead.

Usage:
    python scripts/gen_aether_event_catalog.py          # write the file
    python scripts/gen_aether_event_catalog.py --check  # exit 1 if stale (CI)
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = REPO_ROOT / "docs" / "architecture" / "generated" / "aether_event_catalog.md"

sys.path.insert(0, str(REPO_ROOT / "src"))

from aether.domain.events import EVENT_TYPES  # noqa: E402

_HEADER = """---
status: normative
updated: 2026-08-07
---

# AETHER Event Catalog

> [!IMPORTANT]
> **This file is generated** from `src/aether/domain/events.py` by
> `scripts/gen_aether_event_catalog.py`, drift-checked in CI with `--check`.
> Edit the Python, not this file.

Events never schedule nodes (spec.md §8) — this catalog is an observational
record the trajectory store, TUI, and future clients consume; it is not a
control-flow mechanism.

| Event | Payload |
| :--- | :--- |
"""


def _payload_fields(event_cls: type) -> str:
    base = {"kind", "run_id", "at"}
    names = [name for name in event_cls.model_fields if name not in base]
    if not names:
        return "—"
    return ", ".join(f"`{name}`" for name in names)


def render() -> str:
    lines = [_HEADER.rstrip("\n")]
    for event_cls in EVENT_TYPES:
        kind = event_cls.model_fields["kind"].default
        lines.append(f"| `{kind}` | {_payload_fields(event_cls)} |")
    lines.append("")
    return "\n".join(lines) + "\n"


def _normalize_for_check(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.startswith("updated:"))


def main() -> int:
    rendered = render()
    if "--check" in sys.argv:
        current = OUTPUT_PATH.read_text() if OUTPUT_PATH.exists() else ""
        if _normalize_for_check(current) != _normalize_for_check(rendered):
            print(f"{OUTPUT_PATH} is stale — run scripts/gen_aether_event_catalog.py", file=sys.stderr)
            return 1
        print(f"{OUTPUT_PATH} is up to date ({len(EVENT_TYPES)} events)")
        return 0

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(rendered)
    print(f"wrote {OUTPUT_PATH} ({len(EVENT_TYPES)} events)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
