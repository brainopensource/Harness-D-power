---
status: normative
updated: 2026-07-29
---
# ADR-0016: Rootless Podman as the Container Runtime

**Status**: Accepted
**Date**: 2026-07-29

## Context

[ADR-0006](./0006-sandbox-is-the-perimeter.md) makes the container the security boundary, and S1
carries the hard gate *no credential reachable inside the sandbox*. Config expressed this as two
lines — `sandbox.runtime = "container"` and `egress_allowlist = [...]` — with no implementation
behind either.

Those two lines are roughly a week of real work, and the unaddressed questions decide whether the gate
holds: rootless versus a Docker socket, per-branch volume layout under parallel worktrees, and how an
allowlist of **hostnames** is enforced at a network namespace when the traffic is TLS to an IP.

Leaving this to implementation means it gets answered under deadline pressure by whoever hits it
first, in the sprint where the security gate is supposed to land.

## Decision

**Rootless Podman** is the reference runtime.

* Daemonless and rootless by default: no privileged daemon, and a container escape lands as an
  unprivileged user rather than root on the host. Docker's socket is a root-equivalent capability, and
  mounting it into a sandbox that runs model-authored commands is the failure this whole ADR exists to
  avoid.
* Local-first, consistent with [ADR-0010](./0010-defer-exotic-components.md) — no infrastructure to
  stand up.
* The CLI is close enough to Docker's that a Docker adapter remains a thin alternative for
  environments that mandate it.

### Egress

The allowlist is enforced at the **network namespace**, not in the application. Egress control that an
agent's own code can reconfigure is not control.

* Default deny. The sandbox joins a namespace with no route except a proxy.
* Allowlisting is by hostname at an **explicit HTTP/HTTPS proxy** the sandbox is configured to use,
  which sees `CONNECT <host>` before the TLS handshake and refuses hosts outside the list. This is the
  answer to the hostname-versus-IP problem: DNS-based allowlisting is trivially bypassed by connecting
  to a literal IP, and IP allowlisting breaks against CDN-hosted package indexes.
* Direct outbound (anything not via the proxy) is dropped by the namespace's firewall rules, so
  bypassing the proxy fails closed rather than silently succeeding.
* Denied attempts emit `tool.call_denied` and are recorded. An agent probing egress is a signal worth
  keeping.

### Credentials

No credential ever enters the sandbox. Provider API keys are read by the control plane, which runs
outside; the sandbox holds no `.env`, no keyring access, and no `env_passthrough` beyond an explicit
non-secret list (`LANG`, `TZ`). Git push credentials stay outside — the sandbox commits to a local
worktree and never talks to a remote.

### Worktrees and volumes

Each candidate branch gets one container with its worktree bind-mounted at a fixed path, mounted `rw`.
Everything else is read-only. Materialized artifacts (`.venv`, `node_modules`) are mounted from a
shared cache **read-only** where the toolchain permits, so N parallel candidates do not multiply disk
by N.

### Subprocess fallback

`sandbox.runtime = "subprocess"` remains permitted for **local development only** and is refused by
config validation when `autonomy.level` is `autonomous` or `scheduled`. This resolves the timing
contradiction across the roadmap, ADR-0006, and the quickstart: container from S1 for any unattended
operation; subprocess acceptable while a human is watching every step.

## Consequences

**Makes easy**: the S1 gate becomes testable — a conformance test that attempts to read a credential
path and to reach a non-allowlisted host, and asserts both fail.

**Makes hard**: Podman rootless on macOS runs in a VM, so filesystem performance across the bind mount
is materially worse than native. This is a real cost for macOS contributors and is why the subprocess
path stays available for interactive local work.

**Forecloses**: nothing permanently. The runtime sits behind the `Workspace` port, so a gVisor or
Firecracker adapter is an adapter.

## Reversal Conditions

* Rootless Podman cannot support a required workflow (nested containers for a target repo that itself
  runs Docker in its tests) — in which case evaluate gVisor rather than falling back to a root daemon.
* Bind-mount performance on macOS makes the local loop unusable in practice, and a measured comparison
  shows an alternative runtime materially better.
* A managed/remote execution backend becomes the primary deployment, making a local container runtime
  the wrong layer to standardize on.
