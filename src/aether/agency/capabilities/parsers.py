"""`OutputParser` — how a model's reply is read, and, beside it, what was
asked for (`TASK-055`). Follows `EditFormat`'s template: the prompt that
states a contract and the parser that reads the answer are one object, so
they cannot disagree.

`ParsedOutput` is the one shape every parser returns so `ModelNode` (T5)
reads a uniform type regardless of which role's parser ran; each parser
fills only the field its own contract produces.
"""

from __future__ import annotations

from typing import Any, Literal, Protocol, runtime_checkable

from aether.agency.capabilities.edit_format import EditFormat, ParsedEdit, get_edit_format
from aether.agency.registry import Registry
from aether.domain.envelope import Envelope
from aether.domain.ids import Frozen
from aether.domain.task import Task
from aether.domain.workspace import WorktreeRef

ARCHITECT_INSTRUCTIONS = (
    "Output a short 3-line analysis plan listing:\n"
    "1. Target function/class\n"
    "2. Expected behavior vs current bug\n"
    "3. Proposed code fix logic"
)

REFLECTOR_INSTRUCTIONS = (
    "Analyze the test failure traceback and output a 2-line correction instruction "
    "stating what was wrong in the previous attempt and how to fix it."
)


class ParsedOutput(Frozen):
    kind: Literal["edit", "text"]
    edit: ParsedEdit | None = None
    text: str = ""

    def into(self, payload: Envelope, result: Any = None, output_type: type[Any] | None = None) -> Any:
        """Fold this parse into the node's output payload."""
        from aether.domain.envelope import GeneratedPatch

        task: Task = payload.task
        worktree: WorktreeRef = payload.worktree
        iteration: int = getattr(payload, "iteration", 0)
        retrieved_files: tuple[str, ...] = getattr(payload, "retrieved_files", ())
        if not retrieved_files and hasattr(payload, "files"):
            retrieved_files = tuple(f.repo_rel_path for f in getattr(payload, "files", ()))
        stop_reason: str = getattr(result, "stop_reason", "end") if result else "end"
        text: str = result.text if result and hasattr(result, "text") else self.text

        target_cls: Any = output_type if output_type is not None else payload.__class__
        if target_cls.__name__ == "RetrievedContext":
            return target_cls(
                task=task,
                worktree=worktree,
                instructions=getattr(payload, "instructions", getattr(task, "instructions", "")),
                files=getattr(payload, "files", ()),
                missing=getattr(payload, "missing", ()),
                plan=text,
            )

        return GeneratedPatch(
            task=task,
            worktree=worktree,
            raw_output=text,
            stop_reason=stop_reason,
            iteration=iteration,
            retrieved_files=retrieved_files,
        )


@runtime_checkable
class OutputParser(Protocol):
    name: str

    def instructions(self) -> str: ...

    def parse(
        self,
        raw: str,
        known_files: tuple[str, ...] = (),
        test_paths: tuple[str, ...] = (),
    ) -> ParsedOutput: ...


class EditFormatParser:
    """Delegates to an `EditFormat` — `edit_format.py` is left alone
    (`sprint-05.md` Task 3 AC4); this wraps it so `ModelNode` reads the same
    `ParsedOutput` shape regardless of which parser its role uses. Registered
    once per format name (`edit:unified_diff`, `edit:whole_file_codeblock`)
    so `RoleSpec.parser` stays a bare string."""

    def __init__(self, edit_format_name: str) -> None:
        self._format: EditFormat = get_edit_format(edit_format_name)
        self.name = f"edit:{edit_format_name}"

    def instructions(self) -> str:
        return self._format.instructions()

    def parse(
        self,
        raw: str,
        known_files: tuple[str, ...] = (),
        test_paths: tuple[str, ...] = (),
    ) -> ParsedOutput:
        return ParsedOutput(
            kind="edit",
            edit=self._format.parse(raw, known_files=known_files, test_paths=test_paths),
        )


class PlanParser:
    """Architect output: a short free-text plan, read back verbatim."""

    name = "plan"

    def instructions(self) -> str:
        return ARCHITECT_INSTRUCTIONS

    def parse(self, raw: str, *args: Any, **kwargs: Any) -> ParsedOutput:
        return ParsedOutput(kind="text", text=raw.strip())


class LessonParser:
    """Reflector output: a short correction instruction."""

    name = "lesson"

    def instructions(self) -> str:
        return REFLECTOR_INSTRUCTIONS

    def parse(self, raw: str, *args: Any, **kwargs: Any) -> ParsedOutput:
        return ParsedOutput(kind="text", text=raw.strip())


class PassthroughText:
    """No output contract; the reply is read back verbatim."""

    name = "text"

    def instructions(self) -> str:
        return ""

    def parse(self, raw: str, *args: Any, **kwargs: Any) -> ParsedOutput:
        return ParsedOutput(kind="text", text=raw)


class UnknownParser(Exception):
    """Raised at construction. A role naming a parser nobody implements must
    fail at load, not at the moment the first reply arrives."""


PARSERS: dict[str, OutputParser] = {
    "edit:unified_diff": EditFormatParser("unified_diff"),
    "edit:whole_file_codeblock": EditFormatParser("whole_file_codeblock"),
    PlanParser.name: PlanParser(),
    LessonParser.name: LessonParser(),
    PassthroughText.name: PassthroughText(),
}
_REGISTRY: Registry[OutputParser] = Registry("output parser", PARSERS, unknown=UnknownParser)


def get_parser(name: str) -> OutputParser:
    return _REGISTRY.get(name)


__all__ = [
    "ARCHITECT_INSTRUCTIONS",
    "PARSERS",
    "REFLECTOR_INSTRUCTIONS",
    "EditFormatParser",
    "LessonParser",
    "OutputParser",
    "ParsedOutput",
    "PassthroughText",
    "PlanParser",
    "UnknownParser",
    "get_parser",
]
