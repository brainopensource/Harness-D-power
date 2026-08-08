"""Standalone experimental edit-format parser — Tier 1 + Tier 2 fixes from the
small-model investigation. Does NOT modify anything under src/aether/.

Imports the real `WholeFileCodeblockFormat` read-only, for baseline comparison
and to reuse its `FileEdit`/`ParsedEdit` domain shapes. Everything new lives
here. If this earns its way into src/aether/, it becomes a registered
EditFormat per the Protocol + registry pattern in workflow/edit_format.py.

Tier 1 (parser tolerance, all pure functions):
  1. Accept `#+` (one or more hashes) before a filename comment, not just `#`.
     A markdown-trained small model writes `### main.py`; the original only
     accepted a single `#`.
  2. An empty path after `python:` (```python:` with nothing) falls through
     to unlabelled recovery instead of hard-erroring, so a `# path` line
     inside the block still gets a chance.
  3. A leading `/` is stripped, but ONLY when the resulting relative path's
     basename matches a file the harness actually retrieved and showed the
     model (`known_files`). This does not touch the `..` traversal guard —
     that check still runs on the stripped path.

Tier 2 (bind to retrieved context, zero model-authored text is trusted):
  4. If exactly one non-test file was retrieved AND exactly one unlabelled,
     unresolvable fenced block came back, bind them. This is categorically
     different from the deleted F7 fallbacks (which parsed a path out of
     model prose, and so could latch onto `run_tests.py` quoted in a repair
     prompt): here the path comes from the harness's own retrieval record,
     never from anything the model wrote. Guarded by refusing any path in
     `test_paths`.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from aether.workflow.edit_format import (  # noqa: E402  (read-only import, baseline for comparison)
    FileEdit,
    ParsedEdit,
    WholeFileCodeblockFormat,
)

_FENCE = re.compile(r"```(?:python|py)?[:\s]*(?P<path>[\w./\-]+\.py)\s*\n(?P<code>.*?)```", re.DOTALL)
_EMPTY_LABEL_FENCE = re.compile(r"```(?:python|py):\s*\n(?P<code>.*?)```", re.DOTALL)
_UNLABELLED_FENCE = re.compile(r"```(?:python|py)?\s*\n(?P<code>.*?)```", re.DOTALL)
# Tier 1.1 — one or more '#', optional "filename:" prefix.
_COMMENT_FILE = re.compile(r"^#+\s*(?:filename:\s*)?([\w./\-]+\.py)")
_HEADER_FILE = re.compile(r"===\s*([\w./\-]+\.py)\s*===")


class ImprovedWholeFileCodeblockFormat:
    """Drop-in replacement for `WholeFileCodeblockFormat` with Tier 1 + Tier 2
    tolerance. Constructed with the harness context a real `ApplyStep` already
    has on hand (`RetrievedContext.files`, `Task.test_paths`), so it can only
    ever bind a path the harness itself retrieved — never one guessed out of
    the model's prose.
    """

    name = "whole_file_codeblock_improved"

    def __init__(self, known_files: tuple[str, ...] = (), test_paths: tuple[str, ...] = ()) -> None:
        self._known_files = known_files
        self._test_paths = set(test_paths)

    def instructions(self) -> str:
        return WholeFileCodeblockFormat().instructions()

    def parse(self, raw: str) -> ParsedEdit:
        files: list[FileEdit] = []
        errors: list[str] = []

        # Pass 1 — canonical, unchanged from the original.
        consumed_spans: list[tuple[int, int]] = []
        for match in _FENCE.finditer(raw):
            path = match.group("path").strip()
            code = match.group("code").strip()
            resolved = self._resolve_path(path, errors)
            if resolved is None:
                continue
            if not self._syntax_ok(resolved, code, errors):
                continue
            files.append(FileEdit(repo_rel_path=resolved, text=code + "\n"))
            consumed_spans.append(match.span())

        if files or errors:
            return ParsedEdit(kind="whole_files", files=tuple(files), errors=tuple(errors))

        # Pass 2 — every fence that Pass 1 did NOT already resolve: an empty
        # label (```python:`) or no label at all. Both are candidates for
        # comment/header recovery (Tier 1.1) and, failing that, Tier 2
        # binding — an empty label is not meaningfully different from no
        # label at all once Pass 1 has already had first refusal.
        candidate_blocks = list(_EMPTY_LABEL_FENCE.finditer(raw)) or list(_UNLABELLED_FENCE.finditer(raw))
        recovered_any_label = False
        for match in candidate_blocks:
            code = match.group("code").strip()
            path = self._label_from_context(code, raw[: match.start()])
            if path is None:
                continue
            recovered_any_label = True
            resolved = self._resolve_path(path, errors)
            if resolved is None:
                continue
            if not self._syntax_ok(resolved, code, errors):
                continue
            files.append(FileEdit(repo_rel_path=resolved, text=code + "\n"))

        if files:
            return ParsedEdit(kind="whole_files", files=tuple(files), errors=tuple(errors))

        # Tier 2 — bind an unlabelled block to the sole retrieved file, only
        # when there is exactly one of each and no label was recoverable
        # (i.e. this is not overriding a model that did state a path).
        eligible_files = [f for f in self._known_files if f not in self._test_paths]
        if not recovered_any_label and len(candidate_blocks) == 1 and len(eligible_files) == 1:
            match = candidate_blocks[0]
            code = match.group("code").strip()
            target = eligible_files[0]
            if self._syntax_ok(target, code, errors):
                return ParsedEdit(
                    kind="whole_files",
                    files=(FileEdit(repo_rel_path=target, text=code + "\n"),),
                    errors=(f"bound unlabelled block to the sole retrieved file {target!r} (Tier 2)",),
                )

        if not files and not errors and raw.strip():
            errors.append("no labelled ```python:<path> block found in the model's output")
        return ParsedEdit(kind="whole_files", files=tuple(files), errors=tuple(errors))

    # ------------------------------------------------------------- helpers

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

    def _resolve_path(self, path: str, errors: list[str]) -> str | None:
        """Tier 1.3: strip a leading '/' only when the basename matches a
        retrieved file. The traversal guard (`..`) always applies, on the
        stripped path — a leading slash never bypasses it.
        """
        candidate = path
        if path.startswith("/"):
            stripped = path.lstrip("/")
            basenames = {Path(f).name for f in self._known_files}
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
