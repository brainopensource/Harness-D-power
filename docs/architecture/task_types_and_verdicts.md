---
status: rationale
updated: 2026-08-07
---

# Task Types and Verdicts — The Generic Work Model

**Design of record for M5 (H2 — Framework).** Ratified by
[ADR-0019](../decisions/0019-three-horizons-harness-framework-metaloop.md) and
[ADR-0020](../decisions/0020-verdict-capability-and-judge-integrity.md).

This document answers one question: **what is a unit of work, and how do we know it succeeded**
— for a code fix, a question about the codebase, an explanation, a research task, or something
nobody has thought of yet.

---

## 1. What is wrong today

`domain/task.py`:

```python
class Task(Frozen):
    task_id: TaskId
    repo: str  # ← SWE-bench
    base_commit: str  # ← SWE-bench
    instructions: str
    environment_image_digest: str  # ← SWE-bench
    test_command_hash: str  # ← SWE-bench
    source: TaskSource
```

Four of six fields are SWE-bench, all mandatory, none defaulted. **A task for *"explain how
dispatch works"* cannot be constructed without fabricating a repo, a commit, an image digest and
a test-command hash.** And even if you fabricated them, `check_evaluator_termination` would
refuse the topology, because `retrieve → answer` never reaches a `kind: evaluate` node.

The unit of work is not a unit of work. It is a benchmark row.

---

## 2. The generic model

```python
class TaskType(StrEnum):
    CODE_FIX = "code_fix"  # produce a patch that makes hidden tests pass
    QA = "qa"  # answer a question about a corpus
    EXPLAIN = "explain"  # produce a faithful explanation of code or behaviour
    RESEARCH = "research"  # gather and synthesise from external sources
    GENERIC = "generic"  # anything with a declared verdict


class Task(Frozen):
    task_id: TaskId
    task_type: TaskType
    instructions: str
    payload: TaskPayload  # discriminated on task_type
    verdict_spec: VerdictSpec  # WHICH judge — TCB data, pinned by hash
    source: TaskSource
```

**`verdict_spec` is the important field.** The task carries *which judge applies*, pinned by
hash, and the judge's own specification lives in TCB data the candidate cannot reach
(ADR-0020 §2). A task does not carry its answer; it carries the identity of the thing that
knows.

### 2.1 Payloads — discriminated, and `code_fix` is unchanged

```python
class CodeFixPayload(Frozen):
    kind: Literal["code_fix"] = "code_fix"
    repo: str
    base_commit: str
    environment_image_digest: str
    test_command_hash: str
    test_paths: tuple[str, ...] = ()  # TASK-049's I7 globs


class QAPayload(Frozen):
    kind: Literal["qa"] = "qa"
    corpus: CorpusRef  # what may be retrieved from
    question: str
    answer_schema: str | None = None  # JSON Schema, when the answer is structured


class ExplainPayload(Frozen):
    kind: Literal["explain"] = "explain"
    corpus: CorpusRef
    subject: str  # "the dispatch choke point"
    audience: Literal["new_contributor", "reviewer", "operator"]


class ResearchPayload(Frozen):
    kind: Literal["research"] = "research"
    question: str
    allowed_sources: tuple[str, ...]  # egress is declared, never ambient


class GenericPayload(Frozen):
    kind: Literal["generic"] = "generic"
    inputs_json: str  # wire-serializable (I3)


TaskPayload = CodeFixPayload | QAPayload | ExplainPayload | ResearchPayload | GenericPayload
```

