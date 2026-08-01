#!/usr/bin/env python3
"""Import a pinned SWE-bench Lite subset as a `BenchmarkSuite` (audit M-1, W9.1).

Harvesting from this repository yielded 0/23 valid tasks
(`docs/rationale/benchmarks/s4-harvest-findings.md`), so the plan's decided
source is an *imported* suite instead: SWE-bench Lite, which ships pinned base
commits and a reproducing test command per task — the two properties the E0
harvester validation gate requires and could not find here.

Deterministic by construction: rows are taken in dataset order from offset 0, so
re-running produces a byte-identical suite. The result is committed once and
frozen, per `docs/06-guides-and-patterns/benchmark-curation.md`.

    python3 scripts/import_swebench_lite.py --limit 30 \
        --output benchmarks/definitions/s0-core.json
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROWS_ENDPOINT = "https://datasets-server.huggingface.co/rows"
DATASET = "princeton-nlp/SWE-bench_Lite"
PAGE = 100


def fetch_rows(limit: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    offset = 0
    while len(rows) < limit:
        params = urllib.parse.urlencode(
            {
                "dataset": DATASET,
                "config": "default",
                "split": "test",
                "offset": offset,
                "length": min(PAGE, limit - len(rows)),
            }
        )
        with urllib.request.urlopen(f"{ROWS_ENDPOINT}?{params}", timeout=120) as resp:
            payload = json.load(resp)
        batch = payload.get("rows", [])
        if not batch:
            break
        rows.extend(entry["row"] for entry in batch)
        offset += len(batch)
    return rows[:limit]


def _test_files(test_patch: str) -> list[str]:
    """Files the reference test patch touches — the suite's `test_files`."""
    seen: list[str] = []
    for line in test_patch.splitlines():
        if line.startswith("+++ b/"):
            path = line[len("+++ b/") :].strip()
            if path and path not in seen:
                seen.append(path)
    return seen


def _source_files(patch: str) -> list[str]:
    seen: list[str] = []
    for line in patch.splitlines():
        if line.startswith("+++ b/"):
            path = line[len("+++ b/") :].strip()
            if path and path not in seen:
                seen.append(path)
    return seen


def to_task(row: dict[str, object]) -> dict[str, object]:
    instance_id = str(row["instance_id"])
    patch = str(row.get("patch", ""))
    test_patch = str(row.get("test_patch", ""))
    fail_to_pass = row.get("FAIL_TO_PASS", "[]")
    try:
        tests = json.loads(fail_to_pass) if isinstance(fail_to_pass, str) else list(fail_to_pass)
    except json.JSONDecodeError:
        tests = []

    source = _source_files(patch)
    tested = _test_files(test_patch)

    return {
        "task_id": instance_id,
        "repo": str(row["repo"]),
        "base_commit": str(row["base_commit"]),
        # SWE-bench pins the parent commit only; the "target" is the reference
        # patch, which has no commit sha in the dataset. Recording the base sha
        # here would claim a resolution that does not exist, so the instance id
        # is used as an honest opaque reference.
        "target_commit": f"reference-patch:{instance_id}",
        "diff_summary": (
            f"{len(source)} source file(s), {len(tested)} test file(s); "
            f"{len(tests)} FAIL_TO_PASS test(s)"
        ),
        "failing_test_cmd": " ".join(["pytest", "-q", *tests[:8]]) if tests else "pytest -q",
        "files_changed": source + [t for t in tested if t not in source],
        "test_files": tested,
        "source_files": source,
        # Not validated *by this harness*: validation means this tree reproduced
        # the failing test at base_commit, which requires cloning and running
        # each upstream repo. SWE-bench's own validation is not ours to claim.
        "validated": False,
        "validation_reason": (
            "imported from SWE-bench Lite; not re-validated locally "
            "(requires cloning each upstream repo at base_commit)"
        ),
        "harvested_at": datetime.now(UTC).isoformat(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=30, help="number of tasks (>=30 per M-1)")
    parser.add_argument("--output", type=Path, default=Path("benchmarks/definitions/s0-core.json"))
    args = parser.parse_args(argv)

    # Read a wide window, then round-robin across repos. Taking the first N rows
    # in dataset order gives an alphabetical clump — the first 30 are two repos —
    # and a suite that measures two codebases cannot support a claim about the
    # harness in general. Round-robin over repo-sorted rows is deterministic, so
    # the suite stays reproducible and pinnable.
    pool = fetch_rows(max(args.limit * 10, 300))
    by_repo: dict[str, list[dict[str, object]]] = {}
    for row in pool:
        by_repo.setdefault(str(row["repo"]), []).append(row)
    for bucket in by_repo.values():
        bucket.sort(key=lambda r: str(r["instance_id"]))

    rows: list[dict[str, object]] = []
    depth = 0
    while len(rows) < args.limit:
        added = False
        for repo in sorted(by_repo):
            if depth < len(by_repo[repo]) and len(rows) < args.limit:
                rows.append(by_repo[repo][depth])
                added = True
        if not added:
            break
        depth += 1

    if len(rows) < args.limit:
        print(f"FAIL: selected {len(rows)} tasks, wanted {args.limit}", file=sys.stderr)
        return 1
    rows.sort(key=lambda r: str(r["instance_id"]))

    suite = {
        "suite_id": f"s0-core-swebench-lite-{args.limit}",
        "repo": DATASET,
        "tasks": [to_task(r) for r in rows],
        "created_at": datetime.now(UTC).isoformat(),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(suite, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output} — {len(suite['tasks'])} tasks from {DATASET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
