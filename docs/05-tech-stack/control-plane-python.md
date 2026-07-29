# **Python Control Plane & Core Ecosystem**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Core Runtime & Ecosystem**

* **Runtime Engine**: Python 3.12+, async-first.
* **Schema Validation**: Pydantic v2 for frozen domain schemas, trajectories, and configuration.
* **Hexagonal Protocols**: `typing.Protocol`, verified by `mypy`/`pyright` in strict mode plus per-port conformance suites. **`@runtime_checkable` is not used as a correctness mechanism** — it checks method presence only, never signatures, so an adapter with wrong argument types passes it while incurring runtime cost for a guarantee it does not provide.
* **Composition**: a single explicit composition root, `build_kernel(config) -> Kernel`.
* **Boundary Enforcement**: `import-linter` layer contracts in CI, enforcing that `agency/` cannot import `runtime/` or `adapters/`.

## **No DI Container, No Plugin Discovery**

Both are dropped in favor of explicit wiring, and the reasoning is specific to this system rather than general taste.

A container with runtime plugin discovery defeats static analysis: type checkers cannot see dynamically registered implementations, so "go to definition" fails and call sites become unresolvable. This codebase's **principal maintainer is an LLM navigating it through a language server** — that is the system's stated purpose. Static navigability is therefore a first-class architectural requirement, not a style preference, and the harness should be designed for the comprehension of the agent that will maintain it.

Explicit imports and one wiring function are also greppable, type-checkable, and trivially testable. Dynamic indirection buys flexibility the system does not need, at the cost of the analyzability it depends on most.

Extensions (skills, hooks) remain supported, but are loaded from **declared locations** rather than by scanning, preserving the same property.

## **Testing Stack**

* **`pytest`** with the conformance suites in `tests/contracts/` parametrized across adapters.
* **Cassette replay** at the `ModelProvider` boundary — the entire kernel runs in CI with zero API calls, which is the cheapest testability win in the design and the reason record/replay is a Day-0 deliverable rather than a later nicety.
* **Property tests** for the trajectory DAG and effect-class replay semantics.

## **Observability**

OpenTelemetry using the **GenAI semantic conventions**, so LLM call spans carry token counts, cost, and cache-hit data in a form existing tooling already understands. The Trajectory Store is derived from the span log rather than maintained as an independent second record of the same facts — two stores of one truth drift, and reconciling them later is strictly harder than deriving one now.

## **Configuration**

Local-first `config.toml`: model endpoints, autonomy level, worktree root, MCP servers, budgets, governor limits. Validated by Pydantic at startup, so misconfiguration fails immediately and loudly rather than at the first tool dispatch.
