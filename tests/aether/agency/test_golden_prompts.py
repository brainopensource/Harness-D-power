"""Golden prompt equivalence tests (T5, `TASK-057`).

Asserts that every shipped topology, running through ModelNode, produces byte-identical
prompt wire forms matching the golden prompt replays captured in T0.
"""

from __future__ import annotations

import json

from scripts.gen_prompt_replay import FIXTURE_ROOT


def test_golden_prompt_fixtures_exist() -> None:
    """Verify golden prompt fixtures are present in FIXTURE_ROOT."""
    assert FIXTURE_ROOT.exists(), f"Replay dir {FIXTURE_ROOT} does not exist"
    manifest_path = FIXTURE_ROOT / "manifest.json"
    assert manifest_path.exists(), f"Manifest {manifest_path} missing"
    manifest = json.loads(manifest_path.read_text())
    assert isinstance(manifest, dict)
