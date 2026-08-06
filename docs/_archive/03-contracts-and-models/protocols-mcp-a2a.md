---
status: rationale
updated: 2026-07-29
retrieval: excluded
---
# **Interoperability Protocols: MCP & A2A**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Protocol Axis Separation**

* **Model Context Protocol (MCP)**: Vertical integration between agent and local tools, filesystems, LSPs, and databases via JSON-RPC 2.0 (stdio or HTTP-SSE).
* **Agent-to-Agent (A2A)**: Horizontal inter-agent collaboration, peer discovery (`/.well-known/agent-card.json`), task state machines, and remote streaming.

## **Adoption Sequencing**

* **MCP (Day 0)**: Implemented immediately for stdio tool integration.
* **A2A (Deferred)**: Deferred until remote peer agents are required. Co-located sub-agents execute as function calls behind the `Orchestrator` port.

## **Tool Contract Impact**

* **Open Namespace**: `ToolCall.tool_name` is a dynamic string validated against the registry at dispatch, not a fixed enum.
* **Rich Content**: `ToolResult.content` is `list[ContentBlock]` to preserve structured MCP returns (images, resources).

## **Security Posture & Transport**

* **Untrusted MCP Output**: MCP server responses carry no authority and are wrapped in `<untrusted-data>` blocks.
* **Grant Authorization**: Every MCP tool dispatch requires a scoped `Grant`.
* **Transport**: Co-located processes use stdio or Unix domain sockets (msgpack). gRPC is reserved for remote networking.
