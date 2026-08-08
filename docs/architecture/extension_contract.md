---
status: rationale
updated: 2026-08-07
---

# Extension Contract — Building on AETHER Without Forking

**Design of record for M5.** Ratified by
[ADR-0021](../decisions/0021-extension-contract-and-trust.md).

Today there is no extension mechanism. Adding a role, a retrieval strategy or a tool means
editing `src/aether/` and opening a PR against this repository. Every surveyed competitor solved
this declaratively; this document is how we do it **without handing away the property that makes
our numbers mean anything.**

---

## 1. The four tiers

| Tier | You ship | Form | Reviewed by | May widen capability? |
| :--- | :--- | :--- | :--- | :---: |
| **T0** Parameters | Prompts, retrieval params, budgets | Values in a topology or role file | Nobody — it is data | **No** |
| **T1** Roles | A `RoleSpec`: sources, parser, role prompt | YAML naming **registered** ids | Nobody — it is data | **No** |
| **T2** Topologies & fragments | Node composition | YAML, hash-pinned | Validator (5 static checks) | **No** |
| **T3** Capabilities | A `ContextSource`, `Inference`, `OutputParser`, tool, adapter | Python class + registry entry | **Human PR** | Yes — hence the review |

> **The load-bearing rule: T0–T2 are data, and data cannot widen capability.**
>
> A role file *names* a `ContextSource` by registered id; it cannot define one. A topology
> *names* a strategy; it cannot define one. Registries are frozen at composition (I6), so the
> set of things data can reach is fixed before any task runs.

That sentence is the whole security argument. It is also why T0–T2 is exactly the meta-loop's
mutable surface under ADR-0006 — **the extension contract and the meta-loop's authority boundary
are the same line viewed from two sides.** Getting one right gets the other free.

**`Verdict` appears in no tier.** Its registry is closed by
[ADR-0020](../decisions/0020-verdict-capability-and-judge-integrity.md). A judge is never an
extension, because an extension that supplies the judge grades its own work.

---

## 2. What a T1 role looks like

```yaml
# extensions/acme-rag/roles/acme_explorer.yaml
role_id: acme_explorer
extends: editor                      # inherit, then override — Kimi's `extend:` pattern
role_prompt: |
  You answer questions about a codebase. Cite every claim with file:line.
sources:                             # REGISTERED IDS ONLY — cannot define a new one
  - { id: symbol_source,  params: { max_symbols: 40 } }
  - { id: lexical_source, params: { max_hits: 20 } }
  - { id: graph_source,   params: { hops: 2, max_bytes: 8000 } }
parser: { id: cited_answer_parser }
effects: [ read, model ]             # ceiling, enforced by attenuation — not a comment
```

A validator rejects this at **load** if `acme_explorer` names an unregistered source, parser or
effect — the same fail-at-construction discipline as `UnknownEditFormat` and
`UnregisteredNodeKind`. *A benchmark that fails on iteration three of task forty because an id
was never registered has already burned the run.*

`effects` is enforced by **capability attenuation** (`TASK-068`, ADR-0017): the `DispatchFacade`
handed to this role is narrowed to `{read, model}` at construction. A role declaring
`[read, model]` **cannot write even if it tries** — denied at the choke point, by type, not by
trust.

---

## 3. The package

```
acme-rag/
├── aether-extension.yaml
├── roles/       acme_explorer.yaml            # T1
├── topologies/  acme_rag_v1.yaml              # T2
├── skills/      SKILL.md files                # T0 — prompt fragments
└── src/         acme/sources.py:GraphSource   # T3 — needs human review
```

```yaml
extension_id: acme-rag
version: 1.2.0
provides:
  roles:        [ acme_explorer ]
  topologies:   [ acme_rag_v1 ]
  capabilities: [ acme.sources:GraphSource ]
requires:
  aether: ">=3.1,<4"
  capabilities: [ symbol_source, entry_file_source ]
effects: [ read, model ]
```

`requires.capabilities` is what makes an extension fail loudly on an AETHER that lacks a source
it depends on, instead of degrading silently into a worse prompt.

