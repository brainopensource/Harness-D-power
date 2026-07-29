# **Interoperability Protocols: MCP & A2A**

> [!NOTE]
> **Working Proposal Disclaimer**: This document represents a working architectural proposal for SAGIHA2 and will be iteratively refined as practical evaluations progress.

## **Protocol Axis Separation**
* **Model Context Protocol (MCP)**: Universal vertical integration layer connecting single agents to local host tools, filesystems, language servers, and databases via JSON-RPC 2.0 (Stdio pipe or HTTP-SSE).
* **Agent-to-Agent Protocol (A2A)**: Universal horizontal collaboration layer enabling inter-agent task delegation, peer discovery (`/.well-known/agent-card.json`), task state machine lifecycle management, and cross-system streaming.
