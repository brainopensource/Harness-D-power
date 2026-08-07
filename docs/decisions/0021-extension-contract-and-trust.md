---
status: normative
updated: 2026-08-07
---
# ADR-0021: The Extension Contract — Capability Is Declared, and Install Is Not Trust

**Status**: Accepted · **Date**: 2026-08-07 · **Fork**: raised by [ADR-0019](./0019-three-horizons-harness-framework-metaloop.md)

## Context

[ADR-0019](./0019-three-horizons-harness-framework-metaloop.md) commits to a framework others
build on. Today there is **no extension mechanism at all**: adding a role, a retrieval strategy
or a tool means editing `src/aether/` and opening a PR against this repo.

Every surveyed competitor solved this, and each solved it declaratively:

| System | Mechanism | Evidence |
| :--- | :--- | :--- |
| Kimi CLI | YAML `AgentSpec` with `extend:`, `allowed_tools`, `exclude_tools`, `subagents`; tools as dotted `module:Class` paths resolved with type-keyed DI | `agentspec.py`, `soul/toolset.py:683-714` |
| Grok | Skills as `SKILL.md` frontmatter; plugin marketplace bundling skills + commands + agents + hooks + MCP | `docs/user-guide/08-skills.md`, `09-plugins.md` |
| OpenHands | ACP — any stdio subprocess is an agent, selected by one config string | `docs/ACP_AGENTS.md` |

Two design points recur and both are worth adopting:

1. **Capability is declared in files, never coded.** The same declaration drives both the human
   surface and the model's auto-invocation surface, via independent flags.
2. **Grok separates `install` from `trust`.** A plugin's hooks and MCP servers stay inert until
   explicitly trusted; `grok plugin install X` without `--trust` prints the source and stops.

That separation is not paranoia. `claude_refs/guide/security/security-hardening.md` catalogues
**655 malicious skills** against a live marketplace. **An extension marketplace is an attack
surface**, and this project's threat model already assumes the agent is an untrusted actor
executing code it wrote over content it did not write.

## Decision

### 1. Four extension tiers, and the boundary between data and code

| Tier | What a third party ships | Form | Who may add it |
| :--- | :--- | :--- | :--- |
| **T0 — Parameters** | Prompt text, retrieval params, budgets | Values in a topology or role file | Meta-loop (ADR-0006) |
| **T1 — Roles** | A `RoleSpec`: source list, parser, role prompt | YAML naming **registered** capability ids | Meta-loop, ancestry-tracked |
| **T2 — Topologies & fragments** | Node composition | YAML, hash-pinned (ADR-0014) | Meta-loop |
| **T3 — Capabilities** | A `ContextSource`, `Inference`, `OutputParser`, tool, adapter | **Python class + registry entry** | **Human PR only** |

> **The load-bearing rule: T0–T2 are data, and data cannot widen capability.**
>
> A role file *names* a `ContextSource` by registered id; it cannot define one. A topology
> *names* a strategy; it cannot define one. Registries are frozen at composition (I6), so the
> set of things data can reach is fixed before any task runs. This is what keeps the meta-loop's
> grant small — and it is the property none of the surveyed systems has, because none of them
> needed it.

**`Verdict` is deliberately absent from every tier.** Its registry is closed by
[ADR-0020](./0020-verdict-capability-and-judge-integrity.md); a judge is never an extension.

### 2. Extensions are packages with a manifest

An extension is a directory with `aether-extension.yaml`:

```yaml
extension_id: acme-symbol-retrieval
version: 1.2.0
provides:
  roles:        [ acme_explorer ]        # T1 — YAML RoleSpecs
  topologies:   [ acme_rag_v1 ]          # T2 — hash-pinned
  capabilities: [ acme.sources:GraphSource ]   # T3 — requires human review
requires:
  aether: ">=3.1,<4"
  capabilities: [ symbol_source, entry_file_source ]
effects: [ read, model ]                 # the maximum this extension may request
```

`effects` is a **declared ceiling, enforced by attenuation** (`TASK-068`, ADR-0017): the
`DispatchFacade` handed to anything this extension provides is narrowed to that set at
construction. An extension declaring `[read, model]` cannot write, even if it tries — denied at
the choke point, by type.

### 3. Install ≠ trust ≠ enable

Three independent states, following grok's separation:

- **Installed** — files on disk. Grants nothing.
- **Trusted** — an operator decision, recorded with the source, the version and a content hash.
  **T3 capabilities do not load until trusted.** T0–T2 may load untrusted, because data cannot
  widen capability.
- **Enabled** — named by a `RunConfig`. An installed, trusted extension still does nothing until
  a run asks for it.

A trusted extension whose content hash changes reverts to untrusted. Trust is granted to a
version, never to a name.

### 4. Extensions may not touch the TCB, and are measured like anything else

- No extension may provide a `Verdict`, a strategy, a validator check, or anything under
  `kernel/`, `measurement/`, `workflow/executor.py`, `workflow/validator.py`, the schemas, or CI.
  `tcb-isolation` enforces the import direction; `TCB_PATHS` enforces the file set.
- **An extension is a mechanism, so it does not promote without an ablation** (`spec.md` §7). A
  community role that does not clear the floor is not shipped-and-ignored; it is not admitted.
- Extension identity enters the instrument tuple: a run using extensions records their ids,
  versions and content hashes in `sha256(RunConfig)`, or the run is not reproducible
  (`measurement.md` §6).

### 5. No in-process plugin ABI

Third-party **code** arrives one of three ways, in ascending order of isolation:

1. A registered capability class in a trusted extension (T3, human-reviewed).
2. An **MCP server** — already one adapter of the existing `ToolRegistry` port (ADR-0016),
   outputs labelled `UNTRUSTED_EXTERNAL` at construction.
3. An **out-of-process sidecar** speaking the JSON contract the ports already imply (I3).

There is no dynamic plugin loader, no `entry_points` scan, no runtime registration — that would
contradict I6 and hand the meta-loop rung 4 (arbitrary code) while looking like rung 3 (data).

## Consequences

**Positive.** Community contribution becomes a mechanism. The meta-loop's search space (T0–T2)
is exactly the space that cannot widen capability, so ADR-0006's authority boundary and this
contract are the same line viewed from two sides. Attenuation gives extensions a real,
type-enforced ceiling.

**Negative, and accepted.** A manifest format, a trust store and an attenuating facade are real
work with no benchmark payoff. Requiring human review for T3 caps community velocity — and that
is the intended trade.

**Neutral.** Nothing changes for a run using no extensions.

## Reversal conditions

- **If no third-party extension exists six months after M5**, the contract has one user and its
  machinery folds back into composition.
- **If any extension ever provides a `Verdict`, a strategy or a TCB file**, this ADR failed and
  the mechanism is withdrawn, not patched.
- **If trust is ever granted to a name rather than a content hash**, revert — that is the exact
  shape of the 655-malicious-skill attack.
- **If an extension's declared `effects` ceiling is not enforced by attenuation** but only by
  convention, the tier system is decorative and should be deleted rather than believed.

## References

- [ADR-0019](./0019-three-horizons-harness-framework-metaloop.md) · [ADR-0020](./0020-verdict-capability-and-judge-integrity.md)
- [ADR-0006](./0006-tcb-boundary-and-meta-loop-authority.md) — the meta-loop's mutable surface, which T0–T2 mirror
- [ADR-0016](./0016-mcp-integration-trust-model.md) · [ADR-0017](./0017-subagent-capability-attenuation.md)
- [`architecture/extension_contract.md`](../architecture/extension_contract.md) — the design detail
