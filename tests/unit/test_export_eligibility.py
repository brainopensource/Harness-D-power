"""Exporter eligibility + schema hygiene (v2-S4 Epic S4.4 closeout).

Pins the four-criteria gate from `trace-distillation.md`: admitted ∧ ¬tainted ∧
within-budget ∧ replay-verified. Absence of a verdict is never a pass.
"""

from __future__ import annotations

import pytest

from sagiha.domain.content import Message, TextBlock, ToolResult
from sagiha.domain.events import GateEvaluated, ReplayVerified
from sagiha.domain.identity import StepId
from sagiha.domain.trajectory import RunRecord, TrajectoryStep
from sagiha.domain.work import CriterionResult, GateReport, TaskSpec
from sagiha.outer_loop.export.eligibility import assess
from sagiha.outer_loop.export.license import is_export_permitted
from sagiha.outer_loop.export.schema import DPOSample, SFTSample


def _task(*, task_id: str = "t1", parent: str | None = None) -> TaskSpec:
    return TaskSpec(task_id=task_id, goal="fix", acceptance=(), parent_task_id=parent)


def _record(run_id: str, *, status: str = "completed") -> RunRecord:
    return RunRecord(run_id=run_id, task=_task(), status=status)  # type: ignore[arg-type]


def _gate(admitted: bool) -> GateReport:
    return GateReport(
        criteria=(CriterionResult(description="a", check="a", passed=admitted, required=True),),
        no_new_suppressions=admitted,
        tests_unmodified=admitted,
        diff_within_bounds=admitted,
    )


def _step(*, trusted: bool = True, run_id: str = "r1") -> TrajectoryStep:
    return TrajectoryStep(
        step_id=StepId(run_id=run_id, branch_id="main", seq=1),
        message=Message(role="assistant", content=[TextBlock(text="ok")]),
        tool_results=(ToolResult(call_id="c1", content=[TextBlock(text="out")], trusted=trusted),),
        prefix_digest="digest-a",
    )


def _eligible_events(run_id: str = "r1", *, admitted: bool = True) -> list:
    return [
        GateEvaluated(run_id=run_id, gate_report=_gate(admitted)),
        ReplayVerified(run_id=run_id, replay_run_id="replay-1"),
    ]


def test_assess_all_four_criteria_true_is_eligible() -> None:
    elig = assess(_record("r1"), [_step()], _eligible_events())
    assert elig.eligible is True
    assert elig.reasons() == ()


def test_assess_none_admitted_is_not_a_pass() -> None:
    """No GateEvaluated → admitted=None → ineligible (GateReport doctrine)."""
    elig = assess(
        _record("r1"),
        [_step()],
        [ReplayVerified(run_id="r1", replay_run_id="replay-1")],
    )
    assert elig.admitted is None
    assert elig.eligible is False
    assert "admitted=None" in elig.reasons()


def test_assess_missing_replay_verified_is_not_a_pass() -> None:
    elig = assess(
        _record("r1"),
        [_step()],
        [GateEvaluated(run_id="r1", gate_report=_gate(True))],
    )
    assert elig.replay_verified is None
    assert elig.eligible is False
    assert "replay_verified=None" in elig.reasons()


def test_taint_canary_excludes_run() -> None:
    """Untrusted tool output (default / canary) must exclude the run from export."""
    elig = assess(_record("r1"), [_step(trusted=False)], _eligible_events())
    assert elig.tainted is True
    assert elig.eligible is False
    assert "tainted=True" in elig.reasons()


def test_budget_parked_run_not_within_budget() -> None:
    elig = assess(_record("r1", status="input-required"), [_step()], _eligible_events())
    assert elig.within_budget is False
    assert elig.eligible is False
    assert "within_budget=False" in elig.reasons()


def test_rejected_gate_not_eligible_but_usable_as_dpo_rejected_signal() -> None:
    elig = assess(_record("r1"), [_step()], _eligible_events(admitted=False))
    assert elig.admitted is False
    assert elig.tainted is False
    assert elig.within_budget is True
    assert elig.replay_verified is True
    assert elig.eligible is False  # SFT requires admitted
    assert elig.reasons() == ("admitted=False",)


def test_sft_sample_schema_roundtrip() -> None:
    sample = SFTSample(
        messages=[{"role": "assistant", "content": [{"kind": "text", "text": "hi"}]}],
        tools=[],
        labels={"admitted": True, "task_id": "t1"},
    )
    assert SFTSample.model_validate(sample.model_dump()).labels["admitted"] is True


def test_dpo_sample_schema_roundtrip() -> None:
    sample = DPOSample(
        prompt=[{"role": "user", "content": [{"kind": "text", "text": "fix"}]}],
        chosen={"role": "assistant", "content": [{"kind": "text", "text": "ok"}]},
        rejected={"role": "assistant", "content": [{"kind": "text", "text": "no"}]},
        labels={"parent_task_id": "parent"},
    )
    assert DPOSample.model_validate(sample.model_dump()).labels["parent_task_id"] == "parent"


@pytest.mark.parametrize(
    ("spdx", "ok"),
    [
        ("MIT", True),
        ("Apache-2.0", True),
        (None, False),
        ("GPL-3.0", False),
        ("", False),
    ],
)
def test_license_gate_fail_closed(spdx: str | None, ok: bool) -> None:
    assert is_export_permitted(spdx) is ok


@pytest.mark.asyncio
async def test_dpo_export_excludes_tainted_sibling() -> None:
    """Taint canary: a tainted rejected sibling must not form a DPO pair."""
    from sagiha.outer_loop.export.dpo import export_dpo_pairs
    from sagiha.outer_loop.export.eligibility import RunEligibility

    parent = "parent-1"
    chosen = RunRecord(run_id="c", task=_task(task_id="c", parent=parent), status="completed")
    rejected = RunRecord(run_id="r", task=_task(task_id="r", parent=parent), status="completed")
    steps = {
        "c": [_step(run_id="c", trusted=True)],
        "r": [_step(run_id="r", trusted=False)],
    }
    eligibility = {
        "c": RunEligibility(
            run_id="c", admitted=True, tainted=False, within_budget=True, replay_verified=True
        ),
        "r": RunEligibility(
            run_id="r", admitted=False, tainted=True, within_budget=True, replay_verified=True
        ),
    }
    pairs, _hits = await export_dpo_pairs(
        records=[chosen, rejected],
        steps_by_run=steps,
        eligibility_by_run=eligibility,
        tool_schemas=(),
        redact_patterns=[],
    )
    assert pairs == []
