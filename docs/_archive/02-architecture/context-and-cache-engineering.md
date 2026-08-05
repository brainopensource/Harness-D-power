---
status: historical
updated: 2026-07-29
---
# **Context & Cache Engineering**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **The Cache Constraint**

Prompt caching requires a **byte-identical prefix**. Dynamic token percentage reallocation per turn breaks the prefix and forfeits cache on every call. **Order by stability, not by budget share.**

## **Layered Assembly**

Context is assembled in order of decreasing stability to keep token growth append-only:

| Layer | Contents | Change Frequency |
| :---- | :---- | :---- |
| **Stable prefix** | System instructions, tool schemas, project conventions | Once per session |
| **Semi-stable** | Retrieved repository context for current task | Only when task retrieval changes |
| **Append-only tail** | Conversation, tool calls, observations | Every turn (appended) |

### Layer 6 Retrieval is Seed-Only

Pre-assembled retrieval occurs strictly once at task start. Subsequent retrieval is agentic (e.g., via `grep`, `find_symbols`, `get_skeleton`) and appends to the tail.

* **Enforced by Structure**: `ContextAssembler` accepts `retrieval_seed` exclusively at construction.
* **Enables Interrupt-and-Steer (`v2-S7`)**: Steering appends to the tail while layers 1–7 remain byte-identical.
* *References: [ADR-0021](../08-decisions/0021-seed-only-layer-6-retrieval.md), landing in `v2-S3` (PR-3.1).*

## **Compaction Strategy**

Compaction is an explicit checkpoint on task boundaries or headroom thresholds, not a continuous process. It resets the cache once to reclaim window headroom.

## **Lossless Compression & Re-Hydration**

* **AST Skeletonization**: Strip function bodies; keep interfaces, signatures, attributes, and docstrings.
* **Symbol Context Injection**: Inject scope-local definitions, imports, caller/callee signatures.
* **Log Condensation**: Collapse repetitive whitespace, duplicate tracebacks, and spinners.
* **Staged Re-Hydration**: If compilation or tests fail post-compaction, affected files are re-inserted in full before retrying.

## **Reasoning & Tool Discipline**

* **Reasoning Blocks**: Extended thinking payload is stored as opaque `ReasoningBlock` and round-tripped verbatim to preserve provider signatures and cache hits (with a separate `summary` field for display).
* **Tool Output Discipline**: `ToolResult` includes `truncated` and `full_output_uri` fields so the model explicitly handles truncated output.

## **Metrics**

Every run tracks token consumption alongside **cache hit rate**.
