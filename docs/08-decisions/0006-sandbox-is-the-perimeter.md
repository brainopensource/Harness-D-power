---
status: normative
updated: 2026-07-29
---

# ADR-0006: The Sandbox Is the Security Perimeter

**Status**: Accepted
**Date**: 2026-07-28

## Context
The original security model was a "command sanitizer" checking shell strings against a policy matrix, blocking things like `rm -rf`. Blocklisting shell strings fails to `bash -c`, `python -c`, base64 payloads, `$IFS` substitution, symlink indirection, and any interpreter already in the image. Containers were also scheduled at Day 2, while a Day-1 gate claimed "zero cross-branch state contamination" — unreachable, since worktrees isolate tracked files and nothing else.

## Decision
The container (or gVisor) boundary is the security perimeter, required from slice S1. Credentials never enter the sandbox. Egress is allowlisted at the network namespace. Command blocklisting is retained only as a usability guardrail and is never relied upon as a control. `run_command` takes `argv` as a list, never a shell string.

## Consequences
A container runtime becomes a prerequisite for meaningful autonomy, which raises the setup bar. In exchange the isolation claims become true, and the six-threat model in the security module has a mechanism behind each mitigation. Local `subprocess` mode remains available for development and is refused under autonomous or scheduled autonomy.

## Reversal Conditions
None for the perimeter itself. The specific runtime (Docker vs Podman vs gVisor) is an implementation choice that may change.
