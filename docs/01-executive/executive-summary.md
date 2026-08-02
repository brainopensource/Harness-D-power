---
status: rationale
updated: 2026-07-29
retrieval: excluded
---
# Executive Summary: SAGIHA Meta-Harness

> [!NOTE]
> Working architectural proposal, refined iteratively.

## Overview
SAGIHA (Super AGI Harness Agent) turns frontier LLMs into autonomous software engineering agents operating independently or with human oversight. All capabilities are benchmark-measured. Coding is the default [execution profile](../02-architecture/execution-profiles.md).

## Key Architectural Pillars
- **CAR Structure**: Control (policy/budget), Agency (deliberation), Runtime (execution). Agency holds no Runtime references; actions pass through a single dispatch choke point requiring a PolicyEngine `Grant`. Enforced via CI import rules.
- **Dual-Process Execution**: System 1 (fast ReAct) for local tasks; System 2 (best-of-N + sequential repair) across parallel worktrees for complex tasks.
- **Epistemic Memory Split**: Tree-sitter/git for deterministic code graphs; bi-temporal SQLite for episodic memory.
- **Protocols**: MCP for vertical tools; A2A for remote peer agents.
- **Bounded Self-Improvement (RHI)**: Outer loop optimizes prompts, parameters, and adapters—never evaluators, policy, gates, or benchmarks. Requires human sign-off.

## Non-Negotiable Invariants
1. **Sandbox Perimeter**: Security rests on sandbox boundaries, not command blocklists.
2. **Data vs Instruction**: Repo/web content is data, never instruction.
3. **Pristine Injection**: Candidates run against read-only injected test suites and cannot edit graders.
4. **Typed Port Contracts**: No `Dict[str, Any]` across ports; contracts verified via per-port conformance suites.
5. **Trigger-Based Migration**: Components migrate based on empirical triggers, not calendar dates.

*See [Phased Migration Matrix](../07-roadmap/phased-migration-matrix.md) and [Hexagonal Ports](../03-contracts-and-models/hexagonal-ports.md).*
