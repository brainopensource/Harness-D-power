#!/usr/bin/env python3
"""Run the A/A variance floor (Sprint 3 Task 5).

Two identical AETHER configurations, paired: same tasks, same order, same
seeds. Any difference between them is variance — sampling, test order, timing,
flaky tests — and that variance is the denominator every later claim in this
project is judged against (`measurement.md` §3, ADR-0002).

    # blocking precondition, enforced below, not documented and hoped for:
    python3 scripts/build_eval_image.py --runtime docker
    python3 scripts/build_floor_manifest.py --n 84

    # rehearsal: full pipeline, local stub endpoint, zero API calls
    python3 scripts/run_aa_floor.py --dry-run

    # the real run
    OPENROUTER_API_KEY=... python3 scripts/run_aa_floor.py \\
        --model-base-url https://openrouter.ai/api/v1 --model qwen/qwen3-coder

**The B3 canary is a blocking precondition and there is no flag to skip it.**
`measurement.md` §2 requires it to pass *in the floor environment* before the
floor run; if a deliberately broken candidate passes evaluation here, every
number this script could produce is unmeasured. It is re-run in-process each
time rather than trusted from an earlier session.

`--dry-run` serves a local SSE endpoint that returns an empty completion, so
the whole pipeline — manifest, worktrees, container evaluation, repair edge,
statistics — is exercised with no external calls and no spend. It **refuses to
write the report**: an arm whose model produced nothing is not an arm, and a
floor computed from two of them is a floor over the empty patch.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import statistics as pystats
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from aether import engine  # noqa: E402
from aether.domain.gate import GateStatus  # noqa: E402
from aether.domain.task import Task, TaskSource  # noqa: E402
from aether.measurement.manifest import (  # noqa: E402
    load_manifest,
    manifest_hash,
    tasks_in_split,
)
from aether.measurement.outcomes import ArmRun, TaskOutcome  # noqa: E402
from aether.measurement.statistics import (  # noqa: E402
    FamilyRegistry,
    mcnemar_exact,
    noise_floor_from,
    resolve_rate,
)

DEFAULT_MANIFEST = REPO_ROOT / "benchmarks" / "manifests" / "internal-floor-01.yaml"
DEFAULT_SUITE_DIR = Path.home() / ".cache" / "aether" / "internal_suite"
DEFAULT_REPORT = REPO_ROOT / "docs" / "rationale" / "benchmarks" / "noise-floor.md"
TOPOLOGY = REPO_ROOT / "workflows" / "linear_repair_v1.yaml"
TEST_COMMAND = "python3 run_tests.py"
FAMILY_ID = "aa_floor_smoke_01"


# ----------------------------------------------------------- preconditions


def require_b3_canary(runtime: str) -> None:
    """Blocking. No flag disables this."""
    print("precondition: B3 canary in this environment…", flush=True)
    env = {**os.environ, "AETHER_REQUIRE_CONTAINER": "1"}
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/integration/test_b3_canary.py", "-q"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    print(result.stdout.strip().splitlines()[-1] if result.stdout.strip() else "(no output)")
    if result.returncode != 0:
        print(result.stdout[-3000:], file=sys.stderr)
        raise SystemExit(
            "B3 canary did not pass in this environment. The floor is blocked regardless of "
            "anything else being ready (measurement.md §2 B3, sprint-03.md Task 5 criterion 1)."
        )


def require_declared_family() -> dict[str, Any]:
    family = FamilyRegistry().get(FAMILY_ID)
    print(f"precondition: family '{FAMILY_ID}' declared (registered_at {family['registered_at']})")
    return family


# ------------------------------------------------------- the stub endpoint


class _StubHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        body = b'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n'
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: Any) -> None:
        return


def start_stub_endpoint() -> tuple[str, ThreadingHTTPServer]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _StubHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_address[1]}/v1", server


# --------------------------------------------------------------- the arms


async def run_arm(
    arm_id: str,
    tasks: list[dict[str, Any]],
    args: argparse.Namespace,
    manifest_digest: str,
    manifest_sha: str,
    model_base_url: str,
    api_key: str | None,
) -> ArmRun:
    results: list[TaskOutcome] = []
    for index, entry in enumerate(tasks, start=1):
        instance_id = entry["instance_id"]
        repo_path = Path(args.suite_dir) / instance_id
        # The manifest states the problem; the runner does not invent one.
        # Until 2026-08-07 this was a single hard-coded sentence handed to every
        # task in the manifest, which is the harness-arm face of the same defect
        # that had the baseline arm formatting the SWE-bench template with the
        # bare `instance_id` (audit F1). A manifest entry without the field is
        # refused rather than papered over: it means the manifest predates the
        # field and must be rebuilt before it can carry a measured run.
        problem_statement = str(entry.get("problem_statement", "")).strip()
        if not problem_statement:
            results.append(
                TaskOutcome(
                    task_id=instance_id,
                    status=GateStatus.NONE,
                    detail=(
                        f"{instance_id}: manifest entry has no problem_statement; rebuild the "
                        "manifest with scripts/build_floor_manifest.py (measurement.md §4.1)"
                    ),
                )
            )
            continue

        task = Task(
            task_id=instance_id,  # type: ignore[arg-type]
            repo=entry["repo"],
            base_commit=entry["base_commit"],
            instructions=problem_statement,
            environment_image_digest=entry["environment_image_digest"],
            test_command_hash=entry["test_command_hash"],
            source=TaskSource(manifest_hash=manifest_sha, instance_id=instance_id),
        )
        started = time.monotonic()
        try:
            result = await engine.run(
                task,
                repo_path=str(repo_path),
                worktrees_root=str(Path(args.workdir) / arm_id / instance_id),
                topology_path=str(TOPOLOGY),
                resolve_command=lambda spec: TEST_COMMAND,
                model_base_url=model_base_url,
                model_name=args.model,
                model_api_key=api_key,
                trajectory_db_path=str(Path(args.workdir) / f"{arm_id}.db"),
                entry_file="README.md",
                sandbox_runtime=None if args.uncontained else args.runtime,
            )
            outcome = TaskOutcome(
                task_id=instance_id,
                status=result.gate_report.status,
                wall_clock_ms=int((time.monotonic() - started) * 1000),
                prompt_tokens=result.usage.prompt_tokens,
                completion_tokens=result.usage.completion_tokens,
                detail=result.gate_report.instrument_error or "",
            )
        except Exception as exc:  # noqa: BLE001
            # Our crash is an instrument error for that task, never a failed
            # task — B4 applied to the runner itself.
            outcome = TaskOutcome(
                task_id=instance_id,
                status=GateStatus.NONE,
                wall_clock_ms=int((time.monotonic() - started) * 1000),
                detail=f"runner raised: {type(exc).__name__}: {exc}",
            )
        results.append(outcome)
        print(
            f"  [{arm_id}] {index:3d}/{len(tasks)} {instance_id:28} "
            f"{outcome.status.value:7} {outcome.wall_clock_ms:6d}ms"
            + (f"  {outcome.detail[:120]}" if outcome.status is GateStatus.NONE else ""),
            flush=True,
        )

    return ArmRun(
        run_id=f"{arm_id}-{int(time.time())}",
        arm_id=arm_id,
        harness_id="aether",
        manifest_hash=manifest_sha,
        split=args.split,
        model_fingerprint=f"openai_compatible:{args.model}:{_endpoint_name(model_base_url)}",
        seed=args.seed,
        results=tuple(results),
        topology_hash=_file_hash(TOPOLOGY),
        container_digest=manifest_digest,
        contained=not args.uncontained,
    )


def _endpoint_name(base_url: str) -> str:
    return base_url.split("//", 1)[-1].split("/", 1)[0]


def _file_hash(path: Path) -> str:
    import hashlib

    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, text: str) -> None:
    """Report writing lives outside the coroutine's hot path (ruff ASYNC240):
    blocking pathlib calls in a coroutine are a real smell even in a script."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _lockfile_hash() -> str:
    lock = REPO_ROOT / "uv.lock"
    return _file_hash(lock) if lock.exists() else "(no uv.lock)"


