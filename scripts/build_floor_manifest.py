#!/usr/bin/env python3
"""Generate and pin the internal task manifest the A/A floor runs on (TASK-014).

**Why an internal suite.** Every SWE-bench task needs its own environment image
with that repository's dependencies installed at that commit. Building 50 of
those is hours of work and many GB, and until they exist a SWE-bench floor
cannot be taken at all — `measurement.md` §2 B1/B3. An internal suite of
single-bug Python repair tasks is a *different* instrument measuring the same
thing the A/A floor is for: the variance of two identical configurations of
this harness. The number it produces is a floor **for this suite**, and the
write-up says so in its first line.

**Deterministic by construction.** The repos are generated from a seed, with
pinned author identity and pinned commit dates, so regenerating the suite on
another machine produces byte-identical trees *and identical base commit
SHAs*. The manifest stays valid across machines, which is what makes the floor
re-runnable rather than a one-off.

Every task is screened by the real bidirectional canary before it is pinned:
the gold patch must pass and the empty patch must fail, on the same evaluator
the floor will use. Failures are published with a reason, never dropped.

    python3 scripts/build_floor_manifest.py --n 50 --runtime docker
    python3 scripts/build_floor_manifest.py --n 4 --uncontained   # quick check
"""

from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from aether.adapters.sandbox.podman import ContainerSandbox, runtime_available  # noqa: E402
from aether.measurement.evaluator import RealEvaluator  # noqa: E402
from aether.measurement.manifest import (  # noqa: E402
    TaskCandidate,
    assign_splits,
    build_manifest,
    dump_manifest,
    manifest_hash,
    screen_all,
)
from aether.measurement.validity import WorktreeValidityInstrument  # noqa: E402

DEFAULT_WORKDIR = Path.home() / ".cache" / "aether" / "internal_suite"
DEFAULT_OUT = REPO_ROOT / "benchmarks" / "manifests"
TEST_COMMAND = "python3 run_tests.py"

#: Deterministic git identity and timestamps: same inputs, same SHAs, on any
#: machine. Without these the manifest's base commits would differ per run and
#: the pinned manifest would be unusable anywhere but the machine that built it.
GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "AETHER Suite Generator",
    "GIT_AUTHOR_EMAIL": "suite@aether.invalid",
    "GIT_COMMITTER_NAME": "AETHER Suite Generator",
    "GIT_COMMITTER_EMAIL": "suite@aether.invalid",
    "GIT_AUTHOR_DATE": "2026-01-01T00:00:00+00:00",
    "GIT_COMMITTER_DATE": "2026-01-01T00:00:00+00:00",
}

#: (name, buggy body, fixed body, expected(a, b)) — one small, unambiguous
#: defect shape each. Deliberately easy: the floor measures *variance between
#: two identical configurations*, and a suite nothing can solve produces a
#: degenerate floor where every pair agrees for the wrong reason.
#:
#: Ten defect **shapes**; each instance draws its own constants from its index,
#: so 84 instances are 84 distinct problems rather than ten repeated ones. Be
#: precise about this in any write-up: the suite's diversity is ten shapes
#: wide, and a floor taken on it says nothing about a suite of real bug reports.
BugShape = tuple[str, str, str, "Callable[[int, int], object]"]

BUG_SHAPES: list[BugShape] = [
    ("add", "return a - b", "return a + b", lambda a, b: a + b),
    ("sub", "return a + b", "return a - b", lambda a, b: a - b),
    ("mul", "return a + b", "return a * b", lambda a, b: a * b),
    ("max_of", "return a if a < b else b", "return a if a > b else b", lambda a, b: max(a, b)),
    ("min_of", "return a if a > b else b", "return a if a < b else b", lambda a, b: min(a, b)),
    ("abs_diff", "return a - b", "return abs(a - b)", lambda a, b: abs(a - b)),
    ("clamp_low", "return a", "return max(a, b)", lambda a, b: max(a, b)),
    ("is_even", "return a % 2 == 1", "return a % 2 == 0", lambda a, b: (a % 2 == 0)),
    ("pow_of", "return a * b", "return a**b", lambda a, b: a**b),
    ("floor_div", "return a / b", "return a // b", lambda a, b: a // b),
]


def _git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True, env=GIT_ENV
    ).stdout


