"""`RoleSpec` — roles as data (T5, `TASK-057`).

A role is a composition of capability names (`sources`, `parser`, `inference`),
a role string, and flags. Defining a new role adds NO class — which is the exit
criterion.
"""

from __future__ import annotations

from typing import Any

from aether.domain.context import ContextRequest
from aether.domain.ids import Frozen

ARCHITECT_SYSTEM_ROLE = (
    "You are a precise software architect planning a bug fix in a repository. "
    "You examine the task and entry files and output a clear, concise plan."
)

SYSTEM_ROLE = (
    "You are a precise software engineer fixing a bug in an existing repository. "
    "You are shown the relevant files. Change as little as possible."
)

REFLECTOR_SYSTEM_ROLE = (
    "You are a software engineer reflecting on a failed fix attempt. "
    "Analyze the failing test output and output a concise lesson explaining what went wrong."
)


class RoleSpec(Frozen):
    """A role is a source list, a parser, an inference strategy and a role
    string. Defining a new role adds NO class — which is the exit criterion.
    """

    role_id: str
    role_text: str
    sources: tuple[str, ...]  # names, resolved through registry at composition
    parser: str
    inference: str = "single_turn"
    wants_tools: bool = False

    def request_from(self, payload: Any) -> ContextRequest:
        """Extract a `ContextRequest` projection from any step payload."""
        task = getattr(payload, "task", None)
        worktree = getattr(payload, "worktree", None)
        instructions = getattr(task, "instructions", "") if task else ""
        entry_files = getattr(payload, "retrieved_files", ())
        if not entry_files and task:
            entry_files = getattr(task, "entry_files", ())
        plan = getattr(payload, "plan", "")
        patch_text = getattr(payload, "patch_text", "")
        if not patch_text:
            patch_text = getattr(payload, "raw_output", "")
        gate_detail = getattr(payload, "apply_detail", "")
        report = getattr(payload, "report", None)
        if report:
            gate_detail = getattr(report, "detail", "")
        iteration = getattr(payload, "iteration", 0)

        return ContextRequest(
            task=task,
            worktree=worktree,
            instructions=instructions,
            entry_files=tuple(entry_files),
            plan=plan,
            previous_attempt=patch_text,
            gate_detail=gate_detail,
            iteration=iteration,
        )


ARCHITECT = RoleSpec(
    role_id="architect",
    role_text=ARCHITECT_SYSTEM_ROLE,
    sources=("instructions", "entry_files"),
    parser="plan",
)

EDITOR = RoleSpec(
    role_id="editor",
    role_text=SYSTEM_ROLE,
    sources=("instructions", "plan", "entry_files"),
    parser="edit_format",
)

REPAIRER = RoleSpec(
    role_id="repairer",
    role_text=SYSTEM_ROLE,
    sources=("instructions", "plan", "current_files", "previous_attempt", "gate_output"),
    parser="edit_format",
)

REFLECTOR = RoleSpec(
    role_id="reflector",
    role_text=REFLECTOR_SYSTEM_ROLE,
    sources=("gate_output", "previous_attempt"),
    parser="lesson",
)

ROLES: dict[str, RoleSpec] = {
    "architect": ARCHITECT,
    "editor": EDITOR,
    "repairer": REPAIRER,
    "reflector": REFLECTOR,
}


class UnknownRole(Exception):
    """Raised when an unknown role_id is requested."""


def get_role(role_id: str) -> RoleSpec:
    if role_id not in ROLES:
        raise UnknownRole(f"Unknown role {role_id!r}; registered roles: {sorted(ROLES)}")
    return ROLES[role_id]


__all__ = [
    "ARCHITECT",
    "EDITOR",
    "REPAIRER",
    "REFLECTOR",
    "ROLES",
    "RoleSpec",
    "UnknownRole",
    "get_role",
]