**`CodeFixPayload` carries today's four fields unchanged.** The SWE-bench path is byte-identical
through this change — if the existing 384 tests do not stay green, the generalisation was done
wrong (ADR-0019's stated neutrality).

`ResearchPayload.allowed_sources` deserves its line: **egress is declared per task, never
ambient.** A research task that may reach the network says so in the artifact that is hashed
into the instrument tuple.

---

## 3. The catalogue

| Task type | Payload | Verdict | Admits alone? | Topology shape | "Done" means |
| :--- | :--- | :--- | :---: | :--- | :--- |
| `code_fix` | `CodeFixPayload` | `TestSuiteVerdict` | ✅ | `retrieve → plan → edit → apply → judge →(fail,k)→ repair` | Hidden tests pass |
| `qa` (closed) | `QAPayload` + ground truth | `AssertionVerdict` | ✅ | `retrieve → answer → judge` | Answer matches within declared tolerance |
| `qa` (open) | `QAPayload`, no ground truth | `RubricVerdict` **+ human/deterministic admitter** | ❌ | `retrieve → answer → judge` | Rubric score clears, **and** an admitting verdict agrees |
| `explain` | `ExplainPayload` | `RubricVerdict` + `AssertionVerdict` on citations | ❌ alone | `retrieve → outline → explain → judge` | Faithful, complete for the audience, **every claim cites a real span** |
| `research` | `ResearchPayload` | `RubricVerdict` + `AssertionVerdict` on sources | ❌ alone | `plan → search → read → synthesise → judge` | Sources are in `allowed_sources` and resolve |
| `generic` | `GenericPayload` | Whatever `verdict_spec` names | per verdict | Declared by the topology | Declared by the verdict |

**Read the "admits alone" column as the safety spine.** Three of six rows are `❌`, and for those
an LLM judge *ranks* while a deterministic check or a human *admits* (I9 rev. 2). That is not
bureaucracy — it is the reason a self-improving loop over these task types cannot drift into
grading itself.

### 3.1 The cheapest deterministic admitter: citations

For `explain` and `research`, most of the verification is mechanical and does not need a model:

- every citation resolves to a real file and line range (`AssertionVerdict`)
- every cited span actually contains the claimed symbol
- the answer's JSON validates against `answer_schema`
- sources are drawn only from `allowed_sources`

Only *faithfulness* and *completeness* need a rubric. **Split the verdict rather than reaching
for the LLM judge first** — the deterministic half is what admits, and it is nearly free.

---

## 4. What changes in the executor and validator

**`check_evaluator_termination` → `check_verdict_termination`.** From *"every path reaches a node
of `kind: evaluate`"* to **"every path reaches a node whose output socket is a `GateReport`"**.
The structural guarantee is identical — no topology routes around the judge — and
`retrieve → answer → judge` becomes legal. TCB change; needs a malformed fixture proving it can
still fail (a topology whose terminal node emits something else must be refused).

**Node kinds gained:**

| Kind | In → Out | Purpose |
| :--- | :--- | :--- |
| `answer` | `RetrievedContext → Answer` | `ModelNode` with an answer role and a structured parser |
| `judge` | `Answer \| AppliedPatch → EvaluatedCandidate` | Dispatches to the `Verdict` named by `verdict_spec` |
| `search` | `RetrievedContext → RetrievedContext` | External retrieval; requires declared egress |
| `synthesise` | `RetrievedContext → Answer` | `ModelNode`, multi-source |

`evaluate` stays exactly as it is — it becomes *the `code_fix` specialisation of `judge`*, not a
thing that gets rewritten.

---

## 5. Measurement, per type

**ADR-0002 applies per task type.** A `qa` resolve rate needs a `qa` A/A floor with its own
discordance rates. Variance on an LLM-judged type is not variance on a test-suite-judged one, and
derived N does not transfer between them. A new task type ships with **no number** until its own
floor exists.

**`RubricVerdict` additionally needs a judge-agreement floor** before the type reports anything
(ADR-0020 §5): the same items scored twice by the pinned judge, plus agreement against
`HumanVerdict` on a sample. Report both — a judge that disagrees with itself is an instrument
being characterised, not a judge being trusted.

| Metric | `code_fix` | `qa`/`explain`/`research` |
| :--- | :--- | :--- |
| Primary outcome | pass@1 | pass@1 under the admitting verdict |
| Instrument error | `NONE` rate | `NONE` rate **+ judge-disagreement rate** |
| Floor | A/A on the pinned manifest | A/A **per type** |
| Cost | usd per resolved task | usd per resolved task, **including judge tokens** |

That last cell matters: an LLM judge is an inference cost on every item, and an arm that looks
cheap because its judging is unpriced is the `pricing.py` defect in a new place.

---

## 6. Migration — three steps, none of which breaks `code_fix`

1. **Add `task_type` + `payload`** with `CODE_FIX` as the default and `CodeFixPayload` built
   from today's fields. Manifest schema gains `task_type` (defaulting to `code_fix`) — additive,
   so `schema_version` goes to `1.2.0` and existing manifests keep validating.
2. **Introduce the `Verdict` registry**, with `TestSuiteVerdict` wrapping today's
   `RealEvaluator` verbatim. Rename the validator check. `evaluate` keeps working.
3. **Add one non-code type end to end** — `qa` with `AssertionVerdict`, because it is fully
   deterministic and needs no judge-agreement floor. **That is the proof H2 works**, and it is
   deliberately the type that needs no LLM judge.

`RubricVerdict`, `explain` and `research` follow only after `qa` runs green and the
judge-agreement floor exists.

---

## 7. What this does not do

- **It does not open the judge.** The `Verdict` registry is closed; adding a kind is an ADR
  (ADR-0020 §1).
- **It does not weaken I7.** The judge specification is TCB data pinned by hash for every kind,
  and `judge_unmodified` generalises `tests_unmodified` rather than replacing it.
- **It does not authorise a number.** Every new type is subject to ADR-0002, its own floor, and
  a declared family before any arm runs.
- **It does not make the harness multi-purpose today.** This is M5. Sprints 4 and 5 — the floor
  and the capability layer — come first, because a framework whose judge is uncalibrated is
  worse than a harness.
