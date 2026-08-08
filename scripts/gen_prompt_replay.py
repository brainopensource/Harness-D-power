#!/usr/bin/env python3
"""Record the wire form of every prompt every shipped topology produces (T0,
Sprint 5 dev prompt §5). The *before* image for two gates that do not exist
yet and cannot exist without one:

* T4's I10 prefix-stability floor — "harness-side byte-identical-prefix rate
  over a fixed replay" needs a fixed replay.
* T5's golden-prompt equivalence test — "every shipped topology produces
  byte-identical prompts before and after" needs a *before*.

Both gates are meaningless once `TaskAPI-054` (T2) rewrites the ten
`TaintSpan(...)` call sites this script drives through, so this runs first,
against today's `workflow/nodes/{architect,generate,repair}.py`, and the
fixtures it writes are the contract every later commit in this sprint is
checked against.

**What is recorded is the wire text a provider actually receives**, not the
`TaintSpan` objects that produce it. A span carries `span_id` and
`created_at=datetime.now(UTC)`, both of which differ on every run by
construction; a golden keyed to them would test the clock. `label` IS
recorded — a provenance change is a real change (see T2.5 in the dev
prompt), and this is what makes such a change visible in a diff instead of
silently passing a text-only comparison.

**No network call, no worktree, no container, no git repository.** Every
node is driven directly through a `CapturingFacade` standing in for
`DispatchFacade` — the same substitution `tests/aether/workflow/test_repair.py`'s
`_FakeFacade` already uses for the repair node alone; this script generalises
it to a full topology run via the real `WorkflowExecutor`, so the executed
path — node ordering, the repair unroll, budget reservation — is the real
one and only the I/O at the edges is a stub.

**Regenerating the fixtures is a reviewed act, not a convenience.**
`--update` writes them; the default is `--check`, which fails loudly on any
difference. A reviewer seeing `tests/fixtures/aether_prompt_replay/**` change
in a diff must be able to read what changed in the prompt — that is the
entire value of the fixture, and a script that regenerates silently on every
run would erase it.

    uv run python scripts/gen_prompt_replay.py --check    # CI, and pre-commit
    uv run python scripts/gen_prompt_replay.py --update   # after a reviewed prompt change
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from aether.agency.context.stability import wire_form  # noqa: E402
from aether.domain.budget import BudgetDims  # noqa: E402
from aether.domain.gate import GateReport, GateStatus  # noqa: E402
from aether.domain.ids import RunId  # noqa: E402
from aether.domain.model_io import ModelRequest, ModelStreamEvent, TextDelta  # noqa: E402
from aether.domain.task import Task, TaskSource  # noqa: E402
from aether.domain.workspace import FileSlice, PatchResult, WorktreeRef  # noqa: E402
from aether.engine import NODE_SOCKETS, build_step_registry  # noqa: E402
from aether.kernel.bus import EventBus  # noqa: E402
from aether.kernel.governor import ResourceGovernor  # noqa: E402
from aether.ports.evaluator import EvalSpec  # noqa: E402
from aether.workflow.nodes.retrieve import TaskInput  # noqa: E402
from aether.workflow.validator import load_topology, validate_topology  # noqa: E402

RECORDER_VERSION = "1"
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "aether_prompt_replay"
WORKFLOWS_DIR = REPO_ROOT / "workflows"
_ZERO_BUDGET = BudgetDims()  # Frozen/immutable — safe as a shared default (ruff B008)

#: Every topology reads these two regardless of what its own `entry_files`
#: param names — one in-memory workspace serves every topology identically,
#: so the fixture is deterministic across the whole set rather than needing a
#: per-topology repo fixture.
FIXTURE_FILES: dict[str, str] = {
    "mod.py": "def add(a, b):\n    return a - b  # BUG: should be a + b\n",
    "store.py": "class Store:\n    def __init__(self):\n        self.items = []\n",
    "README.md": "# fixture repo\n\nA two-file package used only to record prompts.\n",
}

#: Kinds whose node calls `DispatchFacade.model()`. Everything else in a
#: topology (`retrieve`, `apply`, `evaluate`) is driven for realism — the
#: repair edge's routing depends on `evaluate`'s verdict — but produces no
#: prompt of its own.
MODEL_NODE_KINDS = frozenset({"architect", "generate", "repair", "reflector"})


class CapturingFacade:
    """Stands in for `workflow.dispatch_facade.DispatchFacade`. Captures every
    `ModelRequest` in call order; serves reads from a fixed in-memory file
    map; and drives `evaluate()` through exactly one FAILED-then-PASSED cycle
    so every topology with a repair block exercises it exactly once.

    Nothing here touches a worktree, a container or the network — `read`,
    `write`, `apply_patch` and `evaluate` are pure in-memory stand-ins. This
    is the same substitution `tests/aether/workflow/test_repair.py::_FakeFacade`
    makes for one node; here it drives a whole topology through the real
    `WorkflowExecutor`.
    """

    def __init__(self, files: dict[str, str]) -> None:
        self._files = files
        self.requests: list[ModelRequest] = []
        self._evaluate_calls = 0

    async def read(self, args: Any, cost_estimate: BudgetDims = _ZERO_BUDGET) -> FileSlice:
        text = self._files.get(args.repo_rel_path)
        if text is None:
            raise FileNotFoundError(args.repo_rel_path)
        return FileSlice(repo_rel_path=args.repo_rel_path, start_line=1, end_line=-1, text=text)

    async def write(self, args: Any, cost_estimate: BudgetDims = _ZERO_BUDGET) -> None:
        self._files[args.repo_rel_path] = args.text

    async def apply_patch(self, args: Any, cost_estimate: BudgetDims = _ZERO_BUDGET) -> PatchResult:
        return PatchResult(applied=False, rejected_hunks=1)

    async def shell(self, args: Any, cost_estimate: BudgetDims = _ZERO_BUDGET, **kw: Any) -> Any:
        raise NotImplementedError("no shipped topology sets params.tools: true (STATUS.md)")

    async def model(self, request: ModelRequest, cost_estimate: BudgetDims) -> list[ModelStreamEvent]:
        self.requests.append(request)
        return [TextDelta(text="STUB_COMPLETION_FOR_PROMPT_CAPTURE")]

    async def evaluate(self, spec: EvalSpec, cost_estimate: BudgetDims) -> GateReport:
        self._evaluate_calls += 1
        # First verdict FAILED (enters the repair block if the topology has
        # one); second verdict PASSED (stops the unroll at exactly one
        # iteration). A topology with no repair block never calls this twice.
        status = GateStatus.FAILED if self._evaluate_calls == 1 else GateStatus.PASSED
        return GateReport(gate="tests", status=status, detail="AssertionError: add(1, 2) == 3")


def _fixture_task() -> Task:
    return Task(
        task_id="fixture-000",  # type: ignore[arg-type]
        repo="fixture/repo",
        base_commit="0" * 40,
        instructions="`add(a, b)` returns the wrong value for positive inputs. Fix it so `add(1, 2) == 3`.",
        environment_image_digest="sha256:" + "0" * 64,
        test_command_hash="sha256:" + "0" * 64,
        test_paths=("run_tests.py",),
        source=TaskSource(manifest_hash="sha256:" + "0" * 64, instance_id="fixture-000"),
    )


async def _record_topology(path: Path) -> list[dict[str, Any]]:
    """Runs one topology to completion through the real executor and returns
    the wire form of every prompt it produced, in execution order."""
    import asyncio

    from aether.workflow.executor import WorkflowExecutor

    topology_text = await asyncio.to_thread(path.read_text, encoding="utf-8")
    topology = load_topology(topology_text)
    validate_topology(topology, NODE_SOCKETS)

    facade = CapturingFacade(dict(FIXTURE_FILES))
    registry = build_step_registry(
        facade,  # type: ignore[arg-type]
        model_name="stub-model",
        tool_catalog=(),
        default_entry_files=("mod.py", "store.py"),
    )
    bus = EventBus()
    bus.subscribe("recorder", drop_policy="never")
    governor = ResourceGovernor(bus)
    executor = WorkflowExecutor(topology, registry, bus, governor)

    run_id = RunId(f"run-replay-{path.stem}")
    task = _fixture_task()
    worktree = WorktreeRef(
        worktree_id="wt-0", run_id=run_id, base_commit=task.base_commit, abs_hint="fixture"
    )
    initial = TaskInput(task=task, worktree=worktree)

    await executor.execute(run_id, initial)

    node_kind = {n["id"]: n["kind"] for n in topology["nodes"]}
    events = bus.drain("recorder")
    model_node_sequence = [
        e.node_id for e in events if e.kind == "node_started" and node_kind.get(e.node_id) in MODEL_NODE_KINDS
    ]
    assert len(model_node_sequence) == len(facade.requests), (
        f"{path.name}: {len(model_node_sequence)} model-kind nodes started but "
        f"{len(facade.requests)} model() calls captured — the recorder's zip assumption "
        "(one model() call per model-kind NodeStarted, same order) no longer holds"
    )

    return [
        {"node_id": node_id, "kind": node_kind[node_id], "request": wire_form(request)}
        for node_id, request in zip(model_node_sequence, facade.requests, strict=True)
    ]


def _topology_hash(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


async def _record_all() -> dict[str, Any]:
    manifest: dict[str, Any] = {"recorder_version": RECORDER_VERSION, "topologies": {}}
    fixtures: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(WORKFLOWS_DIR.glob("*.yaml")):
        calls = await _record_topology(path)
        manifest["topologies"][path.stem] = {
            "topology_hash": _topology_hash(path),
            "prompt_count": len(calls),
        }
        fixtures[path.stem] = calls
    return {"manifest": manifest, "fixtures": fixtures}


def _write(recorded: dict[str, Any]) -> None:
    FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)
    manifest_path = FIXTURE_ROOT / "manifest.json"
    manifest_path.write_text(
        json.dumps(recorded["manifest"], indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    for stem, calls in recorded["fixtures"].items():
        topo_dir = FIXTURE_ROOT / stem
        topo_dir.mkdir(parents=True, exist_ok=True)
        # Clear stale files from a previous shape (fewer/renamed prompts) before writing.
        for stale in topo_dir.glob("*.json"):
            stale.unlink()
        for ordinal, call in enumerate(calls):
            out = topo_dir / f"{ordinal:03d}-{call['kind']}.json"
            out.write_text(json.dumps(call, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_existing() -> dict[str, Any] | None:
    manifest_path = FIXTURE_ROOT / "manifest.json"
    if not manifest_path.exists():
        return None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    fixtures: dict[str, list[dict[str, Any]]] = {}
    for stem in manifest.get("topologies", {}):
        topo_dir = FIXTURE_ROOT / stem
        calls: list[dict[str, Any]] = []
        for out in sorted(topo_dir.glob("*.json")):
            calls.append(json.loads(out.read_text(encoding="utf-8")))
        fixtures[stem] = calls
    return {"manifest": manifest, "fixtures": fixtures}


def _diff(existing: dict[str, Any] | None, recorded: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    if existing is None:
        return ["no fixtures exist yet — run with --update"]
    if existing["manifest"].get("recorder_version") != recorded["manifest"]["recorder_version"]:
        problems.append("recorder_version changed — run with --update and review the diff")
    old_topos = set(existing["fixtures"])
    new_topos = set(recorded["fixtures"])
    if old_topos != new_topos:
        problems.append(f"topology set changed: -{old_topos - new_topos} +{new_topos - old_topos}")
    for stem in sorted(old_topos & new_topos):
        if existing["fixtures"][stem] != recorded["fixtures"][stem]:
            problems.append(f"{stem}: recorded prompts differ from the checked-in fixture")
        old_hash = existing["manifest"]["topologies"][stem]["topology_hash"]
        new_hash = recorded["manifest"]["topologies"][stem]["topology_hash"]
        if old_hash != new_hash:
            problems.append(f"{stem}: topology file changed ({old_hash} -> {new_hash})")
    return problems


async def _main(update: bool) -> int:
    recorded = await _record_all()
    if update:
        _write(recorded)
        print(f"wrote {len(recorded['fixtures'])} topology fixture set(s) to {FIXTURE_ROOT}")
        return 0

    existing = _read_existing()
    problems = _diff(existing, recorded)
    if problems:
        print("prompt replay fixtures are stale:")
        for p in problems:
            print(f"  - {p}")
        print("\nIf this is a reviewed prompt change, re-run with --update and commit the diff.")
        return 1
    print(f"OK: {len(recorded['fixtures'])} topology fixture set(s) match the checked-in replay.")
    return 0


def main() -> int:
    import asyncio

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update", action="store_true", help="write the fixtures instead of checking them")
    args = parser.parse_args()
    return asyncio.run(_main(args.update))


if __name__ == "__main__":
    raise SystemExit(main())
