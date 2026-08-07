"""Comparative-lift rig (TASK-015) — the `HarnessUnderTest` seam.

`spec.md` §9 forbids citing a competitor's published numbers as evidence, and
`measurement.md` §6 says the competitive claim is therefore unsubstantiable
until a rig exists that runs every arm through **our** evaluator, on the same
model and the same manifest. That rig is this module.

**Sprint 3 ships the seam plus the bare-model arm only.** The OpenHands arm is
explicitly out of scope (sprint-03.md), and so is AETHER's own comparative
run — the floor comes first (ADR-0002). What lands here is the shape all arms
must fit, and one arm that fits it.

The baseline is part of the instrument (`measurement.md` §4.1): a weak
baseline manufactures lift. So `BareModelHarness` is pre-registered — one
completion, the official SWE-bench inference template with its **hash
recorded**, no execution feedback, no retrieval beyond the task statement,
temperature and seed pinned, and the identical model fingerprint the harness
arm uses. Every one of those is a way the number could be inflated, which is
why each is a field rather than a habit.

Measurement is a tool, not a port (ADR-0005) — hence `measurement/`, not
`ports/`. This module is *not* in `aether-tcb-isolation`: it composes real
adapters, which is exactly what the TCB may not do.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any, Protocol, cast, runtime_checkable

from aether.domain.gate import GateStatus
from aether.domain.ids import SpanId, TaskId
from aether.domain.model_io import (
    ModelMessage,
    ModelRequest,
    ModelStreamEvent,
    TextDelta,
    UsageEvent,
)
from aether.domain.taint import Provenance, TaintSpan
from aether.domain.task import Task, TaskSource
from aether.measurement.evaluator import RealEvaluator, hash_command
from aether.measurement.manifest import TaskCandidate
from aether.measurement.outcomes import ArmRun, TaskOutcome
from aether.measurement.validity import WorktreeValidityInstrument
from aether.ports.model_provider import ModelProvider

#: The official SWE-bench inference template. Held here as a literal and
#: hashed, because "we used the standard prompt" is not checkable and
#: `template_hash` is (measurement.md §4.1).
SWEBENCH_INFERENCE_TEMPLATE = """\
You will be provided with a partial code base and an issue statement \
explaining a problem to resolve.

<issue>
{problem_statement}
</issue>

