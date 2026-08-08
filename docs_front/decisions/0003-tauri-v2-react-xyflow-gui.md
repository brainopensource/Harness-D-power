---
status: normative
updated: 2026-08-06
---

# ADR-F003: Tauri v2 + React 19 + `xyflow` Choice for Desktop GUI

**Status**: Accepted · **Date**: 2026-08-06

---

## Context

To provide a visual workflow builder (n8n / ComfyUI paradigm) for interacting with the AETHER Orchestrator, we required a desktop framework for Windows and Linux with native performance, low memory footprint, and custom node canvas capabilities.

We evaluated:
* **Option A**: **Tauri v2 + React 19 + `xyflow` (React Flow)** — Score: **92.8 / 100**.
* **Option B**: Tauri v2 + `LiteGraph.js` — Score: 75.3 / 100.
* **Option C**: Rust Native (`egui`) — Score: 59.3 / 100.

---

## Decision

- Select **Tauri v2 (Rust)** as the desktop shell for Windows and Linux.
- Select **React 19 + `xyflow` (React Flow) + Monaco Editor + Tailwind CSS** for the desktop web view application (`src_front/apps/desktop`).

---

## Consequences

- **Pros**:
  * Industry-standard `xyflow` canvas for interactive DAG workflow node rendering.
  * Native Monaco Editor integration for side-by-side git patch diffing.
  * Lightweight Tauri v2 desktop executable ($< 15\text{ MB}$ installer, $< 40\text{ MB}$ idle RAM).
- **Cons**: Webview rendering overhead for exceptionally massive graphs ($> 2,000$ simultaneous nodes).
