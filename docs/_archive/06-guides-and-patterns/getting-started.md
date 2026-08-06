---
status: rationale
updated: 2026-07-30
retrieval: excluded
---
# **Getting Started & Day-Zero Quickstart**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

> [!IMPORTANT]
> **Implementation Truth**: See [STATUS.md](../STATUS.md). **Sprint 3a is closed (2026-07-30)**. `sagiha run` and `sagiha replay --verify` are active in CI using cassette playback. Live-model execution requires the pending OpenAI-compatible adapter.

## **Prerequisites**

* **Runtime**: Python ≥3.13, Git, SQLite3.
* **Sandbox**: Docker or Podman required for autonomous/scheduled modes ([ADR-0006](../08-decisions/0006-sandbox-is-the-perimeter.md)); optional for local interactive development (subprocess sandbox).

## **Configuration**

Configured via `config.toml` (see [Configuration Reference](../05-tech-stack/configuration-reference.md)), validated at startup with Pydantic:

```toml
[model]
mode      = "replay"       # replay active; live/record land with OpenAI adapter

[workspace]
root         = "/path/to/target/repo"
worktree_dir = ".sagiha/worktrees"

[autonomy]
level = "interactive"      # interactive | hybrid | autonomous | scheduled

[governor]
max_concurrent_runs   = 2
max_spend_usd_per_run = 5.0
```

## **Sprint 3a Capabilities (Closed)**

Sprint 3a delivers cassette-driven end-to-end execution (see [Sprint 3a / 3b](../implementation/development_plan_v2.md)): tool parsing, `ModelRequest` v2, digest-matched cassettes, path-scoped core tools, minimal evaluator, and CI integration.

```bash
sagiha run "fix the failing test in tests/test_parser.py" --cassette .sagiha/cassettes/default.json
sagiha replay <run-id> --verify --cassette .sagiha/cassettes/default.json
```

## **Verification Commands**

```bash
# 1. Full test suite with coverage enforcement
uv run pytest tests/ -q --cov=src/sagiha --cov-report=term-missing

# 2. CAR Layer boundary linting
uv run lint-imports

# 3. Type checking
uv run pyright src/sagiha

# 4. CLI interface check
uv run sagiha version
uv run sagiha run --help
uv run sagiha replay --help
```

## **Development Roadmap**

| Sprint / Block | Focus | Documentation |
| :--- | :--- | :--- |
| **Sprint 3a** | Close the loop (cassette-driven) | ✅ Closed — [sprint-3.md](../implementation/development_plan_v2.md) |
| **Sprint 3b** | Hardening (resume, bus resilience, deny-paths) | [sprint-3.md](../implementation/development_plan_v2.md) |
| **Block 2** | E0-lite measurement & harvester | [phased-migration-matrix.md](../07-roadmap/phased-migration-matrix.md) |
| **Blocks 3–5** | Authority, retrieval, sandbox / MCP / OTel | [STATUS.md](../STATUS.md) |

## **Recommended Execution Order**

Follow this exact implementation path:

**model port and digest replay → policy and dispatch → edit/tools → run loop + gates → measurement → retrieval → isolation → search → outer loop**
