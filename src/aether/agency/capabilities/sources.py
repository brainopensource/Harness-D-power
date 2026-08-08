"""`ContextSource` — *what goes in the prompt, and under whose authority*
(`TASK-054`, ADR-0010, ADR-0015).

Closes two audit findings (`capability_layer.md` §1):

* **A4.** A block's `Provenance` label is a property of its **source class**,
  declared once here, never decided ad hoc at a `TaintSpan(...)` call site.
  Repository content and test tracebacks both used to end up labelled
  `Provenance.AGENT` because ten call sites across three node files each made
  that call independently; here it is made once, per class.
* **A5.** "Read these files into a prompt block" used to be implemented
  twice, with different semantics: `retrieve.py:67-93` enforced a byte
  budget and published what it could not read; `repair.py:122-132` had no
  budget and swallowed every read failure into an opaque string the model
  then read as file content. `_budgeted_read` below is the one policy both
  `EntryFileSource` and `CurrentFileSource` use.

Follows `workflow/edit_format.py`'s registry template
(`coding_guidelines.md` §2.1): one `Protocol`, one dict, one
`UnknownSource` raised at the name-resolution call site, never at the
moment a prompt is first assembled.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from aether.agency.dispatch import EffectDispatch
from aether.agency.registry import Registry
from aether.domain.context import ContextBlock, ContextRequest, Layer
from aether.domain.effects import IndexArgs, ReadArgs
from aether.domain.taint import Provenance
from aether.domain.text import tail_biased

#: `REPAIR_OUTPUT_CHARS` in `workflow/nodes/repair.py` today — the same
#: budget, so a repair prompt built through this source truncates identically
#: to the one built inline, and the repair prompt and the gate never disagree
#: about what the failure was (repair.py's own module docstring, point 3).
_DEFAULT_GATE_TAIL = 3000


@runtime_checkable
class ContextSource(Protocol):
    """What goes in the prompt, and under whose authority. `layer` and
    `label` are declared on the class — a property of the source, not a
    per-call decision — so nothing downstream of `gather()` ever has to
    guess who is speaking."""

    name: str
    layer: Layer
    label: Provenance

    async def gather(self, dispatch: EffectDispatch, req: ContextRequest) -> tuple[ContextBlock, ...]: ...


def _missing_block(
    path: str, reason: str, *, layer: Layer, label: Provenance, source_id: str
) -> ContextBlock:
    """Published, not swallowed (`coding_guidelines.md` §2.5): "the model was
    not shown the file" and "the model was shown the file and failed" are
    different diagnoses, and the second is only believable when the first is
    excluded."""
    return ContextBlock(
        layer=layer,
        label=label,
        heading=f"=== {path} (not shown) ===",
        text=f"(not shown: {reason})",
        source_id=source_id,
    )


async def _budgeted_read(
    dispatch: EffectDispatch,
    req: ContextRequest,
    paths: tuple[str, ...],
    *,
    layer: Layer,
    label: Provenance,
    source_id: str,
) -> tuple[ContextBlock, ...]:
    """The one byte-budget policy both file sources use — `retrieve.py`'s,
    promoted, because it is the one that publishes what it dropped."""
    blocks: list[ContextBlock] = []
    budget_left = req.max_bytes
    for repo_rel_path in paths:
        if budget_left <= 0:
            blocks.append(
                _missing_block(
                    repo_rel_path, "byte budget exhausted", layer=layer, label=label, source_id=source_id
                )
            )
            continue
        try:
            args = ReadArgs(worktree=req.worktree, repo_rel_path=repo_rel_path)
            file_slice = await dispatch.read(args)
        except Exception as exc:  # noqa: BLE001 — a missing file is a fact, not a crash
            blocks.append(
                _missing_block(
                    repo_rel_path, type(exc).__name__, layer=layer, label=label, source_id=source_id
                )
            )
            continue
        text = file_slice.text[:budget_left]
        budget_left -= len(text)
        blocks.append(
            ContextBlock(
                layer=layer, label=label, heading=f"=== {repo_rel_path} ===", text=text, source_id=source_id
            )
        )
    return tuple(blocks)


class InstructionsSource:
    """The task statement. Operator-authored — the only `OPERATOR` label in
    the whole set."""

    name = "instructions"
    layer = Layer.L4_TASK
    label = Provenance.OPERATOR

    async def gather(self, dispatch: EffectDispatch, req: ContextRequest) -> tuple[ContextBlock, ...]:
        return (ContextBlock(layer=self.layer, label=self.label, text=req.instructions, source_id=self.name),)


class EntryFileSource:
    """The files a role names, read once before any attempt. Replaces the
    byte-budgeted loop in `retrieve.py:67-93`.

    **`AGENT`, not `UNTRUSTED_EXTERNAL`, and that is a recorded, sequenced
    deviation, not a judgement call made here.** `spec.md` §5 requires
    repository content to be labelled `UNTRUSTED_EXTERNAL`; labelling it
    correctly today would make `DefaultPolicyEngine` fail closed on every
    shell tool call, because `DispatchFacade.shell` always sets
    `widens_capability=True`. Sequenced behind the shell AST classifier
    (`TASK-030a`/`TASK-030b`) and tracked in `STATUS.md`'s deviations and
    `TASK-048`. Do not "fix" this label without landing the classifier first.
    """

    name = "entry_files"
    layer = Layer.L3_REPO
    label = Provenance.AGENT

    async def gather(self, dispatch: EffectDispatch, req: ContextRequest) -> tuple[ContextBlock, ...]:
        return await _budgeted_read(
            dispatch, req, req.entry_files, layer=self.layer, label=self.label, source_id=self.name
        )


class CurrentFileSource:
    """The same files, re-read from the worktree after an attempt —
    `repair.py:122-132`'s re-read, now sharing `EntryFileSource`'s budget and
    `missing` semantics instead of a second, looser copy of both.

    Carries the same `AGENT`-not-`UNTRUSTED_EXTERNAL` deviation as
    `EntryFileSource`, for the same reason and behind the same task.
    """

    name = "current_files"
    layer = Layer.L5_DIALOGUE
    label = Provenance.AGENT

    async def gather(self, dispatch: EffectDispatch, req: ContextRequest) -> tuple[ContextBlock, ...]:
        return await _budgeted_read(
            dispatch, req, req.entry_files, layer=self.layer, label=self.label, source_id=self.name
        )


class PreviousAttemptSource:
    """The model's own prior output, verbatim (`repair.py:75`)."""

    name = "previous_attempt"
    layer = Layer.L5_DIALOGUE
    label = Provenance.AGENT

    async def gather(self, dispatch: EffectDispatch, req: ContextRequest) -> tuple[ContextBlock, ...]:
        text = req.previous_attempt.strip() or "(no patch was produced on the previous attempt)"
        return (ContextBlock(layer=self.layer, label=self.label, text=text, source_id=self.name),)


