---
status: normative
updated: 2026-08-05
---
# ADR-0011: No LSP Adapter; Tree-sitter Plus the Project's Own Toolchain

**Status**: Accepted · **Date**: 2026-08-05 · **Fork**: F11

## Context

One proposal kept an `LSPAdapter` at growth tier with a warm server pool. The other wanted it
eliminated and replaced with tree-sitter, on grounds of instability and cost.

Tree-sitter and an LSP answer different questions — **tree-sitter gives syntax, an LSP gives
semantics** — so "replace one with the other" is not strictly coherent as stated. But the
semantic tier (type errors, unresolved symbols, cross-file references) has a cheaper server:
**the project's own linters and type-checkers**, invoked directly.

Every target repository already has them, they are already required to run for the test gate,
and they are stateless per invocation. An LSP session is a long-lived stateful process pool
that must be warmed, supervised and torn down per worktree — a large amount of machinery to
obtain answers a subprocess already gives.

The predecessor shipped `lsp.py` as a stub with no adapter, which under ADR-0005 means it
should never have existed.

## Decision

- **No `LSPAdapter`.** It is not a port, not a growth-tier port, and does not appear in the
  tree.
- **Tree-sitter serves syntax** — including the pre-write parse that keeps syntax errors out
  of the test loop.
- **The T2 semantic verification tier invokes the project's own linters and type-checkers
  directly**, as subprocesses inside the sandbox.

## Consequences

- No warm pool, no session lifecycle, no per-worktree server supervision.
- Semantic answers are exactly as good as the target project's own tooling — which is the
  standard its maintainers are held to, and therefore the right standard.
- Verification tiers stay: T0 structural (µs), T1 syntax via tree-sitter (~ms/file), T2
  project toolchain (sub-second to seconds), T3 tests (seconds to minutes).

## Reversal Conditions

If T2 measurably needs cross-file semantic queries that a project's own toolchain cannot
answer as a batch invocation — go-to-definition across a large repository inside the repair
loop, at a latency the loop can afford — an `LSPAdapter` is reconsidered. It enters under
ADR-0005 like any other port: with its first adapter and conformance test, in the same change.
