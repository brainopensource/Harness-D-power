"""Comparative-lift rig (TASK-015) — the seam and the bare-model arm.

What must hold for a comparative number to mean anything: every arm is judged
by *our* evaluator (never its own), the baseline's pre-registration is
recorded rather than described, and a crashing arm produces an instrument
error rather than a failed task.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from aether.domain.gate import GateReport, GateStatus
from aether.domain.model_io import ModelRequest, ModelStreamEvent, StopEvent, TextDelta, UsageEvent
from aether.measurement.manifest import TaskCandidate
from aether.measurement.runner import (
    SWEBENCH_INFERENCE_TEMPLATE,
    BareModelHarness,
    HarnessUnderTest,
    PairedRunner,
    candidate_to_task,
    instrument_tuple,
    template_hash,
)

DIGEST = "sha256:" + "d" * 64


def _candidate(instance_id: str) -> TaskCandidate:
    return TaskCandidate(
        instance_id=instance_id,
        repo="org/repo",
        base_commit="a" * 40,
        environment_image_digest=DIGEST,
        test_command="python3 -m pytest -q",
        gold_patch="diff --git a/x b/x\n",
        split="dev",
    )


class _StubProvider:
    def __init__(self, text: str = "diff --git a/x b/x\n") -> None:
        self.requests: list[ModelRequest] = []
        self._text = text

    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelStreamEvent]:
        self.requests.append(request)
        yield TextDelta(text=self._text)
        yield UsageEvent(prompt_tokens=11, completion_tokens=7)
        yield StopEvent(reason="end")

    async def count_tokens(self, request: ModelRequest) -> int:
        return 1


class _StubInstrument:
    """Stands in for `WorktreeValidityInstrument` — the rig's contract with it
    is one method, and the real one is exercised in the integration suite."""

    def __init__(self, status: GateStatus = GateStatus.PASSED) -> None:
        self.patches: list[str] = []
        self._status = status

    async def evaluate_patch(self, candidate: TaskCandidate, patch: str) -> GateReport:
        self.patches.append(patch)
        return GateReport(
            gate="tests",
            status=self._status,
            instrument_error="boom" if self._status is GateStatus.NONE else None,
        )


class _StubEvaluator:
    is_contained = True


def _runner(instrument: _StubInstrument) -> PairedRunner:
    return PairedRunner(
        instrument,  # type: ignore[arg-type]
        _StubEvaluator(),  # type: ignore[arg-type]
        manifest_hash="sha256:" + "1" * 64,
        split="dev",
        model_fingerprint="openai_compatible:test-model:ep-a1",
    )


# ------------------------------------------------------------- the baseline


async def test_the_bare_model_arm_produces_a_patch_and_never_scores_itself() -> None:
    provider = _StubProvider()
    harness = BareModelHarness(provider, "openai_compatible:test-model:ep-a1")

    patch = await harness.attempt(_candidate("t1"))

    assert patch.startswith("diff --git")
    assert not hasattr(harness, "evaluate")  # arms produce patches; the rig judges


async def test_the_baselines_pre_registration_is_recorded_not_described() -> None:
    """`measurement.md` §4.1: a weak baseline manufactures lift, so every knob
    that could weaken it is a recorded field."""
    provider = _StubProvider()
    harness = BareModelHarness(provider, "openai_compatible:test-model:ep-a1", temperature=0.0, seed=7)

    await harness.attempt(_candidate("t1"))
    request = provider.requests[0]

    assert request.temperature == 0.0
    assert request.seed == 7
    assert harness.template_hash == template_hash(SWEBENCH_INFERENCE_TEMPLATE)
    assert harness.config_hash.startswith("sha256:")


async def test_the_bare_model_arm_makes_exactly_one_completion_with_no_tools() -> None:
    """One completion, no execution feedback, no tools — that is what "bare
    model" has to mean, or the comparison is against something else."""
    provider = _StubProvider()
    harness = BareModelHarness(provider, "openai_compatible:test-model:ep-a1")

    await harness.attempt(_candidate("t1"))

    assert len(provider.requests) == 1
    assert provider.requests[0].tools == ()


