"""Regenerate the checked-in CI replay fixture (D28).

`sagiha replay <run_id> --verify` needs a committed cassette whose recorded
request digest matches exactly what `RunLoop` assembles for the trivial
"replay verification" task the CLI's `replay` command runs — same system
prompt default, same `kernel.tool_schemas`, same task/checks. Hand-writing
that JSON would drift the moment prompt assembly changes; this script builds
it through the real code path instead, the same way
`tests/unit/test_sprint3a_e2e.py` records its cassette.

Run after any change to `RunLoop` defaults, `composition.build_kernel`
tool schemas, or the CLI's `replay` command:

    uv run python scripts/gen_replay_fixture.py
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from pathlib import Path

from sagiha.adapters.model.cassette import CassetteEntry, request_digest
from sagiha.agency.run_loop import RunLoop, make_task
from sagiha.composition import build_kernel
from sagiha.domain.config import Config, ModelConfig, TelemetryConfig, WorkspaceConfig
from sagiha.domain.content import Message, ModelRequest, TextBlock
from sagiha.domain.control import RunContext
from sagiha.domain.trajectory import StreamEvent

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "replay_smoke"


class _StopImmediately:
    """Scripted provider: one turn, no tool calls — the CLI replay smoke needs
    only to prove the cassette replays deterministically, not to exercise a
    tool. `tests/unit/test_sprint3a_e2e.py` is the authoritative proof that a
    cassette-driven tool call clears the dispatch choke point and the gate."""

    def __init__(self) -> None:
        self.recorded: list[tuple[ModelRequest, Message]] = []

    async def complete(self, request: ModelRequest) -> Message:
        msg = Message(role="assistant", content=[TextBlock(text="Nothing to do.")])
        self.recorded.append((request, msg))
        return msg

    async def stream(self, request: ModelRequest) -> AsyncIterator[StreamEvent]:
        raise NotImplementedError
        yield  # pragma: no cover


async def main() -> None:
    workspace = FIXTURE_DIR / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    cassette_path = FIXTURE_DIR / "cassette.json"
    trajectory_db = FIXTURE_DIR / "traj.db"
    trajectory_db.unlink(missing_ok=True)
    cassette_path.write_text("[]", encoding="utf-8")

    config = Config(
        model=ModelConfig(mode="replay"),
        workspace=WorkspaceConfig(root=str(workspace)),
        telemetry=TelemetryConfig(trajectory_db=str(trajectory_db)),
    )
    kernel = build_kernel(config, cassette_path=str(cassette_path))
    scripted = _StopImmediately()
    loop = RunLoop(
        model_provider=scripted,  # type: ignore[arg-type]
        policy_engine=kernel.policy_engine,
        resource_governor=kernel.resource_governor,
        tool_registry=kernel.tool_registry,
        trajectory_store=kernel.trajectory_store,
        bus=kernel.bus,
        tool_schemas=list(kernel.tool_schemas),
    )
    ctx = RunContext(
        run_id="fixture-gen",
        autonomy_level="interactive",
        workspace_root=str(workspace),
        budget_remaining_usd=config.governor.max_spend_usd_per_run,
    )
    # Mirrors cli.replay's own task exactly: trivial checks, so the gate
    # always admits regardless of what the scripted turn says.
    task = make_task("replay verification", ["true"], task_id="fixture-gen")
    result = await loop.run(task, ctx)
    assert result.gate_report.admitted is True, "fixture generation must itself admit"

    entries = [
        CassetteEntry(
            request=req, response=resp, digest=request_digest(req)
        ).model_dump(mode="json")
        for req, resp in scripted.recorded
    ]
    cassette_path.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    for suffix in ("", "-wal", "-shm"):
        Path(str(trajectory_db) + suffix).unlink(missing_ok=True)
    print(f"Wrote {len(entries)} cassette entr{'y' if len(entries) == 1 else 'ies'} to {cassette_path}")


if __name__ == "__main__":
    asyncio.run(main())