---

## 4. Install ≠ trust ≠ enable

Three independent states. Conflating them is how a marketplace becomes an attack surface.

| State | Means | Grants |
| :--- | :--- | :--- |
| **Installed** | Files on disk | Nothing |
| **Trusted** | An operator decision, recorded with source, version and **content hash** | T3 capabilities may load |
| **Enabled** | Named by a `RunConfig` | It participates in this run |

- **T0–T2 may load untrusted** — data cannot widen capability, so there is nothing to gate.
- **T3 does not load until trusted.** Untrusted, the extension still contributes its roles and
  topologies; its Python simply is not imported.
- **Trust is granted to a content hash, never to a name.** A trusted extension whose content
  changes reverts to untrusted.

That last rule is not theoretical. `claude_refs/guide/security/security-hardening.md` catalogues
**655 malicious skills** against a live marketplace, and the attack is precisely
trust-by-name-then-mutate. Grok separates the two axes explicitly (`grok plugin install X`
without `--trust` prints the source and stops); we adopt it.

---

## 5. What an extension may never do

| Forbidden | Enforced by |
| :--- | :--- |
| Provide a `Verdict` | Closed registry (ADR-0020) |
| Provide an `ExecutionStrategy` or a validator check | TCB; `tcb-isolation` + `TCB_PATHS` |
| Touch `kernel/`, `measurement/`, `workflow/{executor,validator}.py`, schemas, CI | `tcb-isolation`, `TCB_PATHS`, human review |
| Widen its declared `effects` | Attenuation at construction (ADR-0017) |
| Register anything at runtime | I6 — frozen at composition |
| Ship a number | ADR-0002; an extension is a mechanism |

**An extension is a mechanism, so it does not promote without an ablation** (`spec.md` §7). A
community role that does not clear the floor is not shipped-and-ignored — it is not admitted.
Extension ids, versions and content hashes enter `sha256(RunConfig)`, or a run using them is not
reproducible (`measurement.md` §6).

---

## 6. Third-party code, in ascending isolation

There is **no in-process plugin ABI** — no dynamic loader, no `entry_points` scan, no runtime
registration. That would contradict I6 and hand the meta-loop rung 4 (arbitrary code) while
looking like rung 3 (data).

1. **A registered capability class** in a trusted extension. T3, human-reviewed, in-process.
2. **An MCP server** — already one adapter of the existing `ToolRegistry` port (ADR-0016), no
   new port, outputs labelled `UNTRUSTED_EXTERNAL` at construction.
3. **An out-of-process sidecar** speaking the JSON contract the ports already imply (I3) —
   Rust, Go, anything. `composition.py` binds an effect to a `SidecarClient` instead of a Python
   adapter; the node, the executor, the topology and the port are unchanged.

Option 3 is where the "Rust or Go for small nodes" goal lands, and it costs nothing new: the
conformance suite is already parametrized over adapters, so **a sidecar becomes one more adapter
parameter in the existing suite** — the strongest available guarantee that it behaves identically.

---

## 7. What we took, and the one thing we added

| From | Idea |
| :--- | :--- |
| Kimi CLI | YAML agent spec with `extend:`; tools as dotted `module:Class` with type-keyed DI (`agentspec.py`, `soul/toolset.py:683-714`) |
| Grok | Skills as markdown frontmatter; layered discovery; **`install ≠ trust`**; `grok inspect` as a capability-introspection endpoint |
| OpenHands | Server-driven settings schema — new backend config renders UI with no client change; open `string` for extension dimensions rather than closed unions |
| Claude Code corpus | The marketplace threat model — 655 malicious skills |

**What none of them has, and we do: `data cannot widen capability`.** They did not need it,
because none of them has a meta-loop proposing extensions or a measurement protocol those
extensions could corrupt. We have both, so the tier boundary is not a convention — it is the
thing that keeps H3 safe.

## 8. Reversal

If no third-party extension exists six months after M5, this contract has one user and folds
back into composition. If an extension ever provides a `Verdict`, a strategy or a TCB file, the
mechanism is withdrawn rather than patched.