Please generate a *SEARCH/REPLACE*-free unified diff patch that resolves the \
issue. Respond with the patch only, in `diff --git` format.
"""


def template_hash(template: str = SWEBENCH_INFERENCE_TEMPLATE) -> str:
    return "sha256:" + hashlib.sha256(template.encode()).hexdigest()


@runtime_checkable
class HarnessUnderTest(Protocol):
    """One arm of a comparative run.

    Every arm sees the same `TaskCandidate` and is judged by the same
    `Evaluator`. An arm that scores itself is not an arm, it is a press
    release — which is why `attempt` returns a *patch*, and the rig, not the
    arm, runs the gate.
    """

    @property
    def harness_id(self) -> str: ...

    @property
    def config_hash(self) -> str: ...

    async def attempt(self, candidate: TaskCandidate) -> str:
        """Produce a candidate patch for the task. No evaluation, no gate."""
        ...


class BareModelHarness:
    """The pre-registered baseline arm: one completion, no feedback, no tools.

    Deliberately the weakest *defensible* arm rather than the weakest possible
    one. It gets the same model, the same fingerprint and the official
    template — anything less would inflate every lift number computed against
    it, permanently and invisibly.
    """

    harness_id = "bare_model"

    def __init__(
        self,
        provider: ModelProvider,
        model_fingerprint: str,
        *,
        temperature: float = 0.0,
        seed: int = 0,
        max_tokens: int = 4096,
        template: str = SWEBENCH_INFERENCE_TEMPLATE,
    ) -> None:
        self._provider = provider
        self._model_fingerprint = model_fingerprint
        self._temperature = temperature
        self._seed = seed
        self._max_tokens = max_tokens
        self._template = template
        self.last_usage: tuple[int, int] = (0, 0)

    @property
    def config_hash(self) -> str:
        """Identity of this arm's configuration — every knob that could move
        the number, in a stable order."""
        payload = (
            f"{self.harness_id}|{self._model_fingerprint}|t={self._temperature}|seed={self._seed}"
            f"|max_tokens={self._max_tokens}|template={template_hash(self._template)}"
        )
        return "sha256:" + hashlib.sha256(payload.encode()).hexdigest()

    @property
    def template_hash(self) -> str:
        return template_hash(self._template)

    async def attempt(self, candidate: TaskCandidate) -> str:
        span = TaintSpan(
            span_id=SpanId(f"bare-model-{candidate.instance_id}"),
            label=Provenance.OPERATOR,
            text=self._template.format(problem_statement=candidate.instance_id),
            source=f"manifest:{candidate.instance_id}",
            created_at=datetime.now(UTC),
        )
        request = ModelRequest(
            model=self._model_fingerprint.split(":")[-2]
            if self._model_fingerprint.count(":") >= 2
            else self._model_fingerprint,
            messages=(ModelMessage(role="user", spans=(span,)),),
            max_tokens=self._max_tokens,
            temperature=self._temperature,
            seed=self._seed,  # pinned: an unpinned baseline is a different arm each run
        )
        parts: list[str] = []
        prompt_tokens = 0
        completion_tokens = 0
        # `ModelProvider.stream` is declared `async def ... -> AsyncIterator[...]`,
        # while every adapter implements it as an async *generator* (calling it
        # returns the iterator directly, not a coroutine). Both are legal
        # spellings of the same wire behaviour and the conformance suite
        # exercises the adapters, but they type differently — the cast records
        # which one is real rather than papering over it silently.
        stream = cast("AsyncIterator[ModelStreamEvent]", self._provider.stream(request))
        async for event in stream:
            if isinstance(event, TextDelta):
                parts.append(event.text)
            elif isinstance(event, UsageEvent):
                prompt_tokens, completion_tokens = event.prompt_tokens, event.completion_tokens
            elif event.kind == "stop":
                break
        self.last_usage = (prompt_tokens, completion_tokens)
        return "".join(parts)


class PairedRunner:
    """Runs arms over a manifest through one shared evaluator.

    Same model, same manifest, same judge is the only apples-to-apples
    comparison available in this space (`measurement.md` §6). The runner owns
    the evaluator so no arm can be scored by an instrument it chose.
    """

    def __init__(
        self,
        instrument: WorktreeValidityInstrument,
        evaluator: RealEvaluator,
        manifest_hash: str,
        split: str,
        model_fingerprint: str,
    ) -> None:
        self._instrument = instrument
        self._evaluator = evaluator
        self._manifest_hash = manifest_hash
        self._split = split
        self._model_fingerprint = model_fingerprint

    async def run_arm(
        self,
        arm_id: str,
        harness: HarnessUnderTest,
        candidates: list[TaskCandidate],
        *,
        seed: int = 0,
        topology_hash: str | None = None,
        container_digest: str | None = None,
    ) -> ArmRun:
        """One arm's pass over the manifest, in manifest order.

        Order is not shuffled per arm: the design is paired, and re-ordering
        one arm would introduce exactly the between-arm difference the A/A
        floor exists to measure.
        """
        results: list[TaskOutcome] = []
        for candidate in candidates:
            started = time.monotonic()
            try:
                patch = await harness.attempt(candidate)
                report = await self._instrument.evaluate_patch(candidate, patch)
            except Exception as exc:  # noqa: BLE001 — an arm that crashes is an
                # instrument error for that task, not a failed task. Recording
                # it as FAILED would put our own crash in the denominator.
                results.append(
                    TaskOutcome(
                        task_id=candidate.instance_id,
                        status=GateStatus.NONE,
                        wall_clock_ms=int((time.monotonic() - started) * 1000),
                        detail=f"arm raised: {type(exc).__name__}: {exc}",
                    )
                )
                continue

            prompt_tokens, completion_tokens = getattr(harness, "last_usage", (0, 0))
            results.append(
                TaskOutcome(
                    task_id=candidate.instance_id,
                    status=report.status,
                    wall_clock_ms=int((time.monotonic() - started) * 1000),
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    detail=report.instrument_error or "",
                )
            )

        return ArmRun(
            run_id=f"{arm_id}-{int(time.time())}",
            arm_id=arm_id,
            harness_id=harness.harness_id,
            manifest_hash=self._manifest_hash,
            split=self._split,
            model_fingerprint=self._model_fingerprint,
            seed=seed,
            results=tuple(results),
            topology_hash=topology_hash,
            container_digest=container_digest,
            contained=self._evaluator.is_contained,
        )


def candidate_to_task(candidate: TaskCandidate, manifest_hash: str) -> Task:
    """Materialize a manifest entry as the domain `Task` the engine consumes.

    The `TaskSource` back-reference is not bookkeeping: it is how a trajectory
    proves which pinned manifest it came from, months later.
    """
    return Task(
        task_id=TaskId(candidate.instance_id),
        repo=candidate.repo,
        base_commit=candidate.base_commit,
        instructions=candidate.instance_id,
        environment_image_digest=candidate.environment_image_digest,
        test_command_hash=hash_command(candidate.test_command),
        source=TaskSource(manifest_hash=manifest_hash, instance_id=candidate.instance_id),
    )


def instrument_tuple(run: ArmRun, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """The tuple `measurement.md` §6 requires beside every number.

    A result that cannot state these is not a result. Building it here means a
    report cannot accidentally omit half of it.
    """
    tuple_: dict[str, Any] = {
        "manifest_hash": run.manifest_hash,
        "split": run.split,
        "model_fingerprint": run.model_fingerprint,
        "topology_hash": run.topology_hash,
        "container_digest": run.container_digest,
        "contained": run.contained,
        "seed": run.seed,
        "arm_id": run.arm_id,
        "harness_id": run.harness_id,
    }
    if extra:
        tuple_.update(extra)
    return tuple_


__all__ = [
    "SWEBENCH_INFERENCE_TEMPLATE",
    "BareModelHarness",
    "HarnessUnderTest",
    "PairedRunner",
    "candidate_to_task",
    "instrument_tuple",
    "template_hash",
]
