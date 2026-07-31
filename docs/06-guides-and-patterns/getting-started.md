---
status: rationale
retrieval: excluded
updated: 2026-07-30
---
# **Getting Started & Day-Zero Quickstart**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

> [!IMPORTANT]
> **Implementation truth:** [STATUS.md](../STATUS.md). **Sprint 3a is closed (2026-07-30).**
> `sagiha run` and `sagiha replay --verify` are available now, in CI — but cassette-driven only.
> There is no live-model adapter yet, so every run today is played back from a committed cassette.

## **Prerequisites**

Python >=3.13, Git, SQLite3. A container runtime (Docker or Podman) is required for
autonomous/scheduled operation ([ADR-0006](../08-decisions/0006-sandbox-is-the-perimeter.md));
optional for local interactive development (subprocess sandbox).

## **Configuration**

A single local-first `config.toml` (see [Configuration Reference](../05-tech-stack/configuration-reference.md)).
Many sections are **planned**; composition today consumes only a subset — STATUS.md and the
configuration reference mark which fields are live.

```toml
[model]
mode      = "replay"       # live | record | replay — replay works today; live/record still fail
                            # closed at composition until the OpenAI-compatible adapter lands

[workspace]
root         = "/path/to/target/repo"
worktree_dir = ".sagiha/worktrees"

[autonomy]
level = "interactive"      # interactive | hybrid | autonomous | scheduled

[governor]
max_concurrent_runs   = 2
max_spend_usd_per_run = 5.0
```

Validated by Pydantic at startup for security invariants that already exist (e.g. refuse
subprocess+autonomous, refuse host network without `allow_unsafe`).

## **Sprint 3a — Close the Loop — ✅ Closed**

Sprint 3a delivered one end-to-end capability: **the agent resolves a failing test in a fixture
repo, verified by a gate, logged, and replayable from a cassette** — see
[Sprint 3a / 3b](../rationale/sprints/sprint-3.md).

Delivered: fixed tool-call parsing, `ModelRequest` v2, digest-matched cassette, five built-in tools
with schema-declared path scoping, a minimal evaluator, `sagiha run` / `sagiha replay --verify` in
CI. Still open, as a fast-follow rather than part of the exit test: the OpenAI-compatible (Ollama)
adapter — no run against a real model is possible yet. Out of scope for this sprint entirely:
retrieval/FTS5, container sandbox, best-of-N (Blocks 4–5 / later).

**Available now:**

```bash
sagiha run "fix the failing test in tests/test_parser.py" --cassette .sagiha/cassettes/default.json
sagiha replay <run-id> --verify --cassette .sagiha/cassettes/default.json
```

## **Verify Your Setup (today)**

```bash
# 1. Full test suite (coverage-gated — what CI runs)
uv run pytest tests/ -q --cov=src/sagiha --cov-report=term-missing

# 2. Boundary enforcement — agency/ cannot reach runtime/
uv run lint-imports

# 3. Types on the harness package
uv run pyright src/sagiha

# 4. CLI surface today
uv run sagiha version
uv run sagiha run --help
uv run sagiha replay --help
```

Replay determinism and a full cassette-driven agent run are both verifiable today — Sprint 3a's exit
test runs in CI. A run against a **live** model is not yet possible (see the OpenAI adapter above).

## **What Comes Next**

| Sprint / Block | Focus | Doc |
| :--- | :--- | :--- |
| Sprint 3a | Close the loop | ✅ Closed — [sprint-3.md](../rationale/sprints/sprint-3.md) |
| Sprint 3b | Hardening (resume, bus resilience, deny-path) | [sprint-3.md](../rationale/sprints/sprint-3.md) |
| Block 2 | E0-lite measurement | [phased-migration-matrix.md](../07-roadmap/phased-migration-matrix.md) |
| Blocks 3–5 | Authority, retrieval, sandbox/MCP/OTel | [STATUS.md](../STATUS.md) |

## **Working Order That Avoids the Common Trap**

Build in this order, and resist reordering it: **model port and digest replay → policy and
dispatch → edit/tools → run loop + gates → measurement → retrieval → isolation → search →
outer loop.** The temptation is to start with quantization, tree search, or sidecars. Those
will not matter if the boring path is wrong; correct seams make deferring them free.
