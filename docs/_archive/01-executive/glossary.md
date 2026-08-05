---
status: rationale
updated: 2026-07-29
retrieval: excluded
---
# Glossary

> [!NOTE]
> Working architectural proposal, refined iteratively.

## Architecture
- **CAR**: Control-Agency-Runtime model. Control authorizes, Agency deliberates, Runtime executes. Enforced via grants, import linters, and a single dispatch choke point.
- **Port**: `typing.Protocol` in domain language defining capability boundaries (e.g. `Memory.recall()`).
- **Adapter**: Interchangeable concrete implementation of a port.
- **Conformance Suite**: Parametrized behavioral tests (`tests/contracts/`) validating swappability for adapters.
- **Composition Root**: Single `build_kernel(config)` wiring function; no DI container.
- **Dispatch Choke Point**: Single execution path attaching authorization, budget, auditing, and redaction.
- **Grant**: Expiring capability token minted by `PolicyEngine.authorize()` and verified at execution (`verify_grant`).
- **TCB**: Trusted Computing Base (policy, evaluator, gates, benchmarks, deployment gate, secrets, sandbox). Read-only for agents.
- **Sidecar**: Out-of-process compiled service (deployment topology, not architectural layer).

## Execution
- **DMARTIC**: Inner loop: Design, Measure, Analyze, Review, Test, Improve, Control, Self-Reflect.
- **System 1 / System 2**: Fast ReAct for local tasks; deliberate best-of-N + sequential repair for complex work.
- **Best-of-N**: Propose *n* gated, ranked candidates across worktrees (no persistent MCTS tree/backpropagation).
- **Sequential Repair**: Feeding gate failure diagnostics back to candidates for iterative repair.
- **Escalation Ladder**: Deterministic rules (failures, scope, diff size, risk) routing System 1 to System 2.
- **Worktree**: Isolated git working directory isolating tracked file state per candidate attempt.
- **Materialization**: Copying ignored artifacts (`.env`, `.venv`, `node_modules`) into fresh worktrees.
- **EffectClass**: `PURE` / `IDEMPOTENT` / `DESTRUCTIVE`. Governs replay safety (only `PURE` re-executes on replay).
- **Cassette**: Recorded model interactions enabling zero-network replay.

## Memory & Retrieval
- **STM / LTM**: Short-term session ring-buffer (SQLite-WAL) and durable long-term `Memory` port.
- **Code Graph**: Deterministic code structure (imports, calls, co-change) extracted via Tree-sitter and git.
- **Episodic Memory**: Bi-temporal learned facts, decisions, and rationale with temporal invalidation.
- **Bi-temporal**: Tracks valid time (when fact held) and transaction time (when learned).
- **AST-bounded Chunk**: Code chunk bounded by Tree-sitter symbol spans, prefixed with path and symbol path.
- **Skeletonization**: Stripping function bodies while preserving signatures, interfaces, and docstrings.
- **Staged Re-hydration**: Restoring full file context when compacted context triggers build/test failure.
- **Stable Prefix**: Byte-identical leading prompt text preserved for provider context caching.

## Evaluation
- **Hard Gate**: Binary blocking admission check (tests pass, coverage, unmodified tests, diff bounds).
- **Soft Score**: Continuous ranking signal (PRM value) applied only to candidates clearing hard gates.
- **`tests_unmodified`**: Hard gate ensuring candidates do not alter evaluation test suites.
- **Pristine Injection**: Supplying test suites read-only from base commit.
- **PRM**: Process Reward Model scoring intermediate step quality.
- **A/A Noise Floor**: Score-delta distribution from running unmodified harness twice to measure variance.
- **Commit-replay**: Harvester turning historical commits into un-contaminated task benchmarks.
- **Recall@k**: Retrieval quality metric measured independently from overall task success.

## Improvement
- **RHI**: Recursive Harness Self-Improvement outer loop over mutable surfaces, requiring human sign-off.
- **Mutable Surface**: Editable components (prompts, retrieval parameters, routing heuristics, non-Control adapters).
- **AOI**: Auxiliary Optimization Intelligence (small advisory models in shadow mode).
- **Shadow Mode**: Model predictions logged for calibration without executing actions.
- **Exploration Fraction**: Share of un-censored runs executed to gather unbiased training data.

## Protocols & Channels
- **MCP**: Model Context Protocol for vertical tool integration.
- **A2A**: Agent-to-Agent protocol for peer delegation.
- **Observer / Interceptor**: Event subscribers; interceptors can deny execution, observers only log.
- **Pilot**: External interface driving headless entry point (CLI/TUI, bot, IDE, CI).
- **`sagiha-bot`**: Disposable messaging bot client in separate repository.

## Roadmap
- **Vertical Slice (S0–S4)**: End-to-end integration slices with measurable gates.
- **Trigger Condition**: Quantitative measurement threshold required to adopt advanced components.
