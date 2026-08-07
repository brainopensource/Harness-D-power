"""Pinned task manifests and the bidirectional validity canary (TASK-014).

A manifest is **TCB data**: immutable once pinned, identified by the sha256 of
its canonical JSON form, and a change is a new manifest with a new hash, never
an edit (measurement.md §6). Split assignment (`dev`/`holdout`/`sealed`) is
pinned here, with the tasks it partitions, so it cannot drift per run.

**The entry rule is bidirectional and per task**: a task enters a manifest only
if the *gold patch passes* and the *empty patch fails* on our own instrument.
One direction alone is worthless — gold-passes without empty-fails admits tasks
whose tests pass with no change at all, which score as free resolves; and
~30% of public Pro tasks were estimated broken in a mid-2026 audit, so the
exclusion list is expected to be non-empty. **Every exclusion is published with
a typed reason**: silent exclusion is the overfitting vector measurement.md
§4.3 names.

There is no `--force`. `build_manifest` accepts *verdicts*, not tasks, so a
task that was never screened is not representable in a manifest this module
can produce.

Residency: this module is TCB and lives in `measurement/` (never `adapters/`);
`aether-tcb-isolation` proves it cannot import `aether.adapters`,
`aether.workflow` or `aether.agency`. The instrument that actually materializes
a worktree and runs the tests therefore arrives as a structural
`ValidityInstrument` — the concrete one is `measurement/validity.py`, which is
*not* TCB and may touch adapters.
"""

from __future__ import annotations

import hashlib
import json
import random
from collections.abc import Sequence
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal, Protocol, cast, runtime_checkable

import jsonschema
import yaml

from aether.domain.gate import GateReport, GateStatus
from aether.domain.ids import Frozen

_SCHEMA_PATH = Path(__file__).parent / "schemas" / "manifest_schema.yaml"
SUPPORTED_MAJOR = 1

Split = Literal["dev", "holdout", "sealed"]
Suite = Literal["swe_bench_verified", "swe_bench_pro", "terminal_bench", "internal"]

#: The empty patch. Named rather than inlined because it is half the canary:
#: the tests must FAIL with this applied, or the task admits a free resolve.
EMPTY_PATCH = ""


class ExclusionReason(StrEnum):
    GOLD_PATCH_FAILS = "gold_patch_fails"
    EMPTY_PATCH_PASSES = "empty_patch_passes"
    IMAGE_UNBUILDABLE = "image_unbuildable"
    FLAKY_TESTS = "flaky_tests"
    UPSTREAM_RETRACTED = "upstream_retracted"
    #: Extends the schemas_and_contracts.md §2 draft — see the schema file's
    #: own note. A GateStatus.NONE during screening is our instrument failing,
    #: not the task being broken, and B4 exists to keep those apart.
    INSTRUMENT_ERROR = "instrument_error"


class ManifestValidationError(Exception):
    def __init__(self, check: str, message: str) -> None:
        self.check = check
        super().__init__(f"{check}: {message}")


class TaskCandidate(Frozen):
    """A task *proposed* for a manifest. It is not a manifest entry until the
    canary has judged it — that is the whole point of the type split."""

    instance_id: str
    repo: str
    base_commit: str
    environment_image_digest: str
    test_command: str  # hashed into `test_command_hash` at pin time
    gold_patch: str
    split: Split = "dev"
    fail_to_pass: tuple[str, ...] = ()
    pass_to_pass: tuple[str, ...] = ()
    perturbed_of: str | None = None


class CanaryVerdict(Frozen):
    """The published record of one screening, admitted or not."""

    instance_id: str
    admitted: bool
    gold_status: GateStatus
    empty_status: GateStatus
    reason: ExclusionReason | None = None
    detail: str = ""
    flaky: bool = False


@runtime_checkable
class ValidityInstrument(Protocol):
    """Materializes `candidate` at its base commit with `patch` applied and
    runs its pinned test command. `patch == EMPTY_PATCH` means "apply nothing"."""

    async def evaluate_patch(self, candidate: TaskCandidate, patch: str) -> GateReport: ...


