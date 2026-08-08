"""Edit formats — how a model is asked to express a change, as a swappable box.

Sprint 3 hard-coded one answer: the model emits a unified diff and
`git apply` applies it. Two things were wrong with that as a *structure*. It
put a format decision inside a node, so choosing differently meant editing the
node; and it made the format un-ablatable, when the format is exactly the kind
of mechanism `spec.md` §7 says must clear the noise floor before it promotes.

Small models are the reason this matters now. Locally, qwen2.5:1.5b and
llama3.2:3b both emit *well-formed* diffs whose content is wrong — one "fixed"
a function's signature line and left the buggy body. The same class of model
succeeds on the same tasks when asked for whole files with the path in the
fence, which is what `Aether-D-bench/test_openrouter.py` demonstrated. Which of
those is better is an empirical question, so this module makes both expressible
and lets the measurement decide.

**Deliberately pure.** A format states what to ask for and parses what comes
back; it performs no I/O. `ApplyStep` turns a `ParsedEdit` into effects through
the dispatch facade, so the choke point (I5) still sees every write, and a
format can be unit-tested without a worktree.

Adding a third format — SEARCH/REPLACE blocks, say — is a class here and a
registry entry; no node changes.

**Moved from `workflow/edit_format.py` to `agency/capabilities/edit_format.py`
(TASK-055, ADR-0018).** Unchanged otherwise — this was already the best
abstraction in the codebase and the template `capability_layer.md` §2.1 names
for every other capability protocol in this layer. It is pure
(`aether.domain.ids.Frozen` is its only import), so it is consumed by both
`ApplyStep` in `workflow/` (downward — legal) and `agency.capabilities.parsers
.EditFormatParser` here. `workflow/edit_format.py` re-exports every name for
one release.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

from aether.domain.ids import Frozen

#: The default stays `unified_diff` because nothing has beaten it *on our
#: instrument* yet. `spec.md` §7: no mechanism promotes without an ablation
#: clearing the floor, and "it looked better in a demo" is not that.
DEFAULT_EDIT_FORMAT = "unified_diff"


class FileEdit(Frozen):
    repo_rel_path: str
    text: str


class ParsedEdit(Frozen):
    """What a model's output turned out to contain.

    `errors` is not decoration: a whole-file block that fails to parse as
    Python is a *detected* bad edit, and detecting it here means the repair
    edge can be told what was wrong instead of watching the tests fail for an
    unrelated-looking reason.
    """

    kind: Literal["unified_diff", "whole_files"]
    unified_diff: str = ""
    files: tuple[FileEdit, ...] = ()
    errors: tuple[str, ...] = ()

    @property
    def is_empty(self) -> bool:
        return not self.unified_diff.strip() and not self.files


@runtime_checkable
class EditFormat(Protocol):
    """One way of asking for, and reading back, a change."""

    name: str

    def instructions(self) -> str:
        """The output contract handed to the model, verbatim, in the system
        layer. Kept beside the parser on purpose: a prompt that asks for one
        shape while the parser expects another is a bug that presents as "the
        model is bad"."""
        ...

    def parse(
        self,
        raw: str,
        known_files: tuple[str, ...] = (),
        test_paths: tuple[str, ...] = (),
    ) -> ParsedEdit: ...


_DIFF_START = ("diff --git", "--- ", "+++ ", "@@ ")


class UnifiedDiffFormat:
    """`diff --git` output, applied with `git apply`.

    The parser is the fence-stripping logic that used to live inline in
    `GenerateStep`, moved here so it has a name and tests. Models wrap diffs in
    markdown fences and prose constantly; dropping everything before the first
    diff marker is what makes the common case work at all.
    """

    name = "unified_diff"

    def instructions(self) -> str:
        return (
            "Reply with a unified diff and nothing else.\n"
            "Use `diff --git a/<path> b/<path>` headers with `---`/`+++` lines and `@@` hunks.\n"
            "Context lines must match the file exactly. Do not explain the change."
        )

    def parse(
        self,
        raw: str,
        known_files: tuple[str, ...] = (),
        test_paths: tuple[str, ...] = (),
    ) -> ParsedEdit:
        kept: list[str] = []
        in_diff = False
        for line in raw.splitlines():
            if line.startswith("```"):
                continue
            if line.startswith(_DIFF_START):
                in_diff = True
            if in_diff:
                kept.append(line)

        if not kept:
            return ParsedEdit(
                kind="unified_diff",
                unified_diff="",
                errors=("no diff header found in the model's output",) if raw.strip() else (),
            )
        return ParsedEdit(kind="unified_diff", unified_diff="\n".join(kept) + "\n")


_FENCE = re.compile(r"```(?:python|py)?[:\s]*(?P<path>[\w./\-]+\.py)\s*\n(?P<code>.*?)```", re.DOTALL)

#: Recovery for models that fence code without labelling the fence itself.
_EMPTY_LABEL_FENCE = re.compile(r"```(?:python|py):\s*\n(?P<code>.*?)```", re.DOTALL)
_UNLABELLED_FENCE = re.compile(r"```(?:python|py)?\s*\n(?P<code>.*?)```", re.DOTALL)
_HEADER_FILE = re.compile(r"===\s*([\w./\-]+\.py)\s*===")
_COMMENT_FILE = re.compile(r"^#+\s*(?:filename:\s*)?([\w./\-]+\.py)")


