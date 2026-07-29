---
status: normative
updated: 2026-07-29
---

# **Task Model & Acceptance Criteria**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Why This Module Exists**

A bare string leaves **"done" undefined**, which cascades: the Evaluator has no target to evaluate against, the Plan Mode gate has nothing concrete to approve, and long-horizon work cannot resume after interruption. This is the deepest missing primitive for autonomy, since a system that cannot state what success means cannot recognize it.

## **The Task Model**

```python
class AcceptanceCriterion(BaseModel):
    description: str
    check: str  # machine-checkable command or predicate
    required: bool = True


class TaskSpec(BaseModel):
    task_id: str
    revision: int = 0
    goal: str
    acceptance: tuple[AcceptanceCriterion, ...]
    profile: str = "coding"  # execution profile — see below
    parent_task_id: str | None = None
    status: TaskStatus = "submitted"
```

Full definition in [Domain Schemas](./domain-schemas.md).

## **Acceptance Criteria Must Be Machine-Checkable**

`check` holds a command or predicate that returns pass/fail without human interpretation:

| Good | Bad |
| :---- | :---- |
| `pytest tests/test_auth.py::test_expiry` | "authentication works correctly" |
| `mypy src/ --strict` exits 0 | "types are clean" |
| `curl -sf localhost:8000/health` | "the service starts" |
| No new entries in `# type: ignore` census | "code quality is maintained" |

Criteria that cannot be expressed as a check belong in `goal` as context, never in `acceptance`. This distinction is what keeps the Evaluator honest: it evaluates only what can be verified, and everything else is explicitly acknowledged as unverified.

## **Profiles and Unverified Completion**

`profile` selects the [execution profile](../02-architecture/execution-profiles.md) — which ports the
run mounts and what admits its result. It does **not** relax this file's rules: wherever acceptance
criteria exist, they must still be machine-checkable, under every profile.

What a profile can change is whether criteria exist at all. Some work has no verifiable success
condition — a question, an explanation, a conversation — and forcing a synthetic `check` onto it
produces a criterion that is satisfied by anything, which is worse than none.

> **A task with no acceptance criteria and no gates terminates on the model's own completion signal.
> Nothing independently verifies it.**

That is a genuine epistemic downgrade from everything else this architecture insists on, and it is
stated here rather than buried in a profile table. Three consequences follow:

* `coding` remains the default. Un-verified completion is opt-in, never the fallback.
* The profile is recorded in `run.started` and persisted with the trajectory, so no later analysis,
  benchmark report, or outer-loop training set can mistake an ungated run for a gated one.
* Such runs are **excluded from benchmark suites and from outer-loop evidence** by construction —
  there is no measurement to contribute.

## **Acceptance Is Authored Before Execution**

The Design step of DMARTIC produces the `TaskSpec` including its acceptance criteria, and — for gated risk classes — that spec is what the human approves. Writing criteria first has three effects: it forces the ambiguity out of the request before tokens are spent, it gives the reviewer something concrete to react to, and it prevents the criteria from being quietly retrofitted to whatever the agent happened to produce.

## **Decomposition**

Sub-tasks carry `parent_task_id`, forming a task tree. Two rules govern decomposition:

* A parent's acceptance is not satisfied merely because every child's is. The parent's own criteria are checked independently, since integration failures live precisely in the gaps between correct parts.
* Sub-tasks dispatched in parallel must have **disjoint file-set closures**, computed via `CodeGraph.impacted_by()`. Overlapping sub-tasks are serialized. Partitioning at dispatch time is far cheaper and more reliable than resolving conflicts at merge time.

## **Durability and Resumption**

`TaskSpec` is persisted, not held in memory. A run that is interrupted, gated on human approval, or resumed hours later reloads the spec and its trajectory. This is what makes asynchronous approval gates workable: the task waits durably rather than occupying a live process, and the human replies whenever they get to it.

## **Status Transitions**

```
submitted → working → { input-required | auth-required } → working → { completed | failed | canceled }
```

`input-required` and `auth-required` are **first-class resting states**, not errors. A task parked on an approval request is healthy, and the system reports it as such rather than as a stall.
