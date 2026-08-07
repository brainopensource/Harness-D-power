---
status: rationale
updated: 2026-08-07
---

# A/A Variance Floor — **not yet taken**

**There is no floor number in this file, and none should be cited from it.**
The instrument for taking one is complete, green, and rehearsed end to end; the
arms themselves were deliberately deferred — the run costs real API spend and
the decision was to finish Sprint 1–3's code and tests first, then take the
floor. That is a scheduling decision and it is recorded here as one, exactly as
[`performance_timers.md`](performance_timers.md) records what its own run did
and did not show.

Until this file contains discordance rates:

- **No capability number may be published** ([ADR-0002](../../decisions/0002-no-number-before-the-floor.md)).
- **No admission run can be sized.** Derived N is computed from p₀₁/p₁₀, and
  those come from here ([ADR-0003](../../decisions/0003-statistical-admission-protocol.md) rev. 2 §1).
- **M2-abl stays unsized**, and with it the remaining sprint count.

## What is ready, and verified

| Precondition | State |
| :--- | :--- |
| **B3 canary in the floor environment** | **Green here.** 7/7 in `tests/integration/test_b3_canary.py` under `AETHER_REQUIRE_CONTAINER=1`: a good candidate passes, a deliberately broken candidate **fails**, the host filesystem outside the worktree is invisible, egress is refused, and two negative tests prove the leak and egress probes can go red |
| Evaluation container | Built from `containers/eval/`, referenced **by digest**; the runner is Docker here (the documented `--runtime docker` fallback — Podman is not installed on this host) |
| Pinned manifest | `benchmarks/manifests/internal-floor-01.yaml`, `sha256:7c2c2467…`, 84 tasks, 0 exclusions, splits pinned 50 dev / 21 holdout / 13 sealed |
| Validity canary | Every one of the 84 screened bidirectionally through the container: gold patch passes **and** empty patch fails |
| Declared family | `src/aether/measurement/families/aa_floor_smoke_01.yaml`, registered against that manifest hash, smoke tier, N = 50, DEV split |
| Statistics | Verbatim port green against pinned fixtures; the power simulation reproduces ADR-0003 rev. 2's published table in all twelve cells |
| Pipeline rehearsal | `scripts/run_aa_floor.py --dry-run` runs both arms against a local stub endpoint — manifest → worktree → repair edge → contained evaluation → statistics — with **zero external calls**. It refuses to write this file, because a floor over two arms that produced no patches is a floor over the empty patch |

## Taking it

```bash
python3 scripts/build_eval_image.py --runtime docker      # if not already built
python3 scripts/build_floor_manifest.py --n 84            # if not already pinned
OPENROUTER_API_KEY=… .venv/bin/python scripts/run_aa_floor.py \
    --model-base-url https://openrouter.ai/api/v1 --model qwen/qwen3-coder
```

The B3 canary re-runs as a **blocking precondition** inside that script, in the
same environment and the same session as the arms. There is no flag to skip it.
The script overwrites this file with the real report and writes the raw paired
outcomes beside it as JSON.

Order of magnitude from the rehearsal: **~1.45 s per task per arm** of harness
and container time, over 50 DEV tasks × 2 arms × up to 4 evaluations each. The
real run adds model latency, which will dominate it.

## What this floor will and will not be

It will be a floor for the **`internal-floor-01` suite**: 84 deterministic
single-bug Python repair tasks, ten defect shapes wide, each instance carrying
its own constants. That is a real instrument and a real measurement of *the
variance between two identical configurations of this harness*, which is what
an A/A floor is for.

It will **not** be a SWE-bench floor. A floor is a property of an instrument
*and* a task set. The SWE-bench floor remains blocked on per-task environment
images: every task needs its repository's dependencies installed at its base
commit, which is hours of build time and many GB that this environment does not
have. `docs/benchmarks/swe_verified_sample.md`'s 15 tasks are indexed and their
base commits are pinned, but no image exists for any of them, so the validity
canary would exclude all 15 as `instrument_error` — correctly, and uselessly.
That is the next instrument task, not a floor result.

## The rule this file is held to

**A wide floor is a measurement, not a failure**, and a run that shows nothing
is recorded as showing nothing. That rule is the one that would have saved the
predecessor, whose 2026-08-01 attempt printed `mean_delta: 0.000` and
`Pass rate: 0.0%` from 30 tasks that all failed at worktree setup
(the archived write-up kept those numbers only so nobody re-derived them and
mistook them for a result; the archive has since been removed).
The same rule applies to a floor that was never run: this file says so rather
than leaving a template that could be mistaken for one.
