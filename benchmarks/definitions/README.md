# Pinned benchmark suites

`s0-core.json` is generated, not hand-authored:

```bash
uv run sagiha harvest --repo . --validate --min-tasks 30 --output benchmarks/definitions/s0-core.json
```

It is committed once generated so `bench --aa` and the `bench-aa` CI job run against a **pinned**
suite (`docs/06-guides-and-patterns/benchmark-curation.md`'s freezing rule) — the suite must not
silently drift between CI runs. Adding tasks creates a new suite version rather than mutating this
one in place; see the curation doc for the versioning discipline.

This file is a placeholder until the first real harvest+validate pass populates `s0-core.json` — see
`docs/rationale/benchmarks/noise-floor.md` for why that number is not fabricated here.
