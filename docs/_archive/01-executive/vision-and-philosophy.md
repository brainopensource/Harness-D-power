---
status: rationale
updated: 2026-07-29
retrieval: excluded
---
# Vision & Foundational Design Philosophy

> [!NOTE]
> Working architectural proposal, refined iteratively.

## Core Thesis
Frontier LLMs hold all intelligence, planning, and reasoning. The harness is a modular environment providing context, structured memory, tool contracts, policy enforcement, and verification gates.

## Foundational Principles

1. **LLM-Centric Intelligence**: Models drive goals and decisions; the harness enforces boundaries, policy, and execution.
2. **Hexagonal Boundary Isolation**: Domain-language ports separate core logic from infrastructure. CI import rules and parametrized conformance suites enforce seams.
3. **Day-Zero Decoupling**: Seams drawn upfront allow building simple implementations first and deferring complex ones cleanly.
4. **Boring Components First**: Focus on core primitives (context, edit execution, test loops) over exotic tech. Advanced modules require empirical trigger conditions.
5. **Explicit Composition over DI Containers**: A single `build_kernel(config)` root wires dependencies, preserving static code navigability for human and LLM maintainers.
6. **Dual-Process Loops**: Fast System 1 (ReAct) paired with System 2 (best-of-N + sequential repair) over parallel worktrees, routed via deterministic escalation ladders.
7. **Bounded Model–Harness Co-Evolution**: Outer loop self-improvement optimizes mutable scaffolding (prompts, parameters) but cannot touch the TCB (policy, evaluator, gates, benchmarks).
8. **Generator–Evaluator Separation**: Pristine, read-only test suite injection prevents candidates from altering their own graders.
9. **Honest Measurement**: All performance claims are evaluated against a measured A/A noise floor with multi-run statistical variance reporting.
10. **Untrusted by Default**: External content (repository files, web data) is untrusted. Security relies on container sandboxing, credential isolation, and egress allowlisting.
