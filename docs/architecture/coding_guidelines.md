---
status: rationale
updated: 2026-08-07
---

# Coding Guidelines — House Rules and Patterns

**Read this before your first PR.** Every rule below was learned by something going wrong, and
each names what went wrong so you can tell when the rule stops applying.

This is the *how*. The *what* is [`spec.md`](../spec.md); the *why* is
[`decisions/`](../decisions/README.md); the *shapes* are
[`core_skeletons_and_protocols.md`](../architecture/core_skeletons_and_protocols.md).

---

## 1. Non-negotiable

### 1.1 No `--force`, no escape hatch, ever

The topology validator, the manifest validity gate and the family gatekeeper exist so a failing
check **cannot** be bypassed. If a check is inconvenient, fix what it is checking.

### 1.2 Every gate ships with a test proving it can fail

The founding rule ([`vision.md`](../vision.md) §4). The predecessor's gates silently passed over
broken instruments three separate times. A gate that cannot fail is the most expensive bug this
project can have — and it is not hypothetical here:

- `.importlinter` contracts that select **zero modules** pass green and forbid nothing.
- `docs_budget.py` used to `return 0` before any check when `--max` was omitted, so its bare
  invocation printed a list of failures and exited 0.
- I7's `tests_unmodified` was named in `spec.md` §2 as I7's mechanism and returned nothing under
  `grep` for four sprints.

**Before calling any task done, ask: what would make this gate go red, and is there a test that
does it?**

### 1.3 Fail at load, not at the node's turn

`UnknownEditFormat` and `UnregisteredNodeKind` both raise **at construction**. The reason is
stated in `executor.py:124-131`: *a benchmark that fails on iteration three of task forty because
a kind was never registered has already burned the run.* Every registry added since follows this.

### 1.4 `GateStatus.NONE` is not `FAILED`

`NONE` means *unmeasured*. It is **excluded from the resolve-rate denominator** and reported
separately as an instrument-error rate. If you write `if not passed: repair()` you have merged
them — use the tri-state.

A corollary that is easy to get backwards: a candidate that tampered with its own tests is
`NONE`, **not** `FAILED`. We do not know whether its code was correct, only that we cannot score
it. Mapping it to `FAILED` would make tampering *costly*, which sounds like a deterrent and is
actually a measurement error.

### 1.5 TCB residency is a contract, not a convention

**The implementations of TCB ports live inside TCB paths.** `PolicyEngine` in `kernel/`,
`Evaluator` in `measurement/`. **Never in `adapters/`.** That residency is what makes
`import-linter`'s `tcb-isolation` *select* the module at all. Check `.importlinter` before you
write a module, not after CI fails.

### 1.6 A number without its instrument tuple is not a result

Manifest hash · split · model fingerprint · topology hash · container digests · lockfile hash ·
seed. Every one, every time ([`measurement.md`](../measurement.md) §6).

### 1.7 A mechanism that raises the win rate must extend the validity guards in the same change

Sprint 3.5's lesson, and the reason Sprint 4 exists. It added a system layer, an edit-format seam
and repair context re-reading — all real improvements — while I7 went unenforced and the
baseline was contaminated by injecting the test source into the prompt. **The win rate went up
and the measurement stopped meaning anything.**

### 1.8 TCB data changes cascade — check what pins the hash

The manifest is TCB data; a change is a **new manifest with a new hash**, never an edit. And
`measurement/families/*.yaml` pins `manifest_hash`, so a manifest rebuild forces a family
re-registration. Trace what pins a hash before you change what is hashed.

---

## 2. Patterns to adopt

### 2.1 Protocol + registry + `get_x(name)`

The template is `workflow/edit_format.py`. Copy it verbatim:

```python
@runtime_checkable
class Thing(Protocol):
    name: str

    def instructions(self) -> str: ...  # what we ask for
    def parse(self, raw: str) -> Parsed: ...  # how we read the answer


THINGS: dict[str, Thing] = {A.name: A(), B.name: B()}


class UnknownThing(Exception):
    """Raised at construction. A topology naming something nobody implements
    must fail at load, not when the first answer arrives."""


def get_thing(name: str) -> Thing:
    thing = THINGS.get(name)
    if thing is None:
        raise UnknownThing(f"unknown thing {name!r}; registered: {sorted(THINGS)}")
    return thing
```

**The property that makes this the best abstraction in the codebase:** *the thing that asks and
the thing that reads the answer are one object, so they cannot disagree.* A prompt naming one
format while the parser expects another is a bug that presents as "the model is bad."

### 2.2 Composition over inheritance for capabilities

