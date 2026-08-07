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

    def parse(self, raw: str) -> ParsedEdit: ...


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

    def parse(self, raw: str) -> ParsedEdit:
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

    def parse(self, raw: str) -> ParsedEdit:
        files: list[FileEdit] = []
        errors: list[str] = []
        for match in _FENCE.finditer(raw):
            path = match.group("path").strip()
            code = match.group("code").strip()
            # A model-supplied path is untrusted input. Tier 1 produced
            # `/storage.py` on the first run; caught here it becomes an error
            # the repair edge can read, instead of an adapter exception.
            if path.startswith("/") or ".." in Path(path).parts:
                errors.append(f"{path}: path must be repo-relative and must not escape the worktree")
                continue
            try:
                ast.parse(code)
            except SyntaxError as exc:
                # A detected bad edit, named. Writing it and letting the tests
                # fail would report the wrong cause.
                errors.append(f"{path}: not valid Python ({exc.msg} at line {exc.lineno})")
                continue
            files.append(FileEdit(repo_rel_path=path, text=code + "\n"))

        if not files and not errors:
            _UNLABELLED_FENCE = re.compile(r"```(?:python|py)?\s*\n(?P<code>.*?)```", re.DOTALL)
            _HEADER_FILE = re.compile(r"===\s*([\w./\-]+\.py)\s*===")
            _COMMENT_FILE = re.compile(r"^#\s*(?:filename:\s*)?([\w./\-]+\.py)")
            
            for match in _UNLABELLED_FENCE.finditer(raw):
                code = match.group("code").strip()
                path = None
                
                lines = code.splitlines()
                if lines:
                    m = _COMMENT_FILE.match(lines[0])
                    if m:
                        path = m.group(1)
                
                if not path:
                    before_text = raw[:match.start()]
                    headers = _HEADER_FILE.findall(before_text)
                    if headers:
                        path = headers[-1]
                        
                if not path:
                    py_files = [f for f in set(re.findall(r"\b[\w./\-]+\.py\b", raw)) if f.endswith(".py")]
                    if len(py_files) == 1:
                        path = py_files[0]

                if not path:
                    # Single file mode fallback when target is present in prompt context
                    match_mod = re.search(r"\b([\w./\-]+\.py)\b", raw)
                    if match_mod:
                        path = match_mod.group(1)

                if path:
                    if path.startswith("/") or ".." in Path(path).parts:
                        errors.append(f"{path}: path must be repo-relative and must not escape the worktree")
                        continue
                    try:
                        ast.parse(code)
                    except SyntaxError as exc:
                        errors.append(f"{path}: not valid Python ({exc.msg} at line {exc.lineno})")
                        continue
                    files.append(FileEdit(repo_rel_path=path, text=code + "\n"))
                else:
                    errors.append("unlabelled codeblock found but could not infer file path")

        if not files and not errors and raw.strip():
            errors.append("no labelled ```python:<path> block found in the model's output")
        return ParsedEdit(kind="whole_files", files=tuple(files), errors=tuple(errors))


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
