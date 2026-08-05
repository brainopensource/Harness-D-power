---
status: historical
updated: 2026-07-29
---
# ADR-0006: The Sandbox Is the Security Perimeter

**Status**: Accepted  
**Date**: 2026-07-28

## Context
Command blocklisting (`rm -rf`) fails against subshells (`bash -c`), encoded strings, symlinks, or alternate interpreters. Git worktrees isolate tracked files but do not provide execution isolation.

## Decision
- Container / gVisor boundaries form the security perimeter (required from slice S1).
- Credentials are held outside the sandbox; network egress is allowlisted at the network namespace.
- Command blocklists serve only as usability guardrails, never security controls.
- `run_command` accepts `argv` as `list[str]`, never shell strings.
- Unsandboxed local `subprocess` mode is allowed for dev only, prohibited during autonomous execution.

## Consequences
- Requires container runtimes (Podman/Docker) for autonomous execution.
- Ensures verifiable isolation.

## Reversal Conditions
- None for perimeter isolation. (Container runtime implementations may evolve).