`ModelNode` has no subclasses; behaviour varies by injected capability. A `SubclassArchitectStep`
would rebuild exactly the duplication the layer removes.

### 2.3 Frozen data everywhere

Already universal via `domain.ids.Frozen`. Keep it. Wire-serializability (I3) is what lets any
component move out of process later — nearly free on day one, impossible to retrofit.

### 2.4 Structural Protocols where a layer boundary blocks an import

When a lower layer needs a shape a higher layer provides, **declare the Protocol where it is
consumed** rather than inventing a port. Precedent: `SandboxRunner` in `measurement/evaluator.py`
— *"Not a port (ADR-0005 rev. 2 ratifies eight port areas); a structural collaborator of the
TCB."* Python's structural typing means neither module imports the other.

### 2.5 Publish what you did not do

`RetrievedContext.missing` exists because *"the model was not shown the file" and "the model was
shown the file and failed" are different diagnoses, and the second is only believable when the
first is excluded.* Apply the same rule to manifest exclusions (published with a typed reason),
truncation, and skipped tasks. **Silent exclusion is the overfitting vector.**

### 2.6 Subprocess hygiene

`stdin=DEVNULL`, an **environment allowlist** (never `{**os.environ}`), and a deadline derived
from the lease. Not hygiene — an instrument property: a hung call runs to timeout, returns
`NONE`, and is excluded from the denominator, so an unanswered prompt shrinks N *non-randomly*.

---

## 3. Patterns to refuse

| Refuse | Why |
| :--- | :--- |
| **A DI container** | `spec.md` §3: *"explicit wiring; no DI container."* A container makes I6 (catalog frozen at composition) unverifiable and reintroduces runtime registration through the back door. A 200-line composition root that reads top-to-bottom is a feature |
| **A runtime plugin loader** | Directly contradicts I6, and hands the meta-loop arbitrary code while pretending it is data |
| **A pluggable `Verdict`** | I7 depends on exactly one judge |
| **Generalising the executor beyond acyclic + statically bounded** | ADR-0013's phasing is a safety property, not a limitation to route around |
| **Events that schedule work** | `spec.md` §8: *events never drive node scheduling.* A sensor that must cause work enqueues a task through the engine API |
| **Effects that outlive their lease** | Background execution makes `actuals` arrive after `release()` — the after-the-fact accounting `TASK-034` exists to make unrepresentable |
| **Relabelling tool output after operator approval** | Approval authorises the **effect**, never the **output**. Marking approved output `OPERATOR` converts arbitrary external content into instruction authority — the I11 attack |
| **A learned scorer that admits** | I9: *hard gates admit; proxies rank* |

---

## 4. Layout rules

| Kind of thing | Where it goes |
| :--- | :--- |
| Pure models, zero I/O | `domain/` |
| `Protocol` boundaries | `ports/` — and **a port arrives with its first adapter** (ADR-0005) |
| TCB: dispatch, policy, governor, bus | `kernel/` |
| TCB: evaluator, manifest, statistics | `measurement/` |
| Capabilities, roles, prompts, context | `agency/` (after ADR-0018) |
| Executor, validator, strategies, nodes | `workflow/` |
| Everything behind a non-TCB port | `adapters/` |
| Mocks | `tests/aether/mocks.py` — never in `src/` |
| Wiring | `composition.py` only. **No payload types**, or nodes transitively import the adapter stack |

**Effect payloads are JSON through the dispatcher.** `EffectRequest.descriptor` carries the
payload, `EffectOutcome.result_json` carries the result. Follow it for any new `effect_class`
rather than inventing a second channel.

---

## 5. Definition of done

```bash
uv run ruff format --check . && uv run ruff check .
uv run pyright src/aether/          # NOT --strict; strict lives in pyproject.toml
uv run lint-imports                 # must stay 9 kept, 0 broken
uv run pytest tests/aether tests/conformance tests/integration -q
uv run python scripts/check_links.py
uv run python scripts/docs_budget.py
```

Plus, per task:

- [ ] Every new gate has a **negative test** proving it can fail (§1.2).
- [ ] No contract, glob or path constant selects **zero** modules.
- [ ] `STATUS.md` updated with **pasted command output** — no claim without a command behind it.
- [ ] Anything TCB (`kernel/`, `measurement/evaluator.py`, `workflow/executor.py`,
      `workflow/validator.py`, schemas, CI) got human review and is not a meta-loop auto-commit.
- [ ] No capability number left the change without its full instrument tuple.

**This environment has no `python` on `PATH`** — only `python3`. Always `uv run`.
