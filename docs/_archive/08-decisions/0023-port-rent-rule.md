---
status: historical
updated: 2026-07-31
---
# ADR-0023: The Port-Rent Rule — Ports Pay Rent in Adapters

**Status**: Accepted  
**Date**: 2026-07-31  

## Context

[ADR-0019](./0019-port-consolidation.md) deleted unbacked Protocols. Without a governance rule, speculative or unused ports accumulate over time. Ports carry contract testing overhead, documentation cognitive load, and search noise.

## Decision

**A port shipping zero non-test adapters for two consecutive phases is automatically demoted to `experimental` and enters deletion review.**

- **The Clock**: Tracked by phase (`v2-S<n>`), reset whenever a non-test adapter lands.
- **Non-Test Requirement**: In-memory test stubs do not reset the clock.
- **Demotion vs. Deletion**: Demotion is automatic. Deletion requires written review specifying either deletion or an explicit target phase for adapter delivery.
- **Re-promotion Discipline**: Deleted ports state re-promotion criteria per ADR-0019.
- **TCB Exemption**: TCB boundary ports (`PolicyEngine`, `Evaluator`, `ResourceGovernor`) are exempt.

`ports/meta_improver.py` is explicitly tracked under this rule (dormant per [ADR-0022](./0022-rhi-economic-refounding.md)).

## Consequences

- **Easy**: Keeps port surface lean; speculative ports are safe to try because they leave automatically if abandoned.
- **Hard**: Requires automated CI auditing or phase-exit checklist verification.
- **Foreclosed**: Keeping ports purely as speculative documentation of intent.

## Reversal Conditions

- Deletion churn occurs (ports repeatedly deleted and restored within a year; requires extending window).
- Rule is ignored or never executed (unexecuted rules create false confidence).
- Architecture shifts away from hexagonal port design.

## Related

[ADR-0019](./0019-port-consolidation.md) · [ADR-0022](./0022-rhi-economic-refounding.md) · [Port Stability & Versioning](../03-contracts-and-models/port-stability-and-versioning.md) · [Hexagonal Ports](../03-contracts-and-models/hexagonal-ports.md)
