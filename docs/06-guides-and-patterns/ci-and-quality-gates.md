---
status: rationale
updated: 2026-07-29
retrieval: excluded
---
# **CI & Quality Gates**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

CI mechanically enforces architectural guarantees, layer isolation, conformance, and determinism.

## **The Gate Sequence**

> **Current CI sequence (`.github/workflows/ci.yml`)**: Sprint 3a closed D28 (replay job flags) and D29 (`tests/unit/` inclusion). `tests/integration/` remains **Planned**.

```bash
ruff format --check .          # Formatting
ruff check .                   # Linting
pyright                        # Strict type checking — BLOCKING
mypy src/                      # Type advisory check — advisory
lint-imports                   # CAR layer contract enforcement — BLOCKING
pytest tests/contracts/        # Port conformance for all adapters — BLOCKING
pytest tests/ --cov=src/sagiha # Unit/contract suite (80% coverage floor) — BLOCKING
pytest tests/integration/      # Integration suite — Planned
sagiha replay <run_id> --verify --cassette … --workspace …   # Replay determinism — BLOCKING
```

Blocking architectural gates: type safety, CAR layer boundaries, port conformance, and replay determinism.

## **Layer Contracts (`.importlinter`)**

Enforces the Clean Architecture / Ports-Adapters-Runtime (CAR) boundaries:

```ini
[importlinter]
root_packages = sagiha

[importlinter:contract:car-layering]
name = Agency must not reach the Runtime
type = forbidden
source_modules =
    sagiha.agency
forbidden_modules =
    sagiha.runtime
    sagiha.adapters
ignore_imports =
    sagiha.agency.* -> sagiha.ports.*

[importlinter:contract:ports-are-pure]
name = Ports import nothing internal
type = forbidden
source_modules = sagiha.ports
forbidden_modules =
    sagiha.adapters
    sagiha.runtime
    sagiha.agency
    sagiha.kernel

[importlinter:contract:domain-is-pure]
name = Domain models have no I/O dependencies
type = forbidden
source_modules = sagiha.domain
forbidden_modules =
    sagiha.adapters
    sagiha.runtime
    httpx
    sqlite3

[importlinter:contract:tcb-isolation]
name = Trusted computing base depends on nothing mutable
type = forbidden
source_modules =
    sagiha.kernel.policy
    sagiha.outer_loop.evaluator
forbidden_modules =
    sagiha.agency
    sagiha.aoi
    sagiha.adapters

[importlinter:contract:layers]
name = Overall layering
type = layers
layers =
    sagiha.agency
    sagiha.kernel
    sagiha.adapters
    sagiha.ports
    sagiha.domain
```

> [!IMPORTANT]
> `tcb-isolation` ensures policy/evaluator components remain independent of outer-loop mutable agency/AOI code, preserving isolation described in [RHI](../04-workflows-and-loops/rhi-outer-loop.md).

## **Protecting the Trusted Computing Base (TCB)**

In `.github/workflows/ci.yml`:

```yaml
- name: Reject TCB modifications from agent-authored branches
  run: |
    TCB_PATHS='src/sagiha/kernel/policy|src/sagiha/outer_loop/evaluator|benchmarks/definitions|\.github/workflows|\.importlinter'
    if git diff --name-only origin/main...HEAD | grep -qE "$TCB_PATHS"; then
      if [ "${{ github.event.pull_request.user.login }}" = "sagiha-agent" ]; then
        echo "::error::PR touches the trusted computing base"; exit 1
      fi
      echo "::warning::TCB touched — human review required"
    fi
```

Prevents self-improving agents from modifying evaluation metrics or policy rules.

## **Conformance Matrix**

```yaml
strategy:
  matrix:
    port: [model, memory, indexer, workspace, lsp, tool_registry, trajectory, policy, governor, evaluator, worktree, code_graph, toolchain, reviewer, port_shape, profile_resolution]
run: pytest tests/contracts/test_${{ matrix.port }}_conformance.py -v
```

* Each job tests one port across **all** implementing adapters.
* `port_shape` tests meta-conformance (async signatures, serializable payloads, no untyped dicts). See [Remoteable Ports](../02-architecture/remoteable-ports.md) and [Contracts to Code](../implementation/contracts-to-code.md).
* Guarantees swappability required by the [migration matrix](../07-roadmap/phased-migration-matrix.md).

### Conformance Test Samples

```python
# tests/contracts/test_policy_conformance.py
async def test_denies_write_outside_worktree_at_every_autonomy_level(policy): ...
async def test_forged_grant_is_rejected_at_dispatch(policy, registry): ...
async def test_expired_grant_is_rejected(policy): ...
async def test_grant_scope_is_path_bounded_not_prefix_matched(policy): ...
async def test_always_gate_list_cannot_be_bypassed_by_autonomy_level(policy): ...


# tests/contracts/test_evaluator_conformance.py
async def test_candidate_modification_of_tests_fails_the_gate(evaluator): ...
async def test_evaluator_uses_injected_suite_not_worktree_copy(evaluator): ...
async def test_evaluator_has_no_degraded_mode(evaluator): ...


# tests/contracts/test_profile_resolution_conformance.py
async def test_profile_without_workspace_never_dispatches_a_write(kernel): ...
async def test_ungated_profile_emits_no_gate_report_not_an_empty_one(kernel): ...
async def test_every_profile_dispatches_through_policy_engine(kernel): ...
async def test_always_gate_holds_under_every_profile(kernel): ...
async def test_unknown_profile_name_is_refused_at_composition(config): ...
```

Profile tests ensure [execution profiles](../02-architecture/execution-profiles.md) subtract capability without relaxing supervision or policy enforcement.

## **Replay Determinism**

Replays recorded cassettes without external API calls (live since Sprint 3a, 2026-07-30):

```bash
sagiha replay <run_id> --verify --cassette tests/fixtures/replay_smoke/cassette.json \
  --workspace tests/fixtures/replay_smoke/workspace --trajectory-db /tmp/replay_check.db
```

Validates kernel determinism against non-seeded randomness, wall-clock variance, or side-effect leaks.

## **Code Coverage Floors**

* **Overall codebase**: ≥ 80% line coverage.
* **Security & Core Domain** (`sagiha/kernel/policy`, `sagiha/domain`): ≥ 95% line coverage.

## **Pre-Commit Configuration**

```yaml
repos:
  - repo: local
    hooks:
      - id: ruff-format
        entry: ruff format
      - id: ruff
        entry: ruff check --fix
      - id: pyright
        entry: pyright
        pass_filenames: false
      - id: lint-imports
        entry: lint-imports
        pass_filenames: false
      - id: no-secrets
        entry: detect-secrets-hook
```

`lint-imports` runs pre-commit to catch architectural layering regressions immediately.

## **Scheduled Benchmark Runs**

Costly evaluation suites run nightly, not per-PR:

```yaml
on:
  schedule: [{ cron: "0 3 * * *" }]
  workflow_dispatch:
```

Tracks task resolution, cost per success, cache hit ratios, and retrieval recall@10 while monitoring A/A noise floors.

## **Agent-Authored PR Rules**

PRs created by `SAGIHA` undergo identical CI pipelines plus TCB path validation, mandatory human review, and strict self-merge prohibition.
