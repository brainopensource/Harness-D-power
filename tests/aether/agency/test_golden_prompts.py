"""Golden-prompt equivalence (T5, `TASK-057`) — the entire safety argument for
deleting `workflow/nodes/{architect,generate,repair}.py`.

Every shipped topology must produce byte-identical prompts before and after
`ModelNode` replaces the three node classes it consolidates. `T0`
(`scripts/gen_prompt_replay.py`) recorded the *before* image against today's
node classes into `tests/fixtures/aether_prompt_replay/`; this test re-runs
the same recorder and diffs the result against that fixture.

This file is intentionally the *same* comparison the script's own `--check`
mode makes — duplicated here so it runs under the standing `pytest` suite and
so CI fails a named test, not a script's exit code, when a prompt drifts.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from gen_prompt_replay import (  # noqa: E402
    FIXTURE_ROOT,
    WORKFLOWS_DIR,
    _diff,
    _read_existing,
    _record_topology,
    _topology_hash,
)


async def _record_all_for_test() -> dict[str, object]:
    manifest: dict[str, object] = {"recorder_version": "1", "topologies": {}}
    fixtures: dict[str, list[dict[str, object]]] = {}
    for path in sorted(WORKFLOWS_DIR.glob("*.yaml")):
        calls = await _record_topology(path)
        manifest["topologies"][path.stem] = {  # type: ignore[index]
            "topology_hash": _topology_hash(path),
            "prompt_count": len(calls),
        }
        fixtures[path.stem] = calls
    return {"manifest": manifest, "fixtures": fixtures}


async def test_every_shipped_topology_produces_the_recorded_prompt() -> None:
    """Byte-identical wire form, per topology, per model node.

    Fails the moment a node's system text, layer ordering, or provenance
    label changes without a reviewed `--update` of the fixture — which is
    exactly the silent-drift risk `sprint-05.md` Task 5 names as the reason
    this is the gate, not unit coverage.
    """
    existing = _read_existing()
    assert existing is not None, (
        "no recorded prompts under tests/fixtures/aether_prompt_replay/ — "
        "run `uv run python scripts/gen_prompt_replay.py --update` first (T0)"
    )
    recorded = await _record_all_for_test()
    problems = _diff(existing, recorded)
    assert not problems, "prompt drift detected:\n" + "\n".join(f"  - {p}" for p in problems)


async def test_the_fixture_covers_every_shipped_topology() -> None:
    """A fixture missing a topology would make the equivalence test vacuous
    for that file — the same "a contract that selects nothing forbids
    nothing" failure mode this project keeps finding elsewhere."""
    existing = _read_existing()
    assert existing is not None
    shipped = {p.stem for p in WORKFLOWS_DIR.glob("*.yaml")}
    assert shipped == set(existing["fixtures"]), (
        f"fixture/topology mismatch: missing={shipped - set(existing['fixtures'])} "
        f"extra={set(existing['fixtures']) - shipped}"
    )


def test_fixture_root_is_not_accidentally_empty() -> None:
    """A gate that cannot fail is not counted as a gate (measurement.md §5) —
    guard against the fixture directory existing but holding nothing."""
    assert FIXTURE_ROOT.exists()
    assert any(FIXTURE_ROOT.iterdir()), f"{FIXTURE_ROOT} exists but is empty"
