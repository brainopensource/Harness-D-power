# Harness Capabilities, Additions & Removals Report

This report evaluates proposed feature additions, removals, and refinements for **AETHER DAG v2** by comparing our v2 specification against state-of-the-art reference implementations (Claude Code, Grok Build, Hermes Agent, OpenCode/Crush, Gemini AGY, Clawdbot/Moltbot).

## Summary Table: Proposed Additions & Removals (Ranked by Refactor Effort / Difficulty)

| Rank (Difficulty) | Feature / Capability | Action | Difficulty Level | Target Phase | Rationale & Reference Comparison |
| :---: | :--- | :---: | :---: | :---: | :--- |
| **1** | **Progressive Skill Disclosure (`use_skill` tool)** | **Add** | Low | v2-S6 / C6 | Single tool schema for skill lookup, keeping tool count within the 20-tool budget (*Hermes Agent pattern*). |
| **2** | **Sliding-Window Circuit Breaker & Crash Recovery** | **Add** | Low | v2-S3 | Protects against API rate limits (429/5xx) and transient errors with auto-backoff (*Grok Build `xai-circuit-breaker` pattern*). |
| **3** | **`sagiha export` SFT/DPO Dataset Exporter** | **Add** | Low-Med | v2-S4 | Converts verified, gate-admitted trajectories into training data for local open-weight models (*AETHER unique feature*). |
| **4** | **Clean Up Legacy Docs & Archived Frontend Specs** | **Remove** | Low-Med | v2-S0 | Archive 7 legacy `sprint-fe-*` docs and duplicate benchmark code (`adapters/benchmark/`), unifying under `e0/`. |
| **5** | **Agent Client Protocol (ACP) Decoupled TUI** | **Add** | Medium | v2-S7 / C1 | Decouples terminal UI (Textual/Ratatui) from the core kernel engine over typed IPC (*Grok Build & OpenCode pattern*). |
| **6** | **Chat-Ops Gateway Adapters (Slack/Discord/Telegram)** | **Add** | Medium | C5 | Enables Mode C A2A / chat-ops delegation with grant-subset envelopes (*Hermes Agent / Moltbot pattern*). |
| **7** | **Rust PyO3 Code Intelligence (`aether-core-rs`)** | **Add** | Med-High | v2-S6 | Offloads Tree-sitter AST parsing, FTS5 chunking, and token counting to Rust via PyO3 for 50x speedups (*Grok Build pattern*). |
| **8** | **Continuous Multi-Agent Swarm Overhead** | **Remove** | High | N/A | Rejects continuous background swarm role-play in favor of System 3 Conductor story-DAG scheduling over the `Orchestrator` port. |

## Executive Summary & High-Level Recommendations

AETHER DAG v2 holds structural advantages in security (CAR capability grants, Podman container sandbox, TaintGate v1) and verification (E0 statistical harness, cassette replay) over Claude Code and Grok Build. To achieve world-class operational excellence, we should adopt **Grok Build's Agent Client Protocol (ACP)** for TUI decoupling, **Hermes Agent's progressive skill disclosure** (`use_skill`) to maintain a lean 20-tool prompt budget, and **PyO3 Rust extensions** for AST parsing. Conversely, we must strip legacy frontend spec debt (`sprint-fe-*`) and avoid unnecessary multi-agent swarm role-play, keeping our architecture lean, deterministic, and high-performance.
