"""Retrieval (Sprint 3.5, B3) — the fix for the harness's largest capability gap.

Sprint 3's `RetrieveStep` read one file, defaulting to `README.md`. Three local
models then scored 0/8 on trivial tasks, and the diagnosis was not the models:
they were being asked to patch code they had never been shown, so they invented
a file and diffed against fiction.
"""

from __future__ import annotations

from typing import Any

from aether.domain.ids import RunId, TaskId
from aether.domain.task import Task, TaskSource
from aether.domain.workspace import FileSlice, WorktreeRef
from aether.workflow.nodes.retrieve import RetrievedContext, RetrieveStep, TaskInput
from aether.workflow.step import StepContext

TASK = Task(
    task_id=TaskId("t1"),
    repo="org/repo",
    base_commit="a" * 40,
    instructions="Fix f().",
    environment_image_digest="sha256:" + "a" * 64,
    test_command_hash="sha256:" + "b" * 64,
    source=TaskSource(manifest_hash="sha256:" + "c" * 64, instance_id="i1"),
)
WORKTREE = WorktreeRef(worktree_id="wt-1", run_id=RunId("run-1"), base_commit="a" * 40, abs_hint="/tmp")
CTX = StepContext(run_id=RunId("run-1"), node_id="retrieve", lease="l1")  # type: ignore[arg-type]


class _Facade:
    def __init__(self, files: dict[str, str]) -> None:
        self._files = files
        self.reads: list[str] = []

    async def read(self, args: Any, cost: Any = None) -> FileSlice:
        self.reads.append(args.repo_rel_path)
        if args.repo_rel_path not in self._files:
            raise FileNotFoundError(args.repo_rel_path)
        return FileSlice(
            repo_rel_path=args.repo_rel_path,
            start_line=1,
            end_line=-1,
            text=self._files[args.repo_rel_path],
        )


async def _run(facade: _Facade, **kwargs: Any) -> RetrievedContext:
    step = RetrieveStep(facade, **kwargs)  # type: ignore[arg-type]
    return await step.run(CTX, TaskInput(task=TASK, worktree=WORKTREE))


async def test_it_reads_every_file_the_node_names() -> None:
    facade = _Facade({"mod.py": "def f(): ...", "util.py": "X = 1"})

    result = await _run(facade, entry_files=("mod.py", "util.py"))

    assert facade.reads == ["mod.py", "util.py"]
    assert [f.repo_rel_path for f in result.files] == ["mod.py", "util.py"]


async def test_a_missing_file_is_published_not_swallowed() -> None:
    """"The model was never shown the file" and "the model was shown it and
    failed" are different diagnoses, and the second is only believable when the
    first is ruled out."""
    facade = _Facade({"mod.py": "def f(): ..."})

    result = await _run(facade, entry_files=("mod.py", "gone.py"))

    assert [f.repo_rel_path for f in result.files] == ["mod.py"]
    assert result.missing and "gone.py" in result.missing[0]


async def test_the_byte_ceiling_truncates_rather_than_blowing_the_prompt() -> None:
    facade = _Facade({"big.py": "x" * 5000})

    result = await _run(facade, entry_files=("big.py",), max_bytes=100)

    assert len(result.files[0].text) == 100


async def test_a_file_past_the_ceiling_is_reported_as_missing() -> None:
    facade = _Facade({"a.py": "x" * 100, "b.py": "y" * 100})

    result = await _run(facade, entry_files=("a.py", "b.py"), max_bytes=100)

    assert [f.repo_rel_path for f in result.files] == ["a.py"]
    assert result.missing and "b.py" in result.missing[0]


async def test_the_single_file_view_still_works_for_sprint_2_callers() -> None:
    facade = _Facade({"mod.py": "def f(): ..."})

    result = await _run(facade, entry_files=("mod.py",))

    assert result.file_slice is not None
    assert result.file_slice.repo_rel_path == "mod.py"


async def test_no_files_is_a_valid_state_not_a_crash() -> None:
    result = await _run(_Facade({}), entry_files=("nothing.py",))

    assert result.files == ()
    assert result.file_slice is None
    assert result.instructions == "Fix f()."


async def test_retrieved_files_reach_the_model_prompt() -> None:
    """The end of the chain that was broken: content read here must appear in
    the request the generate node builds."""
    from aether.domain.model_io import ModelRequest, StopEvent
    from aether.workflow.nodes.generate import GenerateStep

    class _ModelFacade:
        def __init__(self) -> None:
            self.request: ModelRequest | None = None

        async def model(self, request: ModelRequest, cost: Any) -> list[Any]:
            self.request = request
            return [StopEvent(reason="end")]

    retrieved = await _run(_Facade({"mod.py": "def f(a, b):\n    return a - b\n"}),
                           entry_files=("mod.py",))
    facade = _ModelFacade()
    await GenerateStep(facade, model_name="m").run(CTX, retrieved)  # type: ignore[arg-type]

    assert facade.request is not None
    prompt = "".join(
        span.text for message in facade.request.messages for span in message.spans
    )
    assert "return a - b" in prompt  # the actual source, not a hallucinated stand-in
    assert "mod.py" in prompt
    assert facade.request.messages[0].role == "system"  # the L1 seed leads