# -------------------------------------------------------------- reporting


def build_report(
    floor: Any,
    arm_a: ArmRun,
    arm_b: ArmRun,
    family: dict[str, Any],
    p_value: float,
    adjusted: float,
    elapsed_s: float,
) -> str:
    wall = [r.wall_clock_ms for r in arm_a.results + arm_b.results]
    per_task = {
        "mean_ms": int(pystats.mean(wall)) if wall else 0,
        "median_ms": int(pystats.median(wall)) if wall else 0,
        "p90_ms": int(sorted(wall)[int(len(wall) * 0.9)]) if wall else 0,
        "max_ms": max(wall) if wall else 0,
    }
    rate_a, rate_b = resolve_rate(arm_a), resolve_rate(arm_b)
    ci_lo, ci_hi = floor.confidence_interval
    return f"""---
status: rationale
updated: {datetime.now(UTC).date().isoformat()}
---

# A/A Variance Floor — `{arm_a.manifest_hash[:19]}…`

Generated by `scripts/run_aa_floor.py`. Every number below came from the run
named in the instrument tuple; none is typed from memory.

**This is a floor for the `internal-floor-01` suite, not for SWE-bench.** A
floor is a property of an instrument *and* a task set. The SWE-bench floor
remains untaken and is blocked on per-task environment images.

## The number

| Quantity | Value |
| :--- | :--- |
| Paired tasks (both arms measured) | {floor.n_tasks} |
| Instrument errors excluded (B4) | {floor.n_instrument_errors} |
| Resolve rate, arm A | {"n/a" if rate_a is None else f"{rate_a:.1%}"} |
| Resolve rate, arm B | {"n/a" if rate_b is None else f"{rate_b:.1%}"} |
| Mean absolute A/A drift | {floor.mean_delta:.4f} |
| Bootstrap CI (α={floor.alpha}, 2000 iters, seed {floor.seed}) | [{ci_lo:.4f}, {ci_hi:.4f}] |
| **Discordance p₀₁** | **{floor.p01:.4f}** |
| **Discordance p₁₀** | **{floor.p10:.4f}** |
| Discordant pairs | {floor.n_discordant} |
| Exact McNemar p | {p_value:.4f} |
| Holm-adjusted p (family `{family["family_id"]}`) | {adjusted:.4f} |

**p₀₁ and p₁₀ are the deliverable.** Every future family's derived N is
computed from them (ADR-0003 rev. 2 §1); without them no admission run in this
project can be sized at all.

A significant McNemar p here would be a **bug report about the harness**, not a
discovery: two identical configurations are not supposed to differ
systematically.

## Per-task wall-clock — what sizes M2-abl

| Statistic | Value |
| :--- | :--- |
| Mean | {per_task["mean_ms"]} ms |
| Median | {per_task["median_ms"]} ms |
| p90 | {per_task["p90_ms"]} ms |
| Max | {per_task["max_ms"]} ms |
| Both arms, wall-clock total | {elapsed_s:.1f} s |

## Instrument

| Field | Value |
| :--- | :--- |
| Manifest hash | `{arm_a.manifest_hash}` |
| Split | {arm_a.split} |
| Model fingerprint | `{arm_a.model_fingerprint}` |
| Topology hash | `{arm_a.topology_hash}` |
| Container digest | `{arm_a.container_digest}` |
| Contained (B3) | {arm_a.contained} |
| Lockfile hash | `{_lockfile_hash()}` |
| Seed | {arm_a.seed} |
| Family | `{family["family_id"]}` registered {family["registered_at"]} |
| Host | {platform.platform()} · {platform.python_version()} |

## Rules this file is held to

- A wide floor is a **measurement**, not a failure. It changes N, it does not
  invalidate the work.
- A run that shows nothing is recorded as showing nothing.
- No number here appears without the instrument tuple above.
"""


