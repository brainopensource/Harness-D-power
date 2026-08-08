---
status: normative
updated: 2026-08-06
---

# ADR-F004: Deterministic Mock Cassette Engine for Parallel Frontend Development

**Status**: Accepted · **Date**: 2026-08-06

---

## Context

Backend development in `src/aether/` is executing in parallel. To prevent front-end development (`src_front/`) from blocking on backend engine completion, front-end components require a deterministic mechanism to simulate execution runs, node transitions, token streaming deltas, and evaluation gate reports.

---

## Decision

- Implement `@aether/mock-server` containing pre-recorded **event stream cassettes** (`swe_bench_pass.json`, `repair_loop_ablation.json`).
- Provide `MockCassettePlayer` inside `@aether/core` implementing the identical interface as `AetherWebsocketClient`.
- Front-end views ingest events via `useAetherStream()` without conditional mock vs. production logic inside UI components.

---

## Consequences

- **Pros**: Front-end CLI and GUI features can be fully developed, visually verified, and automated-tested before backend integration.
- **Cons**: Requires maintaining mock event cassettes aligned with backend JSON schemas.
