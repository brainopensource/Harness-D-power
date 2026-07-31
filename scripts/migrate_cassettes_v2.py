#!/usr/bin/env python3
"""Migrate cassette JSON files to v2 format with usage and model fields.

See refactor_sagiha_v2_guidelines.md §5 PR-1.2.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

DEFAULT_CASSETTES = (
    Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "replay_smoke" / "cassette.json",
)


def migrate_file(path: Path) -> bool:
    if not path.exists():
        print(f"Skipping missing cassette: {path}")
        return False

    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    modified = False

    for entry in data:
        if "usage" not in entry or entry["usage"] is None:
            entry["usage"] = {"input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0}
            modified = True
        if "model" not in entry or entry["model"] is None:
            entry["model"] = "cassette"
            modified = True

    if modified:
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"Migrated cassette to v2: {path}")
        return True
    else:
        print(f"Already v2 compliant: {path}")
        return False


def main() -> int:
    targets = [Path(arg) for arg in sys.argv[1:]] if len(sys.argv) > 1 else list(DEFAULT_CASSETTES)
    migrated_count = 0
    for target in targets:
        if migrate_file(target):
            migrated_count += 1
    print(f"Done. Migrated {migrated_count} cassette(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