def _module_source(body: str) -> str:
    return f"def f(a, b):\n    {body}\n"


def _tests_source(assertion: str) -> str:
    return f"import sys\nfrom mod import f\n\ntry:\n    {assertion}\nexcept AssertionError:\n    sys.exit(1)\nsys.exit(0)\n"


def _constants(shape: str, index: int) -> tuple[int, int]:
    """Per-instance constants, derived from the index so they are stable —
    and chosen so the defect is actually *observable* for this instance.

    Learned from the canary rather than assumed: a first pass used one
    constant rule for every shape, and 16 of 84 tasks were excluded as
    `empty_patch_passes` — `abs_diff` with a > b, `clamp_low` with a >= b and
    `floor_div` with b dividing a are all tasks whose tests pass with no patch
    at all. Those are free resolves for every arm, which is exactly what the
    bidirectional canary exists to catch. A generator that emits them is a
    broken generator, so the shape constrains its own constants here.
    """
    a, b = 2 + (index % 7), 3 + (index % 5)
    if shape in {"abs_diff", "clamp_low", "max_of"}:
        b = a + 1 + (index % 4)  # the fix must change the answer: b > a
    elif shape == "min_of":
        a, b = 5 + (index % 7), 1 + (index % 4)  # a > b
    elif shape == "floor_div":
        a, b = 7 + (index % 9), 2 + (index % 3)
        if a % b == 0:
            a += 1  # true division must differ from floor division
    elif shape == "pow_of":
        b = 3 + (index % 3)  # a * b != a ** b
    return a, b


def generate_task(workdir: Path, index: int) -> TaskCandidate:
    """One deterministic single-bug repair task, as a real git repository."""
    family, buggy, fixed, expected = BUG_SHAPES[index % len(BUG_SHAPES)]
    a, b = _constants(family, index)
    assertion = f"assert f({a}, {b}) == {expected(a, b)!r}"
    instance_id = f"internal__{family}-{index:03d}"
    repo = workdir / instance_id

    if not (repo / ".git").is_dir():
        repo.mkdir(parents=True, exist_ok=True)
        _git("init", "-q", "-b", "main", cwd=repo)
        (repo / "mod.py").write_text(_module_source(buggy))
        (repo / "run_tests.py").write_text(_tests_source(assertion))
        (repo / "README.md").write_text(
            f"# {instance_id}\n\n`mod.f` is wrong. The test in `run_tests.py` says how.\n"
        )
        _git("add", ".", cwd=repo)
        _git("commit", "-q", "-m", f"{instance_id}: base", cwd=repo)

    base_commit = _git("rev-parse", "HEAD", cwd=repo).strip()

    # The gold patch, produced by the same `git diff` the workspace adapter
    # will later apply — a gold patch generated by a different tool than the
    # one that applies it is a canary for the wrong thing.
    (repo / "mod.py").write_text(_module_source(fixed))
    gold_patch = _git("diff", cwd=repo)
    _git("checkout", "--", "mod.py", cwd=repo)

    return TaskCandidate(
        instance_id=instance_id,
        repo=f"internal/{family}",
        base_commit=base_commit,
        environment_image_digest="",  # filled in by the caller from the built image
        test_command=TEST_COMMAND,
        gold_patch=gold_patch,
        split="dev",
    )


def eval_image_digest(runtime: str, tag: str = "aether/eval:build") -> str | None:
    result = subprocess.run(
        [runtime, "image", "inspect", "-f", "{{.Id}}", tag], capture_output=True, text=True
    )
    if result.returncode != 0:
        return None
    digest = result.stdout.strip()
    return digest if digest.startswith("sha256:") else f"sha256:{digest}"


