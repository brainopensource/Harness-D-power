"""Task and its manifest provenance.

No literal skeleton exists for these two types anywhere in the docs — only the
scaffolding comment `task.py # Task, TaskSource` in
docs/development/core_skeletons_and_protocols.md §0. Fields are inferred from
the pinned task-manifest schema (docs/development/schemas_and_contracts.md
§2: instance_id, repo, base_commit, environment_image_digest,
test_command_hash) and from EvalSpec/HarnessUnderTest.attempt(), both of
which reference a bare `task_id: TaskId`.
"""

from __future__ import annotations

from aether.domain.ids import Frozen, TaskId


class TaskSource(Frozen):
    """Back-reference to the pinned manifest entry a Task was materialized from."""

    manifest_hash: str
    instance_id: str


class Task(Frozen):
    task_id: TaskId
    repo: str
    base_commit: str
    instructions: str
    environment_image_digest: str
    test_command_hash: str
    test_paths: tuple[str, ...] = ()  # repo-relative globs a candidate must not touch (I7)
    source: TaskSource
