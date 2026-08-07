"""Manifest tooling and the bidirectional validity canary (TASK-014).

Every gate here ships with a test proving it can fail — the schema, the
version check, the cross-reference checks, both directions of the canary, and
the "no unscreened task" rule.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from aether.domain.gate import GateReport, GateStatus
from aether.measurement.manifest import (
    EMPTY_PATCH,
    CanaryVerdict,
    ExclusionReason,
    ManifestValidationError,
    TaskCandidate,
    ValidityInstrument,
    assign_splits,
    build_manifest,
    canonical_json,
    hash_command,
    load_manifest,
    manifest_hash,
    repos_in,
    screen_all,
    screen_candidate,
    tasks_in_split,
    validate_manifest,
)

DIGEST = "sha256:" + "c" * 64
COMMIT = "a" * 40
CREATED = datetime(2026, 8, 7, tzinfo=UTC)


def _candidate(instance_id: str = "org__repo-1", **overrides: object) -> TaskCandidate:
    base: dict[str, object] = {
        "instance_id": instance_id,
        "repo": "org/repo",
        "base_commit": COMMIT,
        "environment_image_digest": DIGEST,
        "test_command": "python3 -m pytest -q tests/test_x.py",
        "gold_patch": "diff --git a/x b/x\n",
        "problem_statement": f"{instance_id}: x() returns the wrong value for empty input.",
    }
    base.update(overrides)
    return TaskCandidate(**base)  # type: ignore[arg-type]


class ScriptedInstrument:
    """Returns a scripted `GateReport` per (instance_id, direction)."""

    def __init__(self, gold: GateReport, empty: GateReport) -> None:
        self._gold = gold
        self._empty = empty
        self.calls: list[tuple[str, str]] = []

    async def evaluate_patch(self, candidate: TaskCandidate, patch: str) -> GateReport:
        direction = "empty" if patch == EMPTY_PATCH else "gold"
        self.calls.append((candidate.instance_id, direction))
        return self._empty if direction == "empty" else self._gold


def _passed() -> GateReport:
    return GateReport(gate="tests", status=GateStatus.PASSED)


def _failed() -> GateReport:
    return GateReport(gate="tests", status=GateStatus.FAILED)


def _none(error: str = "exit 127") -> GateReport:
    return GateReport(gate="tests", status=GateStatus.NONE, instrument_error=error)


def _build(verdicts: list[CanaryVerdict], candidates: list[TaskCandidate]) -> dict[str, object]:
    return build_manifest(
        manifest_id="floor-smoke-01",
        suite="internal",
        candidates=candidates,
        verdicts=verdicts,
        instrument_contained=True,
        instrument_runtime="docker",
        instrument_image_digest=DIGEST,
        created_at=CREATED,
    )


# --------------------------------------------------------------- the canary


async def test_gold_passes_and_empty_fails_admits_the_task() -> None:
    instrument = ScriptedInstrument(_passed(), _failed())

    verdict = await screen_candidate(_candidate(), instrument)

    assert verdict.admitted is True
    assert verdict.reason is None
    assert instrument.calls == [("org__repo-1", "gold"), ("org__repo-1", "empty")]


async def test_a_failing_gold_patch_is_excluded_with_its_reason() -> None:
    verdict = await screen_candidate(_candidate(), ScriptedInstrument(_failed(), _failed()))

    assert verdict.admitted is False
    assert verdict.reason is ExclusionReason.GOLD_PATCH_FAILS


async def test_a_passing_empty_patch_is_excluded_with_its_reason() -> None:
    """The direction that is easy to forget: tests that pass with no change
    score a free resolve for every arm."""
    verdict = await screen_candidate(_candidate(), ScriptedInstrument(_passed(), _passed()))

    assert verdict.admitted is False
    assert verdict.reason is ExclusionReason.EMPTY_PATCH_PASSES


@pytest.mark.parametrize("direction", ["gold", "empty"])
async def test_an_instrument_error_is_never_blamed_on_the_task(direction: str) -> None:
    """B4 inside the canary: `NONE` is our instrument failing. Recording it as
    `gold_patch_fails` would blame the task for our bug."""
    gold = _none() if direction == "gold" else _passed()
    empty = _none() if direction == "empty" else _failed()

    verdict = await screen_candidate(_candidate(), ScriptedInstrument(gold, empty))

    assert verdict.admitted is False
    assert verdict.reason is ExclusionReason.INSTRUMENT_ERROR
    assert "exit 127" in verdict.detail


async def test_a_task_that_passes_then_fails_identically_is_flaky() -> None:
    class Flaky:
        def __init__(self) -> None:
            self.n = 0

        async def evaluate_patch(self, candidate: TaskCandidate, patch: str) -> GateReport:
            self.n += 1
            return _passed() if self.n == 1 else _failed()

    verdict = await screen_candidate(_candidate(), Flaky(), repeats=2)

    assert verdict.admitted is False
    assert verdict.reason is ExclusionReason.FLAKY_TESTS
    assert verdict.flaky is True


async def test_the_scripted_instrument_satisfies_the_protocol() -> None:
    assert isinstance(ScriptedInstrument(_passed(), _failed()), ValidityInstrument)


# ------------------------------------------------------- exclusions publish


async def test_exclusions_are_published_with_a_reason_and_never_silent() -> None:
    candidates = [_candidate("good-1"), _candidate("broken-1"), _candidate("free-1")]
    verdicts = [
        await screen_candidate(candidates[0], ScriptedInstrument(_passed(), _failed())),
        await screen_candidate(candidates[1], ScriptedInstrument(_failed(), _failed())),
        await screen_candidate(candidates[2], ScriptedInstrument(_passed(), _passed())),
    ]

    manifest = _build(verdicts, candidates)

    assert [t["instance_id"] for t in manifest["tasks"]] == ["good-1"]
    published = {e["instance_id"]: e["reason"] for e in manifest["validity_gate"]["exclusions"]}
    assert published == {
        "broken-1": "gold_patch_fails",
        "free-1": "empty_patch_passes",
    }
    assert all(e["detail"] for e in manifest["validity_gate"]["exclusions"])


async def test_an_unscreened_candidate_cannot_enter_a_manifest() -> None:
    """The no-`--force` rule for this gate: a task with no verdict is not
    representable, so "we forgot to screen it" cannot ship."""
    candidates = [_candidate("screened"), _candidate("never-screened")]
    verdicts = [await screen_candidate(candidates[0], ScriptedInstrument(_passed(), _failed()))]

    with pytest.raises(ManifestValidationError) as exc_info:
        _build(verdicts, candidates)

    assert exc_info.value.check == "validity_gate"
    assert "never-screened" in str(exc_info.value)


async def test_screen_all_screens_every_candidate() -> None:
    candidates = [_candidate("a"), _candidate("b")]
    verdicts = await screen_all(candidates, ScriptedInstrument(_passed(), _failed()))
    assert [v.instance_id for v in verdicts] == ["a", "b"]


# ------------------------------------------------------------ schema gates


def test_a_valid_manifest_validates() -> None:
    candidates = [_candidate("good-1")]
    verdicts = [CanaryVerdict(
        instance_id="good-1", admitted=True, gold_status=GateStatus.PASSED, empty_status=GateStatus.FAILED
    )]
    validate_manifest(_build(verdicts, candidates))  # must not raise


@pytest.mark.parametrize(
    ("mutate", "check"),
    [
        (lambda m: m.pop("tasks"), "schema"),
        (lambda m: m["tasks"][0].update({"split": "production"}), "schema"),
        (lambda m: m["tasks"][0].update({"base_commit": "not-a-sha"}), "schema"),
        (lambda m: m["tasks"][0].update({"environment_image_digest": "aether/eval:latest"}), "schema"),
        (lambda m: m["tasks"][0].update({"test_command_hash": "md5:abc"}), "schema"),
        (lambda m: m["tasks"][0].update({"surprise_key": 1}), "schema"),
        (lambda m: m["validity_gate"].update({"gold_pass_required": False}), "schema"),
        (lambda m: m["validity_gate"].update({"empty_fail_required": False}), "schema"),
        (
            lambda m: m["validity_gate"]["exclusions"].append({"instance_id": "x", "reason": "vibes"}),
            "schema",
        ),
        (lambda m: m.update({"schema_version": "2.0.0"}), "schema_version"),
    ],
)
def test_the_schema_gate_can_fail(mutate, check: str) -> None:  # noqa: ANN001
    manifest = _build(
        [CanaryVerdict(
            instance_id="good-1",
            admitted=True,
            gold_status=GateStatus.PASSED,
            empty_status=GateStatus.FAILED,
        )],
        [_candidate("good-1")],
    )
    mutate(manifest)

    with pytest.raises(ManifestValidationError) as exc_info:
        validate_manifest(manifest)

    assert exc_info.value.check == check


def test_duplicate_instances_are_refused() -> None:
    manifest = _build(
        [CanaryVerdict(
            instance_id="good-1",
            admitted=True,
            gold_status=GateStatus.PASSED,
            empty_status=GateStatus.FAILED,
        )],
        [_candidate("good-1")],
    )
    manifest["tasks"].append(dict(manifest["tasks"][0]))

    with pytest.raises(ManifestValidationError) as exc_info:
        validate_manifest(manifest)

    assert exc_info.value.check == "unique_instances"


def test_a_task_cannot_be_both_admitted_and_excluded() -> None:
    manifest = _build(
        [CanaryVerdict(
            instance_id="good-1",
            admitted=True,
            gold_status=GateStatus.PASSED,
            empty_status=GateStatus.FAILED,
        )],
        [_candidate("good-1")],
    )
    manifest["validity_gate"]["exclusions"].append(
        {"instance_id": "good-1", "reason": "flaky_tests", "detail": "x"}
    )

    with pytest.raises(ManifestValidationError) as exc_info:
        validate_manifest(manifest)

    assert exc_info.value.check == "exclusion_consistency"


# ---------------------------------------------------------------- identity


def _one_task_manifest() -> dict[str, object]:
    return _build(
        [CanaryVerdict(
            instance_id="good-1",
            admitted=True,
            gold_status=GateStatus.PASSED,
            empty_status=GateStatus.FAILED,
        )],
        [_candidate("good-1")],
    )


def test_identity_is_the_canonical_json_sha256_and_is_key_order_independent() -> None:
    manifest = _one_task_manifest()
    reordered = dict(reversed(list(manifest.items())))

    assert manifest_hash(manifest) == manifest_hash(reordered)
    assert canonical_json(manifest) == canonical_json(reordered)
    assert manifest_hash(manifest).startswith("sha256:")


def test_any_change_is_a_new_hash_never_an_edit() -> None:
    manifest = _one_task_manifest()
    before = manifest_hash(manifest)

    manifest["tasks"][0]["split"] = "holdout"

    assert manifest_hash(manifest) != before


def test_test_command_hash_matches_the_evaluators_own_convention() -> None:
    """The evaluator verifies the command it is about to run against this
    exact value; two different hash conventions would make every run a NONE."""
    from aether.measurement.evaluator import hash_command as evaluator_hash_command

    assert hash_command("python3 -m pytest") == evaluator_hash_command("python3 -m pytest")


def test_manifest_round_trips_through_yaml() -> None:
    from aether.measurement.manifest import dump_manifest

    manifest = _one_task_manifest()
    reloaded = load_manifest(dump_manifest(manifest))

    assert manifest_hash(reloaded) == manifest_hash(manifest)


# ------------------------------------------------------------------ splits


def test_splits_are_deterministic_for_a_seed() -> None:
    ids = [f"task-{i}" for i in range(20)]
    assert assign_splits(ids, seed=7) == assign_splits(list(reversed(ids)), seed=7)


def test_splits_partition_every_task_and_respect_the_ratios() -> None:
    ids = [f"task-{i}" for i in range(20)]
    assignment = assign_splits(ids, dev=0.6, holdout=0.25, seed=0)

    assert set(assignment) == set(ids)
    counts = {
        split: sum(1 for v in assignment.values() if v == split)
        for split in ("dev", "holdout", "sealed")
    }
    assert counts == {"dev": 12, "holdout": 5, "sealed": 3}


def test_split_selection_reads_the_pinned_manifest() -> None:
    candidates = [_candidate("dev-1", split="dev"), _candidate("sealed-1", split="sealed")]
    verdicts = [
        CanaryVerdict(
            instance_id=c.instance_id,
            admitted=True,
            gold_status=GateStatus.PASSED,
            empty_status=GateStatus.FAILED,
        )
        for c in candidates
    ]
    manifest = _build(verdicts, candidates)

    assert [t["instance_id"] for t in tasks_in_split(manifest, "dev")] == ["dev-1"]
    assert [t["instance_id"] for t in tasks_in_split(manifest, "sealed")] == ["sealed-1"]


def test_the_repo_set_is_derived_from_the_manifest() -> None:
    """B1's cache clones what the manifest names — never a hard-coded list."""
    candidates = [_candidate("a", repo="org/one"), _candidate("b", repo="org/two")]
    verdicts = [
        CanaryVerdict(
            instance_id=c.instance_id,
            admitted=True,
            gold_status=GateStatus.PASSED,
            empty_status=GateStatus.FAILED,
        )
        for c in candidates
    ]

    assert repos_in(_build(verdicts, candidates)) == ["org/one", "org/two"]


