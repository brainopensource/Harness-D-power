---
status: normative
updated: 2026-08-06
---

# ADR-F002: React 19 + Ink Choice for TUI CLI Client

**Status**: Accepted · **Date**: 2026-08-06

---

## Context

We evaluated three potential stacks for the terminal-based CLI interface (`apps/cli`):
* **Option A**: Rust (`Ratatui` + `crossterm`) — Ultra fast, sub-millisecond, low memory, but high code verbosity and low code sharing with GUI.
* **Option B**: React 19 + `Ink` — Declarative JSX components rendering to terminal ANSI characters using standard Flexbox layout math.
* **Option C**: Python (`Textual`) — Native Python TUI framework.

An evaluation matrix scored Option B highest (**84.9 / 100**) due to React developer familiarity, extensive LLM code generation training data, low verbosity, and direct sharing of custom React hooks and Zustand stores with the web GUI.

---

## Decision

- Select **React 19 + Ink** as the stack for `src_front/apps/cli`.
- Package the TUI CLI as a standalone Node.js executable script (`aether-cli`).

---

## Consequences

- **Pros**: Rapid developer and AI component iteration; ~60% code logic sharing with the GUI desktop app via `@aether/core`; low verbosity JSX components (`<Box>`, `<Text>`).
- **Cons**: Requires Node.js runtime and higher memory consumption (~50–80 MB RAM) compared to native Rust TUIs.
