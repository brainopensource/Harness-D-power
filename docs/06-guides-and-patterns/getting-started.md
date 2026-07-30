---
status: normative
updated: 2026-07-30
---

# **Getting Started & Day-Zero Quickstart**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

> [!IMPORTANT]
> **Implementation truth:** [STATUS.md](../STATUS.md). Today you can verify the scaffold
> (`pytest tests/contracts/`, `lint-imports`, `sagiha version`). `sagiha run` / `replay` are
> **Planned — Sprint 3**, not available yet.

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
mode      = "replay"       # live | record | replay — live/record wiring is Sprint 3

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

## **Near-Term Goal — Sprint 3 (Close the Loop)**

Sprint 3 delivers one end-to-end capability: **the agent resolves a failing test in a fixture
repo, verified by a gate, logged, and replayable from a cassette** — see
[Sprint 3](../sprints/sprint-3.md).

Components in scope: fixed tool-call parsing, `ModelRequest` v2, digest-matched cassette,
OpenAI-compatible (Ollama) adapter, five built-in tools, minimal evaluator, `sagiha run` /
`sagiha replay --verify`. Retrieval/FTS5, container sandbox, and best-of-N are **out of scope**
for this sprint (Blocks 4–5 / later).

> **Planned — Sprint 3** target UX:

```bash
sagiha run --task "fix the failing test in tests/test_parser.py"
sagiha replay --run-id <id> --verify
```

## **Verify Your Setup (today)**

```bash
# 1. Port shape / config contracts
uv run pytest tests/contracts/ -q

# 2. Boundary enforcement — agency/ cannot reach runtime/
uv run lint-imports

# 3. Types on the harness package
uv run pyright src/sagiha

# 4. CLI surface today
uv run sagiha version
```

Replay determinism and a full agent run are **not** verifiable until Sprint 3's exit test is green.

## **What Comes Next**

| Block | Focus | Doc |
| :--- | :--- | :--- |
| Sprint 3 / Block 1 | Close the loop | [sprint-3.md](../sprints/sprint-3.md) |
| Block 2 | E0-lite measurement | [phased-migration-matrix.md](../07-roadmap/phased-migration-matrix.md) |
| Blocks 3–5 | Authority, retrieval, sandbox/MCP/OTel | [STATUS.md](../STATUS.md) |

## **Working Order That Avoids the Common Trap**

Build in this order, and resist reordering it: **model port and digest replay → policy and
dispatch → edit/tools → run loop + gates → measurement → retrieval → isolation → search →
outer loop.** The temptation is to start with quantization, tree search, or sidecars. Those
will not matter if the boring path is wrong; correct seams make deferring them free.
