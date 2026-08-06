---
status: historical
updated: 2026-07-29
---
# ADR-0007: The Trusted Computing Base Is Never Agent-Writable

**Status**: Accepted  
**Date**: 2026-07-28

## Context
Allowing self-improving agents to edit evaluation or policy code incentivizes shortcutting benchmark metrics by modifying the grader.

## Decision
- **TCB Scope**: Policy engine, autonomy config, Evaluator, gate definitions, benchmark tasks, deployment gates, secret handlers, sandbox boundary.
- **Enforcement**:
  1. `MutationProposal.targets` path allowlist.
  2. Protected git branches.
  3. CI rejection of TCB modifications.
  4. Import-linter `tcb-isolation` rule forbidding TCB imports of `agency` or `aoi`.
  5. Mandatory human sign-off for deployment.

## Consequences
- Self-improvement remains bounded, safe, and auditable.

## Reversal Conditions
- None (unrestricted self-modification renders evaluation unfalsifiable).
