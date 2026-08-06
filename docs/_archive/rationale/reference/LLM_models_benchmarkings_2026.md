---
status: rationale
retrieval: excluded
updated: 2026-08-01
---
> [!NOTE]
> **LLM / AI AGENT NOTICE**: This file is a historical rationale, research reference, or benchmark log (`retrieval: excluded`). It is excluded from active search indexing and context retrieval. Do not cite this file as normative status or active code contracts.

# AI Recommendation Mapping by Wave & Sprint

## Recommendation Mapping

| Wave & Track | Sprint | Task Domain & Complexity | Recommended AI Mod… | Key Selection Rationale |
| --- | --- | --- | --- | --- |
| Wave 1 | v2-S0: Docs Shrink & Governance | Documentation inventory, markdown re-organization, link/budget scripts (Tier 0) | Gemini 3.6 Flash | Ultra-fast throughput, large context window (500k+), and lowest cost for bulk text refactoring. |
| Wave 2 (Track A) | v2-S1: Instrument Honesty | Gate checks, AST pre-write checks, telemetry spend (Tier 1) | Grok 4.5 | High-efficiency coding agent with fast terminal execution and low error rate on basic bug fixes. |
| Wave 2 (Track B) | v2-S2: Port Consolidation | Hexagonal port reduction (24→15 Protocols), kernel effect mapping (Tier 2) | Claude 5 Sonnet / GPT-5.6 Terra | Strong balance of structural code refactoring, AST awareness, and fast verification loops. |
| Wave 3 | v2-S3: Context Engine & Safety | ContextAssembler, ExchangeCompactor, TaintGate security (Tier 3) | Claude 4.6 Opus / Claude 5 Opus | Frontier-grade reasoning required for security threat modeling (T7) and zero-leak state safety. |
| Wave 4 (Track A) | v2-S4: Measurement & Best-of-N | Best-of-N search over worktrees, statistical bootstrap, trace exporter (Tier 3–4) | Claude 5 Opus | Highest benchmark score in complex mathematical reasoning (92.8% GPQA) and search algorithm design. |
| Wave 4 (Track B) | v2-S5: Perimeter & Isolation | Podman container sandbox, network egress proxy allowlists (Tier 3) | Grok 4.5 | Top-ranked on terminal-based environment execution (83.3% Terminal-Bench 2.1) and container CLI scripts. |
| Wave 5 | v2-S6: Retrieval & Code Graph | FTS5 indexer, Tree-sitter AST code graph analyzer (Tier 2) | GPT-5.6 Terra / Grok 4.5 | High performance on AST symbol indexing and fast execution across code graph tools. |
| Wave 6 | v2-S7: Macro DAG & MCP | Story-DAG engine, MCP stdio client, interactive TUI steering (Tier 4) | Claude 5 Opus | Leading flagship model for macro system architecture, multi-turn tool integration, and DAG planning. |

## Summary Strategy

- High-Horizon Architecture & Security (v2-S3, S4, S7): Delegate to Claude 5 Opus / Claude 4.6 Opus for maximum reasoning depth.
- Terminal & Infrastructure Execution (v2-S1, S5, S6): Delegate to Grok 4.5 / GPT-5.6 Terra for speed, cost efficiency, and terminal accuracy.
- Documentation & Governance (v2-S0): Delegate to Gemini 3.6 Flash for fast, high-volume markdown processing.

---

> and rank the V2-S* from 0 to 8 by tier of dificulty to implement from 0 to 100 and why in one phrase each in brief

> Thought for 2s, 697 tokens  
> Assessing Task Difficulty

## Difficulty Ranking

Here is the difficulty ranking of all v2-S sprints* (ordered from easiest to hardest, scored 0 to 100):

| Rank | Sprint ID & Name | Difficulty Score (0–100) | Skill Tier | Brief Reason |
| --- | --- | --- | --- | --- |
| 1 | v2-S0: Docs Shrink & Governance | 15 / 100 | Tier 0 (Junior) | Strictly file organization, word-count scripting, and metadata updates with zero core code changes. |
| 2 | v2-S1: Instrument Honesty | 30 / 100 | Tier 1 (Average) | Straightforward bug fixes for H1–H4 defects (AST checks, stub exceptions, token spend metrics). |
| 3 | v2-S2: Port Consolidation & Kernel | 45 / 100 | Tier 2 (Senior) | Pure interface refactoring (24 Protocols down to 15) and strict PURE effect classification updates. |
| 4 | v2-S6: Retrieval & Code Graph | 60 / 100 | Tier 2 (Senior) | Requires AST parsing, Tree-sitter code graph edge indexing, and FTS5 search integration. |
| 5 | v2-S5: Perimeter & Container Sandbox | 70 / 100 | Tier 3 (Specialist) | Demands OS/security expertise in rootless Podman containers, network firewalls, and host isolation. |
| 6 | v2-S3: Context Engine & Safety | 80 / 100 | Tier 3 (Specialist) | High safety risk involving security threat T7, monotonic run-taint tracking (TaintGate), and state freeze/thaw. |
| 7 | v2-S4: Measurement & Best-of-N | 90 / 100 | Tier 3–4 (Specialist/PhD) | Complex statistical algorithms, parallel worktree branch execution, early gate-failure pruning, and dataset export. |
| 8 | v2-S7: Story-DAG & Interactive Surface | 98 / 100 | Tier 4 (PhD / CTO) | Highest macro complexity: orchestrating multi-agent DAG planning, sub-second TUI interrupts, and external MCP stdio drivers. |