# ------------------------------------------------------------------ main


async def main_async(args: argparse.Namespace, manifest: dict[str, Any]) -> int:
    manifest_sha = manifest_hash(manifest)

    if not args.uncontained:
        require_b3_canary(args.runtime)
    family = require_declared_family()
    if family["manifest_hash"] != manifest_sha:
        print(
            f"family '{FAMILY_ID}' was registered against manifest {family['manifest_hash']} "
            f"but this manifest hashes to {manifest_sha}. A manifest change is a new manifest "
            "and needs a new family — there is no amend.",
            file=sys.stderr,
        )
        return 2

    tasks = tasks_in_split(manifest, args.split)[: args.limit]
    tier_floor = family["sample"]["n"]
    if len(tasks) < tier_floor and not args.dry_run:
        print(
            f"split '{args.split}' has {len(tasks)} tasks, family declares N={tier_floor}",
            file=sys.stderr,
        )
        return 2

    server = None
    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
    model_base_url = args.model_base_url
    if args.dry_run:
        model_base_url, server = start_stub_endpoint()
        api_key = None
        print(f"DRY RUN: stub endpoint at {model_base_url}; no external calls, no spend")

    digest = manifest["tasks"][0]["environment_image_digest"] if manifest["tasks"] else ""
    print(f"manifest {manifest_sha}\nsplit {args.split}: {len(tasks)} tasks, two arms\n")

    started = time.monotonic()
    try:
        arm_a = await run_arm("aether_a", tasks, args, digest, manifest_sha, model_base_url, api_key)
        arm_b = await run_arm("aether_b", tasks, args, digest, manifest_sha, model_base_url, api_key)
    finally:
        if server is not None:
            server.shutdown()
    elapsed = time.monotonic() - started

    floor = noise_floor_from(arm_a, arm_b, seed=args.seed)
    b = sum(1 for a, t in zip(arm_a.results, arm_b.results, strict=True) if a.resolved and not t.resolved)
    c = sum(1 for a, t in zip(arm_a.results, arm_b.results, strict=True) if not a.resolved and t.resolved)
    p_value = mcnemar_exact(b, c)
    adjusted = FamilyRegistry().holm_for_family(FAMILY_ID, [p_value])[0]

    print(
        f"\npaired={floor.n_tasks} instrument_errors={floor.n_instrument_errors} "
        f"p01={floor.p01:.4f} p10={floor.p10:.4f} discordant={floor.n_discordant} "
        f"mcnemar_p={p_value:.4f} holm_p={adjusted:.4f}"
    )
    print(f"wall-clock: {elapsed:.1f}s for {len(tasks)} tasks x 2 arms")

    if args.dry_run:
        print(
            "\nDRY RUN: report NOT written. An arm whose model produced nothing is not an arm, "
            "and a floor over two of them is a floor over the empty patch."
        )
        return 0

    report = build_report(floor, arm_a, arm_b, family, p_value, adjusted, elapsed)
    out = Path(args.report)
    _write(out, report)
    raw = out.with_suffix(".json")
    _write(
        raw,
        json.dumps(
            {
                "arm_a": arm_a.model_dump(mode="json"),
                "arm_b": arm_b.model_dump(mode="json"),
                "floor": floor.model_dump(mode="json"),
            },
            indent=2,
        ),
    )
    print(f"\nwrote {out}\nwrote {raw}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--suite-dir", default=str(DEFAULT_SUITE_DIR))
    parser.add_argument("--workdir", default="/tmp/aether_floor")
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--split", default="dev", choices=["dev", "holdout", "sealed"])
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--model", default="qwen/qwen3-coder")
    parser.add_argument("--model-base-url", default="https://openrouter.ai/api/v1")
    parser.add_argument("--runtime", default="docker", choices=["podman", "docker"])
    parser.add_argument("--uncontained", action="store_true", help="not valid for a published number")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--dry-run", action="store_true", help="stub endpoint, no spend, no report")
    args = parser.parse_args(argv)
    Path(args.workdir).mkdir(parents=True, exist_ok=True)

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"no manifest at {manifest_path}; run scripts/build_floor_manifest.py", file=sys.stderr)
        return 2
    manifest = load_manifest(manifest_path.read_text(encoding="utf-8"))
    return asyncio.run(main_async(args, manifest))


if __name__ == "__main__":
    raise SystemExit(main())
