---
status: rationale
updated: 2026-07-29
retrieval: excluded
---
# **Interoperability Protocols: MCP & A2A**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Protocol Axis Separation**

* **Model Context Protocol (MCP)** — vertical integration: one agent to local tools, filesystems, language servers, and databases via JSON-RPC 2.0 over stdio or HTTP-SSE.
* **Agent-to-Agent (A2A)** — horizontal collaboration: inter-agent delegation, peer discovery via `/.well-known/agent-card.json`, task lifecycle state machine, cross-system streaming.

## **Adoption Sequencing**

**MCP is adopted at Day 0** (stdio drivers), because tool integration is immediately load-bearing.

**A2A is deferred until a genuinely remote peer agent exists.** Sub-agents on the same host are function calls behind the `Orchestrator` port, and wrapping them in HTTPS, JSON-RPC, and agent cards adds serialization overhead and operational surface to solve a distribution problem the system does not have. The trigger is a real remote peer, not a phase boundary.

## **Consequences for the Tool Contract**

Because tools are discovered dynamically from MCP servers, the tool namespace must be **open**. `ToolCall.tool_name` is a string validated against the registry at dispatch, not a closed enum. The previous `ActionType` enum with six fixed members could not represent a newly discovered MCP tool at all — a direct contradiction of the "every capability is an MCP server" premise stated elsewhere in the same document.

Likewise, MCP returns **typed content blocks** including images and resource references, so `ToolResult.content` is a `list[ContentBlock]` rather than a stringified `output`. Flattening to a string discards structure the protocol went to the trouble of providing.

## **Security Posture at the Protocol Boundary**

An MCP server is a third-party dependency running with the agent's access, and its output enters the model's context. Two rules apply:

* **Tool output is data, never instruction.** Content returned by an MCP server carries no authority, exactly as with repository and web content. A malicious or compromised server is an injection vector.
* **Every dispatch requires a `Grant`.** MCP servers do not receive ambient authority; they receive scoped, expiring capability tokens like any other Runtime path. Tool descriptions supplied by a server are themselves untrusted content.

## **Transport Notes**

For co-located processes, prefer the simplest transport that works — stdio pipes, or length-prefixed msgpack over a Unix domain socket. gRPC brings protobuf schema management and a threading model that fights asyncio; it is warranted when a second consumer or a genuinely remote peer appears, not before.
