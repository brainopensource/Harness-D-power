---
status: normative
updated: 2026-07-29
---

# **CI & Quality Gates**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

The architecture's guarantees are only real to the extent CI enforces them. Everything else in this suite describes intent; this is the part that holds.

## **The Gate Sequence**

> **Current CI sequence, per `.github/workflows/ci.yml`.** Sprint 3a closed D28 (replay job flags)
> and D29 (`tests/unit/` never ran) — both are enforced now, not planned. `tests/integration/` does
> not exist yet and stays **Planned**.

```bash
ruff format --check .          # formatting
ruff check .                   # lint
pyright                        # types, strict — BLOCKING
mypy src/                      # types, second opinion — advisory
lint-imports                   # CAR layer boundaries — BLOCKING
pytest tests/contracts/        # port conformance, all adapters — BLOCKING
pytest tests/ --cov=src/sagiha # full suite incl. tests/unit/, 80% coverage floor — BLOCKING
pytest tests/integration/      # integration — Planned
sagiha replay <run_id> --verify --cassette … --workspace …   # replay determinism — BLOCKING
```

Four are blocking for architectural rather than hygienic reasons: types, layer contracts, conformance, and replay determinism. Each corresponds to a property the rest of the documentation *claims*, and a claim nobody checks is decoration.

## **Layer Contracts (`.importlinter`)**

The CAR model is enforced here or nowhere.

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

`tcb-isolation` is the one to watch. If the policy engine or evaluator ever imports from `agency` or `aoi`, the trusted computing base has acquired a dependency on code the outer loop may mutate — and the isolation described in [RHI](../04-workflows-and-loops/rhi-outer-loop.md) becomes fiction. This contract is the mechanical proof it hasn't happened.

## **Protecting the Trusted Computing Base**

Layer contracts stop *import* leakage; a separate check stops *edit* leakage. In `.github/workflows/ci.yml` (GitHub Actions):

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

Note what this protects against: not a malicious agent, but a **well-optimized** one. An improver scored on benchmark results has an obvious gradient toward editing the benchmark, and it will find that gradient without any intent to cheat.

## **Conformance Matrix**

```yaml
strategy:
  matrix:
    port: [model, memory, indexer, workspace, lsp, tool_registry, trajectory, policy, governor, evaluator, worktree, code_graph, toolchain, reviewer, port_shape, profile_resolution]
run: pytest tests/contracts/test_${{ matrix.port }}_conformance.py -v
```

`port_shape` is the odd one out: it is a **meta-conformance** suite that checks the shape of the
contracts themselves rather than the behavior of an adapter — no `Dict[str, Any]` across a boundary,
every method `async`, every payload serializable, no `Grant` in a public signature. See
[Remoteable Ports](../02-architecture/remoteable-ports.md) and
[Contracts to Code](../implementation/contracts-to-code.md).

Each job runs one port's suite across **every** adapter implementing it. A new adapter is not "done" until it appears in that parametrization and passes unchanged — that is the operational meaning of swappable, and the mechanism that makes the [migration matrix](../07-roadmap/phased-migration-matrix.md) safe to execute.

### Example Behavioral Tests

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

The profile suite exists because [execution profiles](../02-architecture/execution-profiles.md)
introduce exactly one behavioral risk: a run that mounts fewer ports could be mistaken for a run that
passed fewer checks. The first two tests close it. The next two assert the invariant that a profile
subtracts capability but never supervision — the failure mode where a config key becomes a
privilege-escalation surface.

## **Replay Determinism**

> **Live since Sprint 3a (2026-07-30).** The `replay` job in `.github/workflows/ci.yml` runs this
> against a committed fixture cassette generated by `scripts/gen_replay_fixture.py` — no more
> hand-written cassette JSON. The command below (`--verify-all --fixtures …`) was the stub's
> placeholder shape and never matched the CLI (D28); the real contract takes a run id:

```bash
sagiha replay <run_id> --verify --cassette tests/fixtures/replay_smoke/cassette.json \
  --workspace tests/fixtures/replay_smoke/workspace --trajectory-db /tmp/replay_check.db
```

Replays a recorded cassette and asserts the recorded request digest matches on re-assembly. This is
what turns "record/replay determinism" from a claim into a test, and it runs with **zero API calls**,
so it is fast and free on every PR. Today's fixture is one trivial turn; extending it to a corpus of
recorded trajectories that must all replay byte-for-byte is Block 2 scope, alongside E0-lite.

A failure here means the kernel became sensitive to something outside the recording — wall-clock time, dict ordering, an un-seeded random, or an un-classified side effect. All four are real bugs that would otherwise surface as unreproducible agent behavior weeks later.

## **Coverage**

Line coverage ≥ 80% overall; **≥ 95% on `sagiha/kernel/policy` and `sagiha/domain`**. The higher bar tracks blast radius: a policy bug is a security incident, and a domain-model bug corrupts every trajectory written while it existed.

Coverage is a floor, not a goal. The conformance suites are the real quality signal, and a PR that raises coverage while weakening a conformance test is a regression.

## **Pre-Commit**

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

`lint-imports` runs pre-commit deliberately. Discovering a layer violation after a large refactor is expensive; discovering it at the commit that introduced it is trivial.

## **Benchmarks Do Not Run Per-PR**

Costed suites run nightly and on release tags, never on every push — a few hundred tasks × several dollars × k repetitions is not a per-PR expense.

```yaml
on:
  schedule: [{ cron: "0 3 * * *" }]
  workflow_dispatch:
```

Nightly publishes task success with variance, cost per successful task, cache hit rate, and retrieval recall@10 — and re-measures the **A/A noise floor** whenever the model version changes, since every subsequent comparison depends on a current baseline.

## **Agent-Authored PRs**

When SAGIHA opens a PR against its own repository it runs the identical pipeline, plus: TCB path check, mandatory human review, and no self-merge. The harness gets no privileges in its own repository that a human contributor lacks — that symmetry is the whole point of the trusted computing base.
