# **CI & Quality Gates**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

The architecture's guarantees are only real to the extent CI enforces them. Everything else in this suite describes intent; this is the part that holds.

## **The Gate Sequence**

```bash
ruff format --check .          # formatting
ruff check .                   # lint
pyright                        # types, strict — BLOCKING
mypy src/                      # types, second opinion — advisory
lint-imports                   # CAR layer boundaries — BLOCKING
pytest tests/contracts/        # port conformance, all adapters — BLOCKING
pytest tests/unit/             # unit
pytest tests/integration/      # integration
sagiha replay --verify-all     # trajectory replay determinism — BLOCKING
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
    port: [model, memory, indexer, workspace, lsp, tool_registry, trajectory]
run: pytest tests/contracts/test_${{ matrix.port }}_conformance.py -v
```

Each job runs one port's suite across **every** adapter implementing it. A new adapter is not "done" until it appears in that parametrization and passes unchanged — that is the operational meaning of swappable, and the mechanism that makes the [migration matrix](../07-roadmap/phased-migration-matrix.md) safe to execute.

## **Replay Determinism**

```bash
sagiha replay --verify-all --fixtures tests/fixtures/cassettes/
```

Replays every recorded trajectory and asserts the step sequence matches byte-for-byte. This is what turns "record/replay determinism" from a claim into a test, and it runs with **zero API calls**, so it is fast and free on every PR.

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