class GateOutputSource:
    """The failing test output, tail-biased — the same truncation the gate
    itself reported under (`domain.text.tail_biased`), so the prompt and the
    gate never disagree about what the failure was.

    `tail` is fixed at construction so two roles needing different budgets
    (repair: 3000 chars; reflector: 2000, `architect.py:112`'s original
    figure) register as two distinct names rather than one parametrized
    source — `RoleSpec.sources` stays a tuple of bare strings and round-trips
    through JSON (`TASK-057`).
    """

    layer = Layer.L5_DIALOGUE
    label = Provenance.AGENT

    def __init__(self, name: str, tail: int = _DEFAULT_GATE_TAIL) -> None:
        self.name = name
        self._tail = tail

    async def gather(self, dispatch: EffectDispatch, req: ContextRequest) -> tuple[ContextBlock, ...]:
        text = tail_biased(req.gate_detail, self._tail) or "(the gate reported no output)"
        return (ContextBlock(layer=self.layer, label=self.label, text=text, source_id=self.name),)


class PlanSource:
    """The architect's plan (`TASK-048`).

    **The one genuine label change T2 makes, and it is a fix.**
    `architect.py:92` today concatenates the plan into
    `payload.instructions`, which `generate.py:104-110` then labels
    `OPERATOR` — model-authored text acquiring operator authority through
    string concatenation, the exact shape I11 exists to forbid. Here the plan
    is its own block, labelled `AGENT`, and cannot be merged into an
    `OPERATOR` block because a node using this source never touches a bare
    string (`capability_layer.md` §3.2). Produces no block when there is no
    plan, so a role with no architect ahead of it (e.g. `EDITOR` alone) does
    not carry an empty "plan" section.
    """

    name = "plan"
    layer = Layer.L4_TASK
    label = Provenance.AGENT

    async def gather(self, dispatch: EffectDispatch, req: ContextRequest) -> tuple[ContextBlock, ...]:
        if not req.plan.strip():
            return ()
        return (ContextBlock(layer=self.layer, label=self.label, text=req.plan, source_id=self.name),)


