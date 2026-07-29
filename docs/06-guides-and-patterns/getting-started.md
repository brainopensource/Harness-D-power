# **Getting Started & Day-Zero Quickstart**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Prerequisites**

Python 3.13+, Git, SQLite3, and a container runtime (Docker or Podman). The container runtime is required rather than optional: the sandbox is the security perimeter, so an agent with shell access runs inside one from the first slice.

## **Configuration**

A single local-first `config.toml`:

```toml
[model]
provider  = "..."          # endpoint and credentials
mode      = "live"         # or "replay" to run from cassettes with zero API calls

[workspace]
root         = "/path/to/target/repo"
worktree_dir = ".sagiha/worktrees"

[autonomy]
level = "interactive"      # interactive | hybrid | autonomous | scheduled

[governor]
max_concurrent_runs   = 2
max_spend_usd_per_hour = 5.0
max_lsp_servers       = 4

[sandbox]
egress_allowlist = ["pypi.org", "registry.npmjs.org"]
```

Validated by Pydantic at startup, so misconfiguration fails immediately rather than at the first tool dispatch.

## **The Day-Zero Slice (S0)**

Slice S0 delivers one thing end-to-end: **the agent resolves a failing test in a single file, verified, logged, and replayable.** That is deliberately unglamorous, and it exercises every layer thinly — which is where the real risk lives.

Components in S0: `ModelProvider` with cassette replay, Pydantic domain models, the dispatch choke point, `PolicyEngine` with capability grants, SQLite-WAL trajectory store, Tree-sitter chunking with FTS5, structured edit application, a pytest runner, and commit-per-step checkpoints.

```bash
sagiha run --task "fix the failing test in tests/test_parser.py"
```

## **Verify Your Setup**

```bash
# 1. Port conformance — every adapter satisfies its contract
pytest tests/contracts/

# 2. Replay determinism — the kernel runs with zero API calls
sagiha replay --run-id <id>

# 3. Boundary enforcement — agency/ cannot reach runtime/
lint-imports
```

If all three pass, the architecture's load-bearing guarantees hold on your machine.

## **What Comes Next**

Slices S1–S4 add sandboxed isolation, measured retrieval, candidate search, and the outer loop. Each has a gate that must pass before the next begins — see the [Phased Migration Matrix](../07-roadmap/phased-migration-matrix.md).

## **Working Order That Avoids the Common Trap**

Build in this order, and resist reordering it: **model port and replay → policy and dispatch → edit application → retrieval → isolation → search → outer loop.** The temptation is to start with the interesting parts — quantization, tree search, sidecars. Those are the parts that will not matter if the boring ones are wrong, and the correct seams are what make deferring them free.