def test_changing_any_pre_registered_knob_changes_the_config_hash() -> None:
    provider = _StubProvider()
    base = BareModelHarness(provider, "fp", temperature=0.0, seed=0).config_hash

    assert BareModelHarness(provider, "fp", temperature=0.7, seed=0).config_hash != base
    assert BareModelHarness(provider, "fp", temperature=0.0, seed=1).config_hash != base
    assert BareModelHarness(provider, "fp", template="different").config_hash != base
    assert BareModelHarness(provider, "other-fp").config_hash != base


def test_the_bare_model_harness_satisfies_the_seam() -> None:
    assert isinstance(BareModelHarness(_StubProvider(), "fp"), HarnessUnderTest)


# ------------------------------------------------------------- the rig


async def test_every_arm_is_judged_by_the_rigs_evaluator() -> None:
    instrument = _StubInstrument(GateStatus.PASSED)
    harness = BareModelHarness(_StubProvider(), "fp")
    candidates = [_candidate("t1"), _candidate("t2")]

    run = await _runner(instrument).run_arm("baseline", harness, candidates)

    assert len(instrument.patches) == 2
    assert [r.task_id for r in run.results] == ["t1", "t2"]  # manifest order, unshuffled
    assert all(r.status is GateStatus.PASSED for r in run.results)


async def test_an_arm_that_raises_is_an_instrument_error_not_a_failed_task() -> None:
    """Our crash must not enter the resolve-rate denominator as the task's
    failure — that is B4 applied to the rig itself."""

    class _Exploding:
        harness_id = "exploding"
        config_hash = "sha256:" + "0" * 64

        async def attempt(self, candidate: TaskCandidate) -> str:
            raise RuntimeError("provider timeout")

    run = await _runner(_StubInstrument()).run_arm("boom", _Exploding(), [_candidate("t1")])

    assert run.results[0].status is GateStatus.NONE
    assert "provider timeout" in run.results[0].detail


async def test_token_usage_and_wall_clock_are_recorded_per_task() -> None:
    """Cost per resolved task is a mandatory report column (ADR-0003 rev. 2
    §4); it cannot be reconstructed after the run."""
    harness = BareModelHarness(_StubProvider(), "fp")

    run = await _runner(_StubInstrument()).run_arm("baseline", harness, [_candidate("t1")])

    assert run.results[0].prompt_tokens == 11
    assert run.results[0].completion_tokens == 7
    assert run.results[0].wall_clock_ms >= 0


async def test_the_run_carries_its_instrument_tuple() -> None:
    """A number without its instrument tuple is not a result (`measurement.md`
    §6, Sprint 3 DoD item 10)."""
    harness = BareModelHarness(_StubProvider(), "fp")

    run = await _runner(_StubInstrument()).run_arm(
        "baseline", harness, [_candidate("t1")], seed=7, container_digest=DIGEST
    )
    tuple_ = instrument_tuple(run)

    assert tuple_["manifest_hash"].startswith("sha256:")
    assert tuple_["split"] == "dev"
    assert tuple_["model_fingerprint"] == "openai_compatible:test-model:ep-a1"
    assert tuple_["container_digest"] == DIGEST
    assert tuple_["contained"] is True
    assert tuple_["seed"] == 7


def test_a_manifest_entry_materializes_as_a_task_that_names_its_manifest() -> None:
    task = candidate_to_task(_candidate("t1"), "sha256:" + "9" * 64)

    assert task.source.manifest_hash == "sha256:" + "9" * 64
    assert task.source.instance_id == "t1"
    assert task.environment_image_digest == DIGEST


@pytest.mark.parametrize("status", [GateStatus.PASSED, GateStatus.FAILED, GateStatus.NONE])
async def test_every_tri_state_verdict_survives_into_the_arm_run(status: GateStatus) -> None:
    run = await _runner(_StubInstrument(status)).run_arm(
        "baseline", BareModelHarness(_StubProvider(), "fp"), [_candidate("t1")]
    )

    assert run.results[0].status is status
