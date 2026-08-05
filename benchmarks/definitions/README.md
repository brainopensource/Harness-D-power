# Pinned benchmark suites

`s0-core.json` is generated, not hand-authored:

```bash
uv run sagiha harvest --repo . --validate --min-tasks 30 --output benchmarks/definitions/s0-core.json
```

It is committed once generated so `bench --aa` and the `bench-aa` CI job run against a **pinned**
suite (`docs/06-guides-and-patterns/benchmark-curation.md`'s freezing rule) — the suite must not
silently drift between CI runs. Adding tasks creates a new suite version rather than mutating this
one in place; see the curation doc for the versioning discipline.

**Updated 2026-08-01 (W9).** `s0-core.json` now exists, but it is *imported*, not harvested:
harvesting this repo yields 0/23 valid tasks, so the decided source is a 30-task SWE-bench Lite
subset produced by `scripts/import_swebench_lite.py` (deterministic: round-robin across 12 repos in
`instance_id` order, so re-running reproduces the identical suite).

Every task carries `validated: false` on purpose — validation means *this tree* reproduced the
failing test at `base_commit`, which has not happened. SWE-bench's own validation is not ours to
claim.

**The suite is not yet runnable here.** The E0 runner materializes tasks with `git worktree add`
against the local repository, so these upstream base commits are invalid references. See
`docs/rationale/benchmarks/noise-floor.md` for the full blocker write-up and what closing it
requires.
