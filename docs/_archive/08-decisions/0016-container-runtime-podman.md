---
status: normative
updated: 2026-07-29
---
# ADR-0016: Rootless Podman as the Container Runtime

**Status**: Accepted  
**Date**: 2026-07-29  

## Context

[ADR-0006](./0006-sandbox-is-the-perimeter.md) establishes the container as the security boundary, with the S1 gate mandating *no credential reachable inside the sandbox*. Configuring container execution requires resolving rootless isolation, per-branch volume layouts, and hostname-level egress enforcement.

## Decision

**Rootless Podman** is selected as the reference runtime.

- **Daemonless & Rootless**: Eliminates privileged daemons; container escapes land as unprivileged host users. Avoids Docker socket exposure.
- **Local-first**: Aligns with [ADR-0010](./0010-defer-exotic-components.md) without extra infrastructure overhead.
- **Docker CLI compatibility**: Retains CLI compatibility for thin Docker adapters when required.

### Egress Enforcement

Egress control is enforced at the **network namespace** level (default deny):
- **Explicit HTTP/HTTPS Proxy**: Resolves hostname vs. IP allowlisting by validating `CONNECT <host>` before TLS handshakes.
- **Drop direct outbound**: Non-proxy outbound traffic is dropped by firewall rules.
- **Auditing**: Denied outbound attempts emit `tool.call_denied` events.

### Credentials

No credentials enter the sandbox. API keys and Git push credentials remain in the host control plane. The sandbox holds no `.env` files or keyring access, passing only non-secret environment variables (`LANG`, `TZ`).

### Worktrees and Volumes

Each candidate branch gets a container with its worktree bind-mounted `rw` at a fixed path; all other mounts are read-only. Materialized artifacts (`.venv`, `node_modules`) are mounted read-only from a shared cache.

### Subprocess Fallback

`sandbox.runtime = "subprocess"` is permitted for **local interactive development only** and rejected by validation if `autonomy.level` is `autonomous` or `scheduled`.

## Consequences

- **Easy**: Enables testable S1 security gates (verifying credential isolation and egress blockage).
- **Hard**: macOS performance is impacted by VM bind mounts.
- **Forecloses**: Nothing; runtime sits behind `Workspace` port (e.g., gVisor/Firecracker adapters can be added).

## Reversal Conditions

- Rootless Podman cannot support required workloads (e.g., nested containers).
- macOS bind mount performance proves unusable in practice relative to alternatives.
- Execution model shifts primarily to managed/remote backends.
