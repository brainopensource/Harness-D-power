"""SFT export — one sample per step of an eligible run.

Reconstructs the exact assembled request context via `ContextAssembler.from_trajectory` (the
"exact-not-approximate" replay-reconstruction path, per `next_gen_architecture_specs.md` §6) so a
sample's `messages` is what the model actually saw, not an approximation of it.
"""

from __future__ import annotations

import importlib.metadata
from typing import Final

from sagiha.agency.context.assembler import ContextAssembler
from sagiha.agency.run_loop import DEFAULT_SYSTEM_PROMPT
from sagiha.domain.content import ToolSchema
from sagiha.domain.trajectory import RunRecord, TrajectoryStep
from sagiha.outer_loop.export.redaction import redact_sample
from sagiha.outer_loop.export.schema import SFTSample

def _harness_version() -> str:
    try:
        return importlib.metadata.version("sagiha")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


_HARNESS_VERSION: Final[str] = _harness_version()


async def export_sft_samples(
    *,
    record: RunRecord,
    steps: list[TrajectoryStep],
    tool_schemas: tuple[ToolSchema, ...],
    admitted: bool,
    redact_patterns: list[str],
    include_reasoning: bool = False,
) -> tuple[list[SFTSample], int]:
    """Returns `(samples, total_redaction_hits)`. One sample per step carrying an assistant
    `message` — text-only turns included, since `TrajectoryStep.message` now persists them
    (RC-4) and a distillation target that only ever saw tool-calling turns would teach an
    under-represented skill.
    """
    samples: list[SFTSample] = []
    total_hits = 0

    for i, step in enumerate(steps):
        if step.message is None:
            continue

        prior_steps = steps[:i]
        assembler = ContextAssembler.from_trajectory(
            system_prompt=DEFAULT_SYSTEM_PROMPT,
            tool_schemas=tool_schemas,
            task=record.task,
            steps=prior_steps,
        )
        assembled = await assembler.assemble(role="execution")

        context_messages = [m.model_dump(mode="json") for m in assembled.request.messages]
        target_message = step.message.model_dump(mode="json")
        if not include_reasoning:
            target_message["content"] = [b for b in target_message["content"] if b.get("kind") != "reasoning"]

        labels = {
            "admitted": admitted,
            "step_cost_usd": step.cost.usd,
            "prompt_version": "v2",
            "harness_version": _HARNESS_VERSION,
            "task_id": record.task.task_id,
            "step_seq": step.step_id.seq,
        }

        raw_sample = {
            "messages": [*context_messages, target_message],
            "tools": [s.model_dump(mode="json") for s in tool_schemas],
            "labels": labels,
        }
        redacted, hits = redact_sample(raw_sample, redact_patterns)
        total_hits += hits
        samples.append(SFTSample.model_validate(redacted))

    return samples, total_hits
