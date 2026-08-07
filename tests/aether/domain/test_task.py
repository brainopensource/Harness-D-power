"""Task/TaskSource — see docstring in aether/domain/task.py for the design rationale."""

from __future__ import annotations

from aether.domain.ids import TaskId
from aether.domain.task import Task, TaskSource


def test_task_round_trips_manifest_provenance() -> None:
    task = Task(
        task_id=TaskId("django__django-11099"),
        repo="django/django",
        base_commit="a" * 40,
        instructions="Fix the reported regex validator bug.",
        environment_image_digest="sha256:" + "b" * 64,
        test_command_hash="sha256:" + "c" * 64,
        source=TaskSource(manifest_hash="sha256:" + "d" * 64, instance_id="django__django-11099"),
    )
    assert task.source.instance_id == "django__django-11099"
    assert task.task_id == "django__django-11099"