def test_a_task_with_no_problem_statement_cannot_enter_a_manifest() -> None:
    """Audit F1. `TaskCandidate` carried no issue text at all, so the manifest
    schema could not express the one thing the harness is asked to act on, and
    `runner.py` silently substituted the `instance_id`.

    The gate is at build time because that is the last cheap moment: a manifest
    is TCB data and pinning one is a hash, not an edit.
    """
    candidate = _candidate("org__repo-1", problem_statement="   ")
    verdict = CanaryVerdict(
        instance_id="org__repo-1",
        admitted=True,
        gold_status=GateStatus.PASSED,
        empty_status=GateStatus.FAILED,
    )

    with pytest.raises(ManifestValidationError) as exc_info:
        build_manifest(
            manifest_id="floor-smoke-01",
            suite="internal",
            candidates=[candidate],
            verdicts=[verdict],
            instrument_contained=True,
            created_at=CREATED,
        )

    assert exc_info.value.check == "problem_statement"


def test_an_excluded_task_needs_no_problem_statement() -> None:
    """The gate applies to what is *admitted*. A task excluded because its image
    would not build is published with its reason and never posed to a model, so
    demanding issue text for it would block a legitimate manifest."""
    candidate = _candidate("org__repo-1", problem_statement="")
    verdict = CanaryVerdict(
        instance_id="org__repo-1",
        admitted=False,
        gold_status=GateStatus.NONE,
        empty_status=GateStatus.NONE,
        reason=ExclusionReason.IMAGE_UNBUILDABLE,
    )

    manifest = build_manifest(
        manifest_id="floor-smoke-01",
        suite="internal",
        candidates=[candidate, _candidate("org__repo-2")],
        verdicts=[
            verdict,
            CanaryVerdict(
                instance_id="org__repo-2",
                admitted=True,
                gold_status=GateStatus.PASSED,
                empty_status=GateStatus.FAILED,
            ),
        ],
        instrument_contained=True,
        created_at=CREATED,
    )

    assert [t["instance_id"] for t in manifest["tasks"]] == ["org__repo-2"]
    assert manifest["tasks"][0]["problem_statement"]


def test_the_problem_statement_is_part_of_the_manifests_identity() -> None:
    """Two manifests posing different questions are different instruments, so
    they must not share a hash (measurement.md §6)."""
    verdicts = [
        CanaryVerdict(
            instance_id="org__repo-1",
            admitted=True,
            gold_status=GateStatus.PASSED,
            empty_status=GateStatus.FAILED,
        )
    ]

    def _build(statement: str) -> str:
        return manifest_hash(
            build_manifest(
                manifest_id="floor-smoke-01",
                suite="internal",
                candidates=[_candidate("org__repo-1", problem_statement=statement)],
                verdicts=verdicts,
                instrument_contained=True,
                created_at=CREATED,
            )
        )

    assert _build("the parser drops the final token") != _build("the parser drops the first token")
