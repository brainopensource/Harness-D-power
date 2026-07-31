---
status: rationale
---
# 📐 v2-S4 A/A Noise Floor — s0-core

**Status: template, not yet populated.** This file is committed now so the `bench-aa` CI job
(`.github/workflows/ci.yml`) has somewhere to write its artifact, and so the S4 exit-gate command
sequence in `docs/implementation/development_plan_v2.md` has a real target. The numbers below are
placeholders and must not be cited until a real run replaces them — doing so would repeat exactly
the H1/H5 mistake this sprint exists to fix (a number that looks measured but was never computed).

## How this gets populated

```bash
uv run sagiha harvest --repo . --validate --min-tasks 30 \
    --output benchmarks/definitions/s0-core.json
uv run sagiha bench --suite benchmarks/definitions/s0-core.json --aa --runs 2 \
    --output docs/rationale/benchmarks/noise-floor.md
```

Requires: a pinned suite of ≥30 validated tasks (`benchmarks/definitions/s0-core.json`, S4.1d) and a
live or cassette-recorded model to run the suite against — this is a real compute + time cost, not a
documentation task, which is why it is not fabricated here.

## Template shape (to be overwritten by the real report)

```
Suite: s0-core v1 (N tasks) · model <version> · harness <version> · config <hash>
Runs: 2 · Noise floor: ±<ci_width>pp

Resolved:      <mean> / <n_tasks>  (<pct>% ± <std>pp)
Cost/success:  $<mean> ± $<std>
Wall/success:  <mean>s
Cache hit:     <rate>
Gate failures: tests_pass <n> · tests_unmodified <n> · coverage <n>
Bootstrap CI:  [<lo>, <hi>] (alpha=0.05, seed=0, n=<n_tasks>)
```

`tests_unmodified` nonzero on an A/A run (both passes are the *unmodified* harness) is itself a
signal worth investigating before trusting anything else in the report — see
`e0/reporter.py`'s gate-failure breakdown.