def _load_schema() -> dict[str, Any]:
    with open(_SCHEMA_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


_SCHEMA = _load_schema()


def hash_command(command: str) -> str:
    """Same convention as `measurement/evaluator.py` — the evaluator verifies
    the command it is about to run against exactly this value."""
    return "sha256:" + hashlib.sha256(command.encode()).hexdigest()


def canonical_json(manifest: dict[str, Any]) -> str:
    """Sorted keys, no insignificant whitespace. The YAML file is for humans;
    this is the machine identity (schemas_and_contracts.md common rules)."""
    return json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def manifest_hash(manifest: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(manifest).encode()).hexdigest()


def load_manifest(yaml_text: str) -> dict[str, Any]:
    parsed: Any = yaml.safe_load(yaml_text)
    if not isinstance(parsed, dict):
        raise ManifestValidationError("schema", "manifest must be a mapping")
    return dict(cast("dict[str, Any]", parsed))


def validate_manifest(manifest: dict[str, Any]) -> None:
    """Schema pass plus the cross-references jsonschema cannot express. Raises
    `ManifestValidationError` naming the failed check; there is no bypass."""
    # Version first, deliberately. The schema's own `^1\.` pattern would
    # reject a v2 manifest as a generic shape error, which reads as "malformed
    # file" when the truth is "this validator does not speak that version".
    # Checking here first is also what keeps this branch reachable — a gate no
    # input can reach is not a gate.
    declared = manifest.get("schema_version")
    if isinstance(declared, str) and declared[:1].isdigit():
        major = int(declared.split(".", 1)[0])
        if major != SUPPORTED_MAJOR:
            raise ManifestValidationError(
                "schema_version",
                f"unsupported major {major}; schema evolution is an explicit migration, "
                "never silent tolerance",
            )

    try:
        jsonschema.validate(manifest, _SCHEMA)
    except jsonschema.ValidationError as exc:
        raise ManifestValidationError("schema", exc.message) from exc

    seen: set[str] = set()
    for task in manifest["tasks"]:
        if task["instance_id"] in seen:
            raise ManifestValidationError(
                "unique_instances", f"duplicate instance_id {task['instance_id']!r}"
            )
        seen.add(task["instance_id"])

    for exclusion in manifest["validity_gate"]["exclusions"]:
        if exclusion["instance_id"] in seen:
            raise ManifestValidationError(
                "exclusion_consistency",
                f"{exclusion['instance_id']!r} is both admitted and excluded",
            )


async def screen_candidate(
    candidate: TaskCandidate, instrument: ValidityInstrument, *, repeats: int = 1
) -> CanaryVerdict:
    """Run the bidirectional canary for one task.

    `repeats > 1` re-runs the gold patch to surface within-task flakiness. A
    task that passes once and fails once under an identical instrument is
    `flaky_tests` — excluded with its reason published, never silently kept
    (which would put a coin flip in the resolve-rate denominator).
    """
    gold = await instrument.evaluate_patch(candidate, candidate.gold_patch)
    if gold.status is GateStatus.NONE:
        return CanaryVerdict(
            instance_id=candidate.instance_id,
            admitted=False,
            gold_status=gold.status,
            empty_status=GateStatus.NONE,
            reason=ExclusionReason.INSTRUMENT_ERROR,
            detail=f"gold patch: {gold.instrument_error or 'unmeasured'}",
        )
    if gold.status is not GateStatus.PASSED:
        return CanaryVerdict(
            instance_id=candidate.instance_id,
            admitted=False,
            gold_status=gold.status,
            empty_status=GateStatus.NONE,
            reason=ExclusionReason.GOLD_PATCH_FAILS,
            detail="gold patch does not pass on our instrument",
        )

    for _ in range(max(repeats - 1, 0)):
        again = await instrument.evaluate_patch(candidate, candidate.gold_patch)
        if again.status is not GateStatus.PASSED:
            return CanaryVerdict(
                instance_id=candidate.instance_id,
                admitted=False,
                gold_status=again.status,
                empty_status=GateStatus.NONE,
                reason=ExclusionReason.FLAKY_TESTS,
                detail=f"gold patch passed then reported {again.status.value} under an identical run",
                flaky=True,
            )

    empty = await instrument.evaluate_patch(candidate, EMPTY_PATCH)
    if empty.status is GateStatus.NONE:
        return CanaryVerdict(
            instance_id=candidate.instance_id,
            admitted=False,
            gold_status=gold.status,
            empty_status=empty.status,
            reason=ExclusionReason.INSTRUMENT_ERROR,
            detail=f"empty patch: {empty.instrument_error or 'unmeasured'}",
        )
    if empty.status is not GateStatus.FAILED:
        return CanaryVerdict(
            instance_id=candidate.instance_id,
            admitted=False,
            gold_status=gold.status,
            empty_status=empty.status,
            reason=ExclusionReason.EMPTY_PATCH_PASSES,
            detail="tests pass with no patch applied — this task scores a free resolve",
        )

    return CanaryVerdict(
        instance_id=candidate.instance_id,
        admitted=True,
        gold_status=gold.status,
        empty_status=empty.status,
    )


async def screen_all(
    candidates: Sequence[TaskCandidate], instrument: ValidityInstrument, *, repeats: int = 1
) -> list[CanaryVerdict]:
    return [await screen_candidate(c, instrument, repeats=repeats) for c in candidates]


def assign_splits(
    instance_ids: Sequence[str],
    *,
    dev: float = 0.6,
    holdout: float = 0.25,
    seed: int = 0,
) -> dict[str, Split]:
    """Deterministic split assignment, pinned into the manifest at build time.

    Sorted input plus a seeded RNG: the same ids and seed always produce the
    same partition, so a rebuild is auditable rather than merely plausible.
    Whatever is left after `dev`/`holdout` is `sealed`.
    """
    ordered = sorted(set(instance_ids))
    rng = random.Random(seed)
    shuffled = list(ordered)
    rng.shuffle(shuffled)

    n = len(shuffled)
    n_dev = int(n * dev)
    n_holdout = int(n * holdout)
    assignment: dict[str, Split] = {}
    for index, instance_id in enumerate(shuffled):
        if index < n_dev:
            assignment[instance_id] = "dev"
        elif index < n_dev + n_holdout:
            assignment[instance_id] = "holdout"
        else:
            assignment[instance_id] = "sealed"
    return assignment


def build_manifest(
    *,
    manifest_id: str,
    suite: Suite,
    candidates: Sequence[TaskCandidate],
    verdicts: Sequence[CanaryVerdict],
    instrument_contained: bool,
    instrument_runtime: str | None = None,
    instrument_image_digest: str | None = None,
    repeats: int = 1,
    created_at: datetime | None = None,
    parent_manifest: str | None = None,
) -> dict[str, Any]:
    """Assemble a validated manifest from screened candidates.

    Takes `verdicts`, not tasks: a candidate with no verdict is refused, so
    "we forgot to screen that one" is not expressible. Excluded candidates
    appear in `validity_gate.exclusions` with their typed reason — they are
    published, not dropped.
    """
    by_id = {c.instance_id: c for c in candidates}
    verdict_ids = {v.instance_id for v in verdicts}
    unscreened = sorted(set(by_id) - verdict_ids)
    if unscreened:
        raise ManifestValidationError(
            "validity_gate",
            f"{len(unscreened)} candidate(s) have no canary verdict: {unscreened}. "
            "A task enters a manifest only through the bidirectional canary; there is no bypass.",
        )
    unknown = sorted(verdict_ids - set(by_id))
    if unknown:
        raise ManifestValidationError("validity_gate", f"verdicts for unknown candidates: {unknown}")

    tasks: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    for verdict in verdicts:
        candidate = by_id[verdict.instance_id]
        if not verdict.admitted:
            exclusions.append(
                {
                    "instance_id": verdict.instance_id,
                    "reason": str(verdict.reason or ExclusionReason.INSTRUMENT_ERROR),
                    "detail": verdict.detail,
                }
            )
            continue
        entry: dict[str, Any] = {
            "instance_id": candidate.instance_id,
            "repo": candidate.repo,
            "base_commit": candidate.base_commit,
            "environment_image_digest": candidate.environment_image_digest,
            "test_command_hash": hash_command(candidate.test_command),
            "split": candidate.split,
        }
        if candidate.fail_to_pass:
            entry["fail_to_pass"] = list(candidate.fail_to_pass)
        if candidate.pass_to_pass:
            entry["pass_to_pass"] = list(candidate.pass_to_pass)
        if candidate.perturbed_of is not None:
            entry["perturbed_of"] = candidate.perturbed_of
        if verdict.flaky:
            entry["flaky"] = True
        tasks.append(entry)

    instrument: dict[str, Any] = {"contained": instrument_contained, "repeats": repeats}
    if instrument_runtime is not None:
        instrument["runtime"] = instrument_runtime
    if instrument_image_digest is not None:
        instrument["image_digest"] = instrument_image_digest

    manifest: dict[str, Any] = {
        "schema_version": "1.0.0",
        "manifest_id": manifest_id,
        "suite": suite,
        "created_at": (created_at or datetime.now(UTC)).isoformat().replace("+00:00", "Z"),
        "validity_gate": {
            "gold_pass_required": True,
            "empty_fail_required": True,
            "instrument": instrument,
            "exclusions": exclusions,
        },
        "tasks": tasks,
    }
    if parent_manifest is not None:
        manifest["parent_manifest"] = parent_manifest

    validate_manifest(manifest)
    return manifest


def tasks_in_split(manifest: dict[str, Any], split: Split) -> list[dict[str, Any]]:
    return [task for task in manifest["tasks"] if task["split"] == split]


def repos_in(manifest: dict[str, Any]) -> list[str]:
    """The distinct upstream repositories B1's cache must materialize. Derived
    from the manifest, never hard-coded (TASK-010's own rule)."""
    return sorted({task["repo"] for task in manifest["tasks"]})


def dump_manifest(manifest: dict[str, Any]) -> str:
    """YAML for humans. Identity stays the canonical-JSON hash."""
    return yaml.safe_dump(manifest, sort_keys=True, allow_unicode=True)


__all__ = [
    "EMPTY_PATCH",
    "CanaryVerdict",
    "ExclusionReason",
    "ManifestValidationError",
    "TaskCandidate",
    "ValidityInstrument",
    "assign_splits",
    "build_manifest",
    "canonical_json",
    "dump_manifest",
    "hash_command",
    "load_manifest",
    "manifest_hash",
    "repos_in",
    "screen_all",
    "screen_candidate",
    "tasks_in_split",
    "validate_manifest",
]
