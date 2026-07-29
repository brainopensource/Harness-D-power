# SAGIHA — Super AGI Harness Agent v0.0.1

SOTA autonomous coding harness with a microkernel, capability security, and verification gates.

SAGIHA is built on the CAR model (Control / Agency / Runtime): every tool dispatch flows through
a single choke point authorized by a `PolicyEngine`, hexagonal ports keep the domain independent
of any specific backend, and every port ships with a behavioral conformance suite before it is
considered supported.

## Status

Pre-alpha. The architecture and contracts are specified in [`docs/`](docs/); implementation is
in progress following the sprint sequence in
[`docs/07-roadmap/phased-migration-matrix.md`](docs/07-roadmap/phased-migration-matrix.md).

## Development

```sh
uv sync
uv run pytest tests/contracts/
uv run pyright
uv run lint-imports
```

See [`AGENTS.md`](AGENTS.md) for the architectural invariants and codebase conventions, and
[`docs/06-guides-and-patterns/getting-started.md`](docs/06-guides-and-patterns/getting-started.md)
for a full walkthrough.
