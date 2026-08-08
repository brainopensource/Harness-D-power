---
status: normative
updated: 2026-08-07
---
# ADR-0020: The Verdict Capability, and Judge Integrity for Non-Test Judges

**Status**: Accepted · **Date**: 2026-08-07 · **Fork**: raised by [ADR-0019](./0019-three-horizons-harness-framework-metaloop.md)

## Context

[ADR-0019](./0019-three-horizons-harness-framework-metaloop.md) commits to many task types. A
`qa` task has no test suite; an `explain` task has no exit code. Something must decide whether
they succeeded, and the two obvious answers are both wrong:

- **Keep only the test-suite judge.** Then non-code task types cannot be measured, and
  `check_evaluator_termination` keeps them structurally unexpressible. H2 is dead.
- **Make the judge a plugin point.** Then a third party — or eventually the meta-loop — supplies
  the thing that decides whether its own work was good. That is the failure
  [`vision.md`](../vision.md) §2 names, delivered as a feature.

I7 as currently written assumes the judge is a test suite: *"the agent that writes code cannot
modify the tests grading it,"* enforced by a `tests_unmodified` gate. I9 (*hard gates admit;
proxies rank*) is currently enforced by nothing — `grep -rn "def rank\|def admit" src/aether/`
returns empty, because no ranker exists yet.

**Hermes ships an LLM `FitnessScore` judge — `0.5·correctness + 0.3·procedure + 0.2·conciseness
− length_penalty` — with no constraint preventing it from promoting a variant on its own
score.** That is the concrete mistake this ADR exists to not repeat.

## Decision

### 1. `Verdict` is a capability with a **closed** registry

```python
class Verdict(Protocol):
    """TCB-resident. Decides PASSED / FAILED / NONE for one task type."""

    verdict_kind: str
    admits: bool  # may this verdict alone admit a result?

    async def judge(self, spec: VerdictSpec, candidate: Candidate) -> GateReport: ...
```

Four implementations, and **adding a fifth is an ADR, never a config change or a plugin**:

| Kind | Decides by | `admits` | Used by |
| :--- | :--- | :---: | :--- |
| `TestSuiteVerdict` | Pinned test command exit code (today's `RealEvaluator`) | ✅ | `code_fix` |
| `AssertionVerdict` | Deterministic predicates over structured output (schema match, exact/regex/set membership, numeric tolerance) | ✅ | `qa` with ground truth, `generic` |
| `RubricVerdict` | An LLM judge against a pinned rubric | ❌ **never** | `explain`, `research`, open `qa` |
| `HumanVerdict` | An operator decision, recorded with identity and timestamp | ✅ | Anything, and the escape hatch for a new type before its automation exists |

The registry lives in `measurement/` — TCB residency (`spec.md` §4), so `tcb-isolation` selects
every implementation.

### 2. I7 generalised — **restated, not relaxed**

> **I7 (rev. 2).** The artifact that judges is never reachable from the artifact being judged.

Concretely, for every verdict kind, the **judge specification is TCB data pinned by hash** and
the agent can neither read nor write it:

| Verdict | The pinned artifact |
| :--- | :--- |
| `TestSuiteVerdict` | Test files + `test_command_hash` (today's `tests_unmodified`) |
| `AssertionVerdict` | The assertion set and its tolerances |
| `RubricVerdict` | The rubric text, **the judge model fingerprint, and the judge prompt** |
| `HumanVerdict` | The question put to the operator |

`tests_unmodified` becomes one instance of a general **`judge_unmodified`** gate: before scoring,
the verdict hashes its own specification and refuses to score on mismatch, returning
`GateStatus.NONE` with `instrument_error` — never `FAILED`. A tampered judge is *unmeasured*,
not *failed*, for the reason `measurement.md` §2 gives: an instrument failure is never a data
point, and mapping it to `FAILED` would make tampering costly, which is a measurement error
dressed as a deterrent.

**The rubric is not context.** A `RubricVerdict`'s rubric text must never enter any prompt the
candidate sees. It is retrieved by the judge, from TCB data, at scoring time.

### 3. I9 becomes load-bearing — **a rubric verdict may never admit alone**

> **I9 (rev. 2).** Hard gates admit; proxies rank. **A verdict whose `admits` is `False` may
> order candidates and may never promote one.** Admission requires a verdict with `admits: True`
> — deterministic or human.

Enforced at the type level, not by discipline: `Verdict.admits` is read by the admission path,
and a family declaring only non-admitting verdicts is refused by the statistics gatekeeper the
same way an undeclared family is.

**This is the property that makes H3 survivable.** A self-improving system whose judge is an
LLM it also influences has no fixed point. Requiring a deterministic or human admitter means the
meta-loop can *propose* freely and can never *ratify* itself.

### 4. `check_evaluator_termination` → `check_verdict_termination`

The validator rule generalises from *"every path reaches a node of `kind: evaluate`"* to
**"every path reaches a node whose output socket is a `GateReport`"**. The structural guarantee
is unchanged — no topology routes around the judge — while `retrieve → answer → judge` becomes
expressible. The `on_instrument_error` exemption to a terminal flag node is unchanged.

### 5. Every task type gets its own floor

ADR-0002 applies per task type. A `qa` resolve rate needs a `qa` A/A floor with its own
discordance rates: variance on an LLM-judged type is not the variance measured on a
test-suite-judged one, and derived N does not transfer between them.

**Additionally, for `RubricVerdict` only:** a **judge-agreement floor** is required before the
type may report anything — the same items scored twice by the pinned judge, reporting
self-agreement, plus agreement against `HumanVerdict` on a sample. A judge that disagrees with
itself is an instrument, and it is being characterised, not trusted.

## Consequences

**Positive.** Non-code task types become measurable and expressible. The judge stays outside the
agent's reach under every verdict kind. The `admits` flag makes I9 mechanical for the first
time. `TASK-049`'s `tests_unmodified` work generalises rather than being superseded.

**Negative, and accepted.** Four verdict kinds is more surface than one. `RubricVerdict` needs
a judge-agreement floor before it is usable, which is real work before any `explain` number
exists. `check_verdict_termination` is a TCB edit requiring human review and a malformed
fixture proving it can still fail.

**Neutral.** `code_fix` is unaffected: `TestSuiteVerdict` is today's `RealEvaluator` with a
`verdict_kind` and an `admits` flag attached.

## Reversal conditions

- **If `RubricVerdict`'s judge-agreement floor is wide** — the judge disagreeing with itself or
  with humans beyond a declared margin — the kind is withdrawn and the task types depending on
  it revert to `HumanVerdict` until a better judge exists. A judge that cannot agree with itself
  does not become acceptable by being convenient.
- **If any verdict kind is ever made pluggable from data**, this ADR is being violated. The
  registry is closed by design; opening it hands the meta-loop its own judge.
- **If `admits: False` is ever bypassed** — a rubric-only family admitting a variant — every
  number that family produced is discarded, not corrected.
- **If the generalisation costs a single existing test**, revert: `code_fix` must be
  byte-identical through this change.

## References

- [ADR-0019](./0019-three-horizons-harness-framework-metaloop.md) — why many task types exist
- [ADR-0002](./0002-no-number-before-the-floor.md) · [ADR-0003](./0003-statistical-admission-protocol.md) · [ADR-0006](./0006-tcb-boundary-and-meta-loop-authority.md)
- [`spec.md` §2](../spec.md#2-invariants) — I7 and I9, which this ADR restates
- [`architecture/task_types_and_verdicts.md`](../architecture/task_types_and_verdicts.md) — the catalogue
