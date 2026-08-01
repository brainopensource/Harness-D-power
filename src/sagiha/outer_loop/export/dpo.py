"""DPO export — preference pairs from Best-of-N siblings on identical prefixes.

Siblings share a `parent_task_id` (set by `KernelCandidateExecutor` — see `composition.py`) and,
at step 0, an identical assembled context: same `TaskSpec`, no prior steps, same seed. Step 0's
`prefix_digest` is therefore the machine-checkable form of "identical prefixes"
(`trace-distillation.md`) — grouping on `(parent_task_id, step_0.prefix_digest)` finds exactly
the sibling sets Best-of-N produced, and step 0's *outputs* are the preference signal: what did
each candidate choose to do first, given the identical prompt every sibling received.
"""

from __future__ import annotations

from collections import defaultdict

from sagiha.agency.context.assembler import ContextAssembler
from sagiha.agency.run_loop import DEFAULT_SYSTEM_PROMPT
from sagiha.domain.content import ToolSchema
from sagiha.domain.trajectory import RunRecord, TrajectoryStep
from sagiha.outer_loop.export.eligibility import RunEligibility
from sagiha.outer_loop.export.redaction import redact_sample
from sagiha.outer_loop.export.schema import DPOSample


def _group_key(record: RunRecord, steps: list[TrajectoryStep]) -> tuple[str, str] | None:
    if record.task.parent_task_id is None or not steps:
        return None
    return (record.task.parent_task_id, steps[0].prefix_digest)


async def export_dpo_pairs(
    *,
    records: list[RunRecord],
    steps_by_run: dict[str, list[TrajectoryStep]],
    eligibility_by_run: dict[str, RunEligibility],
    tool_schemas: tuple[ToolSchema, ...],
    redact_patterns: list[str],
) -> tuple[list[DPOSample], int]:
    """Returns `(pairs, total_redaction_hits)`.

    Hygiene: both sides of a pair must individually be untainted, replay-verified, and
    within-budget — only `admitted` is allowed to differ, since that is the preference signal.
    A candidate with `admitted is None` (never evaluated) is excluded from pairing entirely —
    ambiguous provenance is not a safe "rejected" example.
    """
    groups: dict[tuple[str, str], list[RunRecord]] = defaultdict(list)
    for record in records:
        steps = steps_by_run.get(record.run_id, [])
        key = _group_key(record, steps)
        if key is None:
            continue
        elig = eligibility_by_run.get(record.run_id)
        if (
            elig is None
            or elig.tainted is not False
            or elig.replay_verified is not True
            or elig.within_budget is not True
        ):
            continue
        groups[key].append(record)

    pairs: list[DPOSample] = []
    total_hits = 0

    for (parent_task_id, _digest), group_records in groups.items():
        chosen_records = [r for r in group_records if eligibility_by_run[r.run_id].admitted is True]
        rejected_records = [r for r in group_records if eligibility_by_run[r.run_id].admitted is False]
        if not chosen_records or not rejected_records:
            continue

        chosen_record = chosen_records[0]
        chosen_steps = steps_by_run[chosen_record.run_id]
        assembler = ContextAssembler.from_trajectory(
            system_prompt=DEFAULT_SYSTEM_PROMPT,
            tool_schemas=tool_schemas,
            task=chosen_record.task,
            steps=[],
        )
        assembled = await assembler.assemble(role="execution")
        prompt_messages = [m.model_dump(mode="json") for m in assembled.request.messages]
        chosen_message = chosen_steps[0].message.model_dump(mode="json") if chosen_steps[0].message else {}

        for rejected_record in rejected_records:
            rejected_steps = steps_by_run[rejected_record.run_id]
            rejected_message = (
                rejected_steps[0].message.model_dump(mode="json") if rejected_steps[0].message else {}
            )

            raw_sample = {
                "prompt": prompt_messages,
                "chosen": chosen_message,
                "rejected": rejected_message,
                "labels": {
                    "parent_task_id": parent_task_id,
                    "chosen_run_id": chosen_record.run_id,
                    "rejected_run_id": rejected_record.run_id,
                },
            }
            redacted, hits = redact_sample(raw_sample, redact_patterns)
            total_hits += hits
            pairs.append(DPOSample.model_validate(redacted))

    return pairs, total_hits