async def build(args: argparse.Namespace) -> int:
    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    digest = ""
    sandbox = None
    if not args.uncontained:
        if not runtime_available(args.runtime):
            print(f"{args.runtime} not on PATH; use --uncontained to screen without B3", file=sys.stderr)
            return 2
        resolved = eval_image_digest(args.runtime)
        if resolved is None:
            print(
                "aether/eval:build not found. Build it first:\n"
                f"  python3 scripts/build_eval_image.py --runtime {args.runtime}",
                file=sys.stderr,
            )
            return 2
        digest = resolved
        sandbox = ContainerSandbox(args.runtime)
    else:
        # A digest is still required by the schema — the manifest records the
        # environment even when this screening run did not isolate itself.
        digest = "sha256:" + "0" * 64

    candidates = [
        generate_task(workdir, i).model_copy(update={"environment_image_digest": digest})
        for i in range(args.n)
    ]

    print(f"generated {len(candidates)} tasks in {workdir}")
    print(f"screening with the bidirectional canary ({'contained' if sandbox else 'UNCONTAINED'})…")

    verdicts = []
    for candidate in candidates:
        instrument = WorktreeValidityInstrument(
            repo_path=str(workdir / candidate.instance_id),
            worktrees_root=str(workdir / "_worktrees"),
            evaluator=RealEvaluator(
                str(workdir / "_worktrees"),
                resolve_command=lambda spec: TEST_COMMAND,
                sandbox=sandbox,
            ),
            timeout_ms=args.timeout_ms,
        )
        verdict = (await screen_all([candidate], instrument, repeats=args.repeats))[0]
        verdicts.append(verdict)
        mark = "admit " if verdict.admitted else "EXCLUDE"
        print(f"  {mark} {candidate.instance_id} ({verdict.reason or 'gold passes, empty fails'})")

    # Splits are assigned over the *admitted* set, after screening. Assigning
    # them first and then excluding tasks thins each split unevenly, and the
    # smoke tier's N >= 50 applies to DEV — a floor 10 tasks short of its own
    # floor because the canary did its job is not a split policy, it is a bug.
    admitted_ids = [v.instance_id for v in verdicts if v.admitted]
    splits = assign_splits(admitted_ids, seed=args.split_seed)
    candidates = [
        c.model_copy(update={"split": splits[c.instance_id]}) if c.instance_id in splits else c
        for c in candidates
    ]

    manifest = build_manifest(
        manifest_id=args.manifest_id,
        suite="internal",
        candidates=candidates,
        verdicts=verdicts,
        instrument_contained=sandbox is not None,
        instrument_runtime=args.runtime if sandbox is not None else None,
        instrument_image_digest=digest if sandbox is not None else None,
        repeats=args.repeats,
        created_at=datetime.now(UTC),
    )

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.manifest_id}.yaml"
    out_path.write_text(dump_manifest(manifest), encoding="utf-8")

    admitted = len(manifest["tasks"])
    excluded = len(manifest["validity_gate"]["exclusions"])
    print(f"\nadmitted {admitted}, excluded {excluded}")
    print(f"manifest: {out_path}")
    print(f"hash:     {manifest_hash(manifest)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--n",
        type=int,
        default=84,
        # 0.6 * 84 = 50 dev tasks exactly: the smoke tier floors N at 50 and
        # binds to the DEV split, so a 50-task manifest with a 60/25/15 split
        # would leave the floor 20 tasks short of its own floor.
        help="tasks to generate (>= 84 keeps the DEV split at the smoke tier's N >= 50)",
    )
    parser.add_argument("--manifest-id", default="internal-floor-01")
    parser.add_argument("--workdir", default=str(DEFAULT_WORKDIR))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--runtime", default="docker", choices=["podman", "docker"])
    parser.add_argument("--uncontained", action="store_true", help="screen without the B3 container")
    parser.add_argument("--repeats", type=int, default=1, help="gold-patch repeats, for flakiness")
    parser.add_argument("--timeout-ms", type=int, default=120_000)
    parser.add_argument("--split-seed", type=int, default=7)
    args = parser.parse_args(argv)
    return asyncio.run(build(args))


if __name__ == "__main__":
    raise SystemExit(main())