class SymbolSource:
    """Wraps `TreeSitterIndexer` through the dispatcher (`index` effect
    class, T2.4) rather than holding an `Indexer` handle directly — I5:
    every effect passes the choke point, and a capability holding an adapter
    handle would be a second path to the filesystem.

    **Reachable, not shipped.** No `RoleSpec` in this sprint uses this
    source: real localization (`LexicalSource`, `TestPathSource`,
    `HistorySource`) is `TASK-064`, deliberately out of scope here
    (`sprint-05.md` anti-drift table — "resist it hardest"). This class only
    proves the mechanism exists; the query heuristic below is a placeholder,
    not a retrieval strategy, and is intentionally naive: the first
    identifier-shaped token in the task instructions, nothing more.
    """

    name = "symbols"
    layer = Layer.L3_REPO
    label = Provenance.AGENT

    def __init__(self, limit: int = 10) -> None:
        self._limit = limit

    async def gather(self, dispatch: EffectDispatch, req: ContextRequest) -> tuple[ContextBlock, ...]:
        import re

        match = re.search(r"\b[A-Za-z_][A-Za-z0-9_]*\b", req.instructions)
        if match is None:
            return ()
        query = match.group(0)
        result = await dispatch.index(IndexArgs(worktree=req.worktree, query=query, limit=self._limit))
        if not result.hits:
            return ()
        text = "\n".join(f"{h.repo_rel_path}:{h.line} {h.kind} {h.name}" for h in result.hits)
        return (
            ContextBlock(
                layer=self.layer,
                label=self.label,
                heading=f"=== symbols matching {query!r} ===",
                text=text,
                source_id=self.name,
            ),
        )


class UnknownSource(Exception):
    """Raised at construction. A role naming a source nobody implements must
    fail at load, not at the moment the first prompt is assembled."""


SOURCES: dict[str, ContextSource] = {
    InstructionsSource.name: InstructionsSource(),
    EntryFileSource.name: EntryFileSource(),
    CurrentFileSource.name: CurrentFileSource(),
    PreviousAttemptSource.name: PreviousAttemptSource(),
    "gate_output": GateOutputSource("gate_output", tail=_DEFAULT_GATE_TAIL),
    "gate_output_reflect": GateOutputSource("gate_output_reflect", tail=2000),
    PlanSource.name: PlanSource(),
    SymbolSource.name: SymbolSource(),
}
_REGISTRY: Registry[ContextSource] = Registry("context source", SOURCES, unknown=UnknownSource)


def get_source(name: str) -> ContextSource:
    return _REGISTRY.get(name)


__all__ = [
    "ContextSource",
    "CurrentFileSource",
    "EntryFileSource",
    "GateOutputSource",
    "InstructionsSource",
    "PlanSource",
    "PreviousAttemptSource",
    "SOURCES",
    "SymbolSource",
    "UnknownSource",
    "get_source",
]
