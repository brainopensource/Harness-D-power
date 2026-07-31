"""Dev-mode subprocess Workspace rooted at a directory — Sprint 3a."""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path

from sagiha.domain.content import CommandResult
from sagiha.domain.work import EditRequest, EditResult, HunkResult


def resolve_within(root: Path, path: str) -> Path:
    """Resolve `path` under `root`, refusing anything that escapes it.

    Uses `Path.is_relative_to` rather than string prefixing: a `startswith`
    comparison admits sibling directories that merely share a name prefix
    (root `/w/proj` would accept `/w/proj-evil/secrets`). Resolving first also
    closes the symlink escape that a purely lexical check cannot see.
    """
    candidate = (root / path).resolve()
    if not candidate.is_relative_to(root):
        raise PermissionError(f"Path escapes workspace root: {path}")
    return candidate


class LocalWorkspace:
    """Filesystem workspace for interactive/dev autonomy (no container)."""

    def __init__(self, root: str) -> None:
        self._root = Path(root).resolve()

    @property
    def root(self) -> Path:
        return self._root

    def _resolve(self, path: str) -> Path:
        return resolve_within(self._root, path)

    async def read(self, path: str, offset: int = 0, limit: int | None = None) -> str:
        target = self._resolve(path)
        text = await asyncio.to_thread(target.read_text, encoding="utf-8")
        lines = text.splitlines(keepends=True)
        end = None if limit is None else offset + limit
        return "".join(lines[offset:end])

    async def write(self, path: str, content: str) -> None:
        target = self._resolve(path)
        await asyncio.to_thread(target.parent.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(target.write_text, content, encoding="utf-8")

    async def apply_edit(self, request: EditRequest) -> EditResult:
        target = self._resolve(request.path)
        original = await asyncio.to_thread(target.read_text, encoding="utf-8")
        text = original
        hunks: list[HunkResult] = []
        for index, edit in enumerate(request.edits):
            if edit.old_string == "":
                text = edit.new_string + text
                hunks.append(HunkResult(applied=True, index=index, reason="ok"))
                continue
            count = text.count(edit.old_string)
            if count == 0:
                hunks.append(HunkResult(applied=False, index=index, reason="anchor_not_found"))
                break
            if count != edit.expected_occurrences:
                hunks.append(HunkResult(applied=False, index=index, reason="ambiguous_anchor"))
                break
            text = text.replace(edit.old_string, edit.new_string, edit.expected_occurrences)
            hunks.append(HunkResult(applied=True, index=index, reason="ok"))
        else:
            await asyncio.to_thread(target.write_text, text, encoding="utf-8")
            return EditResult(hunks=tuple(hunks), syntax_valid=True)

        # Failures after first miss: mark remaining skipped
        while len(hunks) < len(request.edits):
            hunks.append(
                HunkResult(
                    applied=False,
                    index=len(hunks),
                    reason="skipped_after_failure",
                )
            )
        return EditResult(hunks=tuple(hunks), syntax_valid=True)

    async def run(self, command: list[str]) -> CommandResult:
        start = time.monotonic()
        proc = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(self._root),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "PWD": str(self._root)},
        )
        stdout_b, stderr_b = await proc.communicate()
        duration_ms = (time.monotonic() - start) * 1000.0
        return CommandResult(
            exit_code=proc.returncode or 0,
            stdout=stdout_b.decode("utf-8", errors="replace"),
            stderr=stderr_b.decode("utf-8", errors="replace"),
            duration_ms=duration_ms,
        )

    async def checkpoint(self, label: str) -> str:
        """Return the current HEAD sha — the ref the coding gates diff against.

        This returned `label` before PR-1a, i.e. it claimed to be a commit sha and was
        not one. `RunContext.base_commit` is derived from this, and a gate diffing
        against a made-up ref reports nothing useful, so the lie propagated straight
        into the evaluator.

        Raises `RuntimeError` when the workspace is not a git repository. Callers must
        not treat that as "no changes" — `RunLoop` leaves `base_commit` unset and the
        gates fail closed.
        """
        result = await self.run(["git", "rev-parse", "HEAD"])
        if result.exit_code != 0:
            raise RuntimeError(
                f"checkpoint({label!r}) failed: workspace at {self.root} is not a git "
                f"repository or has no commits — {result.stderr.strip()}"
            )
        return result.stdout.strip()

    async def restore(self, commit_sha: str) -> None:
        return None


def list_dir_entries(root: Path, path: str = ".") -> list[dict[str, str | int | None]]:
    base = resolve_within(root.resolve(), path)
    entries: list[dict[str, str | int | None]] = []
    for child in sorted(base.iterdir(), key=lambda p: p.name):
        kind = "dir" if child.is_dir() else "file"
        if child.is_symlink():
            kind = "symlink"
        size = child.stat().st_size if child.is_file() else None
        entries.append(
            {
                "path": str(child.relative_to(root)),
                "kind": kind,
                "size_bytes": size,
            }
        )
    return entries


def grep_workspace(root: Path, pattern: str, path: str = ".") -> list[dict[str, str | int]]:
    import re

    base = resolve_within(root.resolve(), path)
    rx = re.compile(pattern)
    matches: list[dict[str, str | int]] = []
    files = [base] if base.is_file() else list(base.rglob("*"))
    for file in files:
        if not file.is_file():
            continue
        try:
            text = file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            if rx.search(line):
                matches.append(
                    {
                        "path": str(file.relative_to(root)),
                        "line": i,
                        "text": line,
                    }
                )
                if len(matches) >= 200:
                    return matches
    return matches
