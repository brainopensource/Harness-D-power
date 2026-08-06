---
status: normative
updated: 2026-08-05
---
# ADR-0008: Shell AST Analysis Classifies; the Sandbox Contains

**Status**: Accepted · **Date**: 2026-08-05 · **Fork**: F8

## Context

**The mechanism was never contested. The claim attached to it was.**

One proposal specified a shell command AST parser and described it as *"eliminating
security bypasses based on regex"*. The other agreed the parser is worth building but
insisted the container sandbox is the security boundary and the parser is a classifier.

Parsing a shell command tells you what it *appears* to do. It does not constrain what it
*can* do — command substitution, indirection through a variable, an interpreter invoked on
attacker-controlled input, and a dozen other paths defeat static analysis of a shell string.
Treating the parser as containment is how the real containment gets deprioritised.

## Decision

- **Build the parser.** Shell commands are parsed to an AST before execution.
- **Its purpose is classification and escalation, never containment.** It maps a command to
  an effect classification and drives the `Reject | AskRuleMatch | AskFailClosed` taxonomy.
- **The container sandbox is the perimeter.** Deny-by-default egress; the agent reaches the
  host or the network only through an audited path.
- No security claim is made for the parser in any document, ADR or commit message.

## Consequences

- A defeated parse produces a wrong *classification*, which is an escalation bug. It does not
  produce a container escape.
- Auto-denial is bounded: **3 consecutive / 20 total** denials, after which the run halts
  rather than looping. An unbounded denial loop is its own denial of service.

## Reversal Conditions

**None on the deny-by-default posture.** Individual allowlist entries are always revisable
with an audit trail. If a second containment mechanism is ever proposed, it is evaluated on
the understanding that a second security mechanism is a second thing to get right.