class WholeFileCodeblockFormat:
    """Complete files in fenced blocks labelled with their path.

    Two properties a diff does not have: the model never has to reproduce
    context lines exactly (the commonest way a small model's diff fails to
    apply), and the result is **syntax-checkable before it touches the
    worktree** — `ast.parse` rejects a broken file here rather than letting the
    test runner report a confusing error later.

    The cost is honest and worth stating: whole files burn output tokens
    proportional to file size, and a large file may not fit the completion
    ceiling at all. That is precisely the trade the M2 ablation measures.
    """

    name = "whole_file_codeblock"

    def instructions(self) -> str:
        return (
            "Reply with the COMPLETE contents of each file you change, and nothing else.\n"
            "Use one fenced block per file, labelled with its path:\n"
            "```python:path/to/file.py\n"
            "# the complete file, not a fragment\n"
            "```\n"
            "Do not use diffs, ellipses, or `# unchanged` placeholders."
        )

    def parse(
        self,
        raw: str,
        known_files: tuple[str, ...] = (),
        test_paths: tuple[str, ...] = (),
    ) -> ParsedEdit:
        files: list[FileEdit] = []
        errors: list[str] = []

        # Pass 1 — canonical, labelled blocks.
        for match in _FENCE.finditer(raw):
            path = match.group("path").strip()
            code = match.group("code").strip()
            resolved = self._resolve_path(path, known_files, errors)
            if resolved is None:
                continue
            if not self._syntax_ok(resolved, code, errors):
                continue
            files.append(FileEdit(repo_rel_path=resolved, text=code + "\n"))

        if files or errors:
            return ParsedEdit(kind="whole_files", files=tuple(files), errors=tuple(errors))

        # Pass 2 — unlabelled or empty-labelled blocks (e.g. ```python:).
        candidate_blocks = list(_EMPTY_LABEL_FENCE.finditer(raw)) or list(_UNLABELLED_FENCE.finditer(raw))
        recovered_any_label = False
        for match in candidate_blocks:
            code = match.group("code").strip()
            path = self._label_from_context(code, raw[: match.start()])
            if path is None:
                continue
            recovered_any_label = True
            resolved = self._resolve_path(path, known_files, errors)
            if resolved is None:
                continue
            if not self._syntax_ok(resolved, code, errors):
                continue
            files.append(FileEdit(repo_rel_path=resolved, text=code + "\n"))

        if files:
            return ParsedEdit(kind="whole_files", files=tuple(files), errors=tuple(errors))

        # Tier 2 — bind an unlabelled block to the sole retrieved non-test file,
        # only when there is exactly one unlabelled block and one eligible file,
        # and no label was recovered from the model's output.
        test_paths_set = set(test_paths)
        eligible_files = [f for f in known_files if f not in test_paths_set]
        if not recovered_any_label and len(candidate_blocks) == 1 and len(eligible_files) == 1:
            match = candidate_blocks[0]
            code = match.group("code").strip()
            target = eligible_files[0]
            if self._syntax_ok(target, code, errors):
                return ParsedEdit(
                    kind="whole_files",
                    files=(FileEdit(repo_rel_path=target, text=code + "\n"),),
                    errors=(),
                )

        if not files and not errors and raw.strip():
            errors.append("no labelled ```python:<path> block found in the model's output")
        return ParsedEdit(kind="whole_files", files=tuple(files), errors=tuple(errors))

    def _label_from_context(self, code: str, preceding_text: str) -> str | None:
        lines = code.splitlines()
        if lines:
            labelled = _COMMENT_FILE.match(lines[0])
            if labelled:
                return labelled.group(1)
        headers = _HEADER_FILE.findall(preceding_text)
        if headers:
            return headers[-1]
        return None

    def _resolve_path(self, path: str, known_files: tuple[str, ...], errors: list[str]) -> str | None:
        """Tier 1.3: strip a leading '/' only when the basename matches a
        retrieved file. The traversal guard (`..`) always applies, on the
        stripped path — a leading slash never bypasses it.
        """
        candidate = path
        if path.startswith("/"):
            stripped = path.lstrip("/")
            basenames = {Path(f).name for f in known_files}
            if Path(stripped).name in basenames:
                candidate = stripped
            else:
                errors.append(f"{path}: path must be repo-relative and must not escape the worktree")
                return None
        if ".." in Path(candidate).parts:
            errors.append(f"{path}: path must be repo-relative and must not escape the worktree")
            return None
        return candidate

    def _syntax_ok(self, path: str, code: str, errors: list[str]) -> bool:
        try:
            ast.parse(code)
        except SyntaxError as exc:
            errors.append(f"{path}: not valid Python ({exc.msg} at line {exc.lineno})")
            return False
        return True


FORMATS: dict[str, EditFormat] = {
    UnifiedDiffFormat.name: UnifiedDiffFormat(),
    WholeFileCodeblockFormat.name: WholeFileCodeblockFormat(),
}


class UnknownEditFormat(Exception):
    """Raised at construction. A topology naming a format nobody implements
    must fail at load, not at the moment the model's first answer arrives."""


def get_edit_format(name: str) -> EditFormat:
    fmt = FORMATS.get(name)
    if fmt is None:
        raise UnknownEditFormat(f"unknown edit_format {name!r}; registered: {sorted(FORMATS)}")
    return fmt


__all__ = [
    "DEFAULT_EDIT_FORMAT",
    "FORMATS",
    "EditFormat",
    "FileEdit",
    "ParsedEdit",
    "UnifiedDiffFormat",
    "UnknownEditFormat",
    "WholeFileCodeblockFormat",
    "get_edit_format",
]
