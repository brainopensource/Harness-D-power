---
status: normative
updated: 2026-08-06
---
# ADR-0016: MCP Lands as One Adapter, and Its Output Is Untrusted

**Status**: Accepted · **Date**: 2026-08-06 · **Fork**: raised by the Phase 0 lock audit

**Decided now, built at growth tier.** Deciding costs a page; building prematurely costs
velocity, and [ADR-0005](./0005-eight-ports-adapter-first.md) forbids the port anyway until its
adapter exists. This is the same pattern as [ADR-0007](./0007-architect-editor-seam.md) — settle
the shape, ship nothing — applied at roadmap scale.

## Context

MCP is how external tool ecosystems will reach the harness, and the pressure when it arrives will
be to give it a privileged pathway: its own port, its own registry, its own trust level. That
pressure is worth pre-empting, because every one of those would be a second path around a choke
point that exists to have none.

Two properties make the integration unusually clean if decided in advance. MCP is already
wire-serialized JSON-RPC, so the impedance match with I3's wire-serializable ports is exact. And
an MCP server's tools are already tool descriptors, which is what `ToolRegistry` traffics in.

One property makes it dangerous. MCP servers can change their advertised tool catalog at runtime,
which collides directly with I6 (extension resolution frozen at composition).

## Decision

- **MCP is one adapter behind the existing `ToolRegistry` port.** `McpToolRegistry`. It is not a
  new port, not a growth-tier port, and gets no privileged pathway. A composite registry
  federates it with the built-in tools.
- **Every MCP tool invocation goes through `kernel/dispatch.py`** like any other effect —
  authorize → verify → lease → dispatch → release — with **per-tool capability grants**. An MCP
  server is not granted access as a server; its individual tools are.
- **MCP tool outputs are `untrusted-external`** ([ADR-0015](./0015-taintgate-provenance-model.md)).
  A remote tool is precisely the case the taint model exists for: content the agent did not
  write, arriving over a channel the operator does not control.
- **The catalog is snapshotted at composition, and a refresh is a recomposition.** This preserves
  I6 rather than carving an exception into it. A server that changes its tools mid-run does not
  change what this run may do — a runtime catalog change is otherwise an authorization surface
  that mutates after authorization, which is the exact failure the verify-at-effect step exists
  to catch one layer down.
- **Entry per [ADR-0005](./0005-eight-ports-adapter-first.md):** the adapter lands with its
  conformance test against the existing `ToolRegistry` suite. No new protocol enters `ports/`.

## Consequences

- MCP costs one adapter and zero architectural change, which is the evidence that the port
  boundary was drawn in the right place.
- Tool schemas are paid for on every model call, so a large federated catalog is a real token
  cost. On-demand schema loading is an optimization admitted like any other — behind an ablation,
  not by assumption.
- A misbehaving MCP server degrades to a denied effect and a typed error. It cannot escalate,
  because it never held a grant broader than the tool being called.

## Reversal Conditions

If a class of MCP capability genuinely cannot be expressed as a `ToolRegistry` tool descriptor —
bidirectional streaming, or a server-initiated interaction — that is evidence the boundary is
wrong, and it reopens **as a port question** under ADR-0005, with its first adapter named.

**Not reversible:** the untrusted labelling of MCP output, and dispatch through the choke point.
Those follow from I5 and [ADR-0015](./0015-taintgate-provenance-model.md), and this ADR has no
authority to weaken either.
