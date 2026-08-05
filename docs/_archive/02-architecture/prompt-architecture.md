---
status: historical
updated: 2026-07-29
---
# **Prompt Architecture**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Prompt Layout**

Prompt context is structured by strictly decreasing stability (see [Context & Cache Engineering](./context-and-cache-engineering.md)):

```
┌─ STABLE PREFIX ─────────────────────── cached, byte-identical across turns ─┐
│ 1. Role & operating contract                                               │
│ 2. Tool schemas                    (from ToolRegistry, canonical order)   │
│ 3. Safety & trust framing          (<untrusted-data> envelope enforcement) │
│ 4. Project conventions             (AGENTS.md / CLAUDE.md, verbatim)       │
├─ SEMI-STABLE ──────────────────── changes only when retrieval changes ─────┤
│ 5. Task spec + acceptance criteria                                         │
│ 6. Retrieved repository context    (AST-bounded chunks, skeletons)         │
│ 7. Active plan state               (update_plan contents)                  │
├─ APPEND-ONLY TAIL ──────────────────────── grows, never rewritten ─────────┤
│ 8. Conversation, tool calls, observations, diagnostics                     │
└────────────────────────────────────────────────────────────────────────────┘
```

Cache breakpoints close Layers 4 and 7.

## **Layer Specification**

1. **Role & Operating Contract**: (~400 tokens) Defines agent persona, verification requirement, code-intelligence preference, and acceptance criteria rules.
2. **Tool Schemas**: Deterministic, canonically ordered schema definitions emitted by `ToolRegistry`. See [Tool Catalog](../03-contracts-and-models/tool-catalog.md).
3. **Safety & Framing**: Enforces `<untrusted-data>` wrapping around external payloads and specifies actions requiring human approval.
4. **Project Conventions**: Repository `AGENTS.md` injected verbatim.
5. **Task Spec & Acceptance Criteria**: Explicit target goals and machine-checkable test rules.
6. **Retrieved Context**: Tree-sitter AST chunks and symbol skeletons.
7. **Active Plan State**: Persistent step state anchoring context across compactions.
8. **Append-Only Tail**: Turns and tool results. Reasoning blocks are transported as opaque provider payloads (`ReasoningBlock`).

## **Exchange-Granular Compaction**

Compaction operates over complete **exchanges** (assistant call + tool results + reasoning block) to prevent orphaned IDs:

| Parameter | Default | Description |
| :--- | :--- | :--- |
| **Headroom %** | `20%` | Triggers compaction when available context headroom falls below 20%. |
| **`keep_first_exchanges`** | `2` | Preserves the first 2 exchanges verbatim to keep initial task framing. |
| **`keep_last_tokens`** | `24_000` | Preserves the most recent full exchanges fitting in 24k tokens. |

* **Compaction Event**: Replaced turns yield a `CompactionApplied` event.
* **Taint Preservation**: Tainted exchanges re-wrap summaries in `<untrusted-data>` per [Threat T7](./security-and-threat-model.md).
* **Implementations**: `TruncatingCompactor` (deterministic default) and `ModelCompactor`.

## **Sub-Agent Prompts & Governance**

* **Sub-Agents**: Prompts assemble with narrowed tool access, dedicated task specs, and isolated conversation tails.
* **Versioning**: Prompt templates stored in `src/sagiha/prompts/`. Layer 3 safety framing belongs to the Trusted Computing Base (TCB) and is exempt from outer-loop self-modification ([RHI Outer Loop](../04-workflows-and-loops/rhi-outer-loop.md)).
