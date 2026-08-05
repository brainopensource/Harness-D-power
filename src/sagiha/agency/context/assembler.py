"""ContextAssembler — layered prompt assembly with a seed-only Layer 6.

See docs/02-architecture/prompt-architecture.md and
docs/02-architecture/context-and-cache-engineering.md, ruling recorded as ADR-0021.

Before this module, `ModelRequest` assembly was four inline lines in the middle of
`RunLoop.run`. That placement is why there was nowhere to put a compaction check, nowhere to
anchor state that must survive compaction, and nowhere to enforce the seed-only rule.

## Seed-only is enforced by shape, not by discipline

`retrieval_seed` is accepted **only** by `__init__`, and no public method takes a
`RetrievalHit`. You cannot refresh Layer 6 mid-task without editing the constructor, which is
a reviewable diff rather than a plausible-looking call. `tests/contracts/test_context_assembler.py`
asserts the absence mechanically.

The rule earns two things downstream. Layer 6 sits *underneath* the entire append-only tail,
so refreshing it invalidates every cached token after it — the saving from fresher context
never pays for a full prefix re-encode. And because nothing rewrites Layer 6 mid-run,
`v2-S7`'s interrupt-and-steer can be a pure tail append with the prefix cache intact.

## Anchored state lives outside the transcript

The task spec, acceptance criteria, plan, open-file set, and unresolved diagnostics are
structured state re-rendered into the prefix on **every** assembly. They are never entrusted
to a compaction summary, because a summary is lossy by definition and these are precisely the
things a long run cannot afford to lose. This is what makes it safe for the compactor to drop
the middle of the transcript at all.
"""

from __future__ import annotations

import hashlib

from pydantic import BaseModel, ConfigDict

from sagiha.agency.context.compactor import Exchange, ExchangeCompactor, TruncatingCompactor
from sagiha.agency.context.tokens import estimate_tokens, message_tokens
from sagiha.domain.config import ContextConfig
from sagiha.domain.content import (
    ContentBlock,
    Message,
    ModelRequest,
    TextBlock,
    ToolResult,
    ToolResultBlock,
    ToolSchema,
    ToolUseBlock,
    wrap_untrusted,
)
from sagiha.domain.graph import DiagnosticItem, RetrievalHit
from sagiha.domain.trajectory import TrajectoryStep
from sagiha.domain.work import TaskSpec

#: Tool arguments that name a file. Used to derive the open-file set from the transcript so
#: callers do not have to remember to report it. Kept here rather than read from
#: `x-sagiha-path` schema markers because the assembler has no registry reference — and a
#: missed entry costs a line of anchored state, never a security property (the authoritative
#: path scoping is `kernel/policy/engine.py`).
_PATH_ARGS: tuple[str, ...] = ("path", "file_path")

#: Tools whose invocation means "this file is being worked on".
_OPEN_FILE_TOOLS: frozenset[str] = frozenset({"read_file", "apply_edit", "write_file"})


def result_message(call_id: str, result: ToolResult, tool_name: str) -> Message:
    """Render one `ToolResult` into the prompt message the model will see.

    **The single place a `ToolResult` becomes prompt content**, and therefore the single
    place the T7 `<untrusted-data>` envelope is applied. Centralizing it here rather than in
    `kernel/dispatch.py` keeps machine consumers of `dispatch` — `GateEvaluator` parses
    `git diff --numstat` through it — reading clean bytes, while still making it impossible
    for untrusted output to reach the model unlabelled: there is no other path from a
    `ToolResult` into a `ModelRequest`.

    `wrap_untrusted` is idempotent, so a result that somehow arrives pre-enveloped is not
    nested twice.
    """
    blocks: list[ContentBlock] = []
    for block in result.content:
        if not result.trusted and isinstance(block, TextBlock):
            blocks.append(
                block.model_copy(update={"text": wrap_untrusted(block.text, source=f"tool:{tool_name}")})
            )
        else:
            blocks.append(block)
    return Message(
        role="user",
        content=[ToolResultBlock(call_id=call_id, content=blocks, is_error=result.is_error)],
    )


class AnchoredState(BaseModel):
    """Structured state re-rendered every assembly; never entrusted to a summary."""

    model_config = ConfigDict(frozen=True)

    task: TaskSpec
    plan: tuple[str, ...] = ()
    open_files: tuple[str, ...] = ()
    unresolved_diagnostics: tuple[DiagnosticItem, ...] = ()


class AssembledPrompt(BaseModel):
    """One assembled request plus the two numbers that make prompt regressions visible."""

    model_config = ConfigDict(frozen=True)

    request: ModelRequest
    #: Hash of layers 1–7 (full prefix + canonical tool-schema order), per the PR-3.1 spec.
    prefix_digest: str
    #: Hash of layers 1–6 only — the region that is genuinely byte-identical across every
    #: step of a run, and therefore **the cache-stability regression signal** the e2e gate
    #: asserts on.
    #:
    #: The split is deliberate and worth stating, because the spec's one-line
    #: `prefix_digest  # layers 1–7 hash — the cache-stability regression signal` conflates
    #: two things that behave differently. Layer 7 (plan, open-file set, unresolved
    #: diagnostics) changes whenever the run touches a new file — by design; it is the state
    #: a long run carries across compaction. So a layers-1–7 hash could never be constant in
    #: any run that opens a second file, and asserting on it would just have produced a test
    #: that had to be deleted. Providers cache on longest-matching-prefix, so what actually
    #: has to hold is that **layers 1–6 never move**; a layer-7 change re-encodes only itself
    #: and the tail. `prefix_digest` moving while this holds is a deliberate layer-7 update.
    #: `stable_prefix_digest` moving is the regression.
    stable_prefix_digest: str
    #: Estimated tokens in the append-only tail (layer 8) — what compaction reclaims.
    tail_tokens: int
    #: Estimated tokens in layers 1–7.
    prefix_tokens: int
    #: Whether this assembly triggered a compaction pass.
    compacted: bool = False


class ContextAssembler:
    """Owns the history a run accumulates and renders it into a `ModelRequest`."""

    def __init__(
        self,
        *,
        system_prompt: str,
        tool_schemas: tuple[ToolSchema, ...] = (),
        task: TaskSpec,
        retrieval_seed: tuple[RetrievalHit, ...] = (),  # Layer 6: set once, frozen
        config: ContextConfig | None = None,
        compactor: ExchangeCompactor | None = None,
    ) -> None:
        self._system_prompt = system_prompt
        # Canonical alphabetical order. Non-deterministic ordering silently breaks the
        # cache prefix; it is part of the contract, not an implementation detail.
        self._tool_schemas: tuple[ToolSchema, ...] = tuple(sorted(tool_schemas, key=lambda s: s.name))
        self._task = task
        #: Layer 6. Private, frozen at construction, and never reassigned. There is no
        #: setter and no method below takes a `RetrievalHit` (ADR-0021).
        self._retrieval_seed: tuple[RetrievalHit, ...] = tuple(retrieval_seed)
        self._config = config or ContextConfig()
        self._compactor: ExchangeCompactor = compactor or TruncatingCompactor()

        #: The opening user turn. Held apart from `_exchanges` because it is not part of any
        #: assistant/tool_result pair and must never be compacted away — it is the task as
        #: the model first received it.
        self._head: Message = Message(role="user", content=[TextBlock(text=task.goal)])
        self._exchanges: list[Exchange] = []
        self._plan: tuple[str, ...] = ()
        self._open_files: list[str] = []
        self._diagnostics: tuple[DiagnosticItem, ...] = ()

    # --- Construction from a persisted run ----------------------------------

    @classmethod
    def from_trajectory(
        cls,
        *,
        system_prompt: str,
        tool_schemas: tuple[ToolSchema, ...] = (),
        task: TaskSpec,
        steps: list[TrajectoryStep],
        retrieval_seed: tuple[RetrievalHit, ...] = (),
        config: ContextConfig | None = None,
        compactor: ExchangeCompactor | None = None,
    ) -> ContextAssembler:
        """Rebuild an assembler from persisted steps — the resume path (absorbs D9).

        Read from `TrajectoryStore`, never from engine memory: an in-process list does not
        survive the restart that resume exists to recover from.
        """
        assembler = cls(
            system_prompt=system_prompt,
            tool_schemas=tool_schemas,
            task=task,
            retrieval_seed=retrieval_seed,
            config=config,
            compactor=compactor,
        )
        for step in steps:
            assembler._append_persisted_step(step)
        return assembler

    def _append_persisted_step(self, step: TrajectoryStep) -> None:
        # RC-4: a step with a persisted `message` and no tool calls is a text-only assistant
        # turn. The previous `_reconstruct_history` skipped every step whose `tool_calls`
        # was empty, which silently dropped those turns — so a resumed run's request digest
        # could never match the recorded one, and replay of a resumed run was impossible.
        if step.message is None and not step.tool_calls:
            return

        if step.message is not None:
            assistant = step.message
        else:
            # Legacy step recorded before `TrajectoryStep.message` existed (S2.5).
            # Whatever text or reasoning accompanied these calls was never stored; this
            # reconstructs only what is recoverable.
            assistant = Message(
                role="assistant",
                content=[
                    ToolUseBlock(call_id=c.call_id, tool_name=c.tool_name, arguments=c.arguments)
                    for c in step.tool_calls
                ],
            )

        results: list[Message] = []
        tainted = False
        for call, result in zip(step.tool_calls, step.tool_results, strict=False):
            if not result.trusted:
                tainted = True
            # Resume must take the same ToolResult → prompt path as the live loop, or a
            # thawed run would show the model unlabelled untrusted bytes (T7 hole).
            results.append(result_message(call.call_id, result, call.tool_name))
        self._record_open_files(assistant)
        self._exchanges.append(Exchange.build(assistant, tuple(results), tainted=tainted))

    # --- Tail growth --------------------------------------------------------

    def append_exchange(
        self,
        assistant: Message,
        results: tuple[Message, ...] = (),
        *,
        tainted: bool = False,
    ) -> None:
        """Append one assistant turn and its paired tool results as an indivisible unit."""
        self._record_open_files(assistant)
        self._exchanges.append(Exchange.build(assistant, results, tainted=tainted))

    def append_repair_turn(self, text: str) -> None:
        """Append harness-authored gate-failure feedback (v2-S7f `RepairConfig`) as a
        user-role message following the last exchange, so the next model call sees its own
        prior turn plus the failure — no second system prompt, prefix cache intact (AD-2).

        `trusted=True` by construction (`domain/events.py` docstring on the caller side
        explains why: the text is derived from this run's own test output, not external
        content) — never wrapped in `<untrusted-data>`, never marks the run tainted.
        """
        if not self._exchanges:
            raise ValueError("append_repair_turn requires at least one prior exchange")
        last = self._exchanges[-1]
        repair_message = Message(role="user", content=[TextBlock(text=text)])
        self._exchanges[-1] = Exchange.build(
            last.assistant,
            (*last.results, repair_message),
            tainted=last.tainted,
            is_summary=last.is_summary,
        )

    def _record_open_files(self, assistant: Message) -> None:
        for block in assistant.content:
            if not isinstance(block, ToolUseBlock) or block.tool_name not in _OPEN_FILE_TOOLS:
                continue
            for key in _PATH_ARGS:
                raw = block.arguments.get(key)
                if isinstance(raw, str) and raw and raw not in self._open_files:
                    self._open_files.append(raw)

    # --- Anchored state -----------------------------------------------------

    def set_plan(self, plan: tuple[str, ...]) -> None:
        self._plan = tuple(plan)

    def seed_open_files(self, paths: tuple[str, ...]) -> None:
        """Seed the open-file set on thaw without wiping paths already derived from the transcript."""
        for path in paths:
            if path and path not in self._open_files:
                self._open_files.append(path)

    def set_diagnostics(self, diagnostics: tuple[DiagnosticItem, ...]) -> None:
        """Replace the unresolved-diagnostic set. Resolved ones are dropped by the caller;
        carrying a resolved diagnostic forward is how a run ends up chasing a fixed bug."""
        self._diagnostics = tuple(diagnostics)

    def anchored(self) -> AnchoredState:
        return AnchoredState(
            task=self._task,
            plan=self._plan,
            open_files=tuple(self._open_files),
            unresolved_diagnostics=self._diagnostics,
        )

    # --- Introspection (used by tests and by the compaction trigger) ---------

    @property
    def exchanges(self) -> tuple[Exchange, ...]:
        return tuple(self._exchanges)

    def tail_tokens(self) -> int:
        return message_tokens(self._head) + sum(ex.tokens for ex in self._exchanges)

    def is_tainted(self) -> bool:
        """True when any exchange in the transcript is tainted.

        Advisory only, and deliberately so: this is the *assembler's* view, used to decide
        envelope rendering. The authoritative taint state is `DefaultPolicyEngine`'s, which
        is Control-internal and is what actually refuses a mutation (T7).
        """
        return any(ex.tainted for ex in self._exchanges)

    # --- Assembly -----------------------------------------------------------

    def _render_layers_1_to_6(self) -> str:
        """The byte-identical cached region: role, tool schemas, safety framing, conventions,
        task spec, retrieval seed.

        Nothing here changes after construction. Sections are emitted only when non-empty,
        which is what keeps a run with no retrieval seed byte-identical to the pre-assembler
        prompt — PR-3.1 is an extraction, not a prompt change, and a prompt change would owe
        an ablation this sprint does not run.
        """
        parts: list[str] = [self._system_prompt]  # layers 1 + 3 + 4, caller-supplied

        # Layer 5 — acceptance criteria. Anchored: re-rendered every assembly so that what
        # the run is graded on survives any number of compactions of the transcript.
        if self._task.acceptance:
            criteria = "\n".join(
                f"- {c.description} (check: `{c.check}`)"
                + ("" if c.required else " [ranks only, does not admit]")
                for c in self._task.acceptance
            )
            parts.append(f"## Acceptance criteria\nYou will be graded on exactly these:\n{criteria}")

        # Layer 6 — retrieval seed. Computed once at task start; never refreshed (ADR-0021).
        if self._retrieval_seed:
            chunks = "\n\n".join(f"### {hit.path}\n{hit.chunk}" for hit in self._retrieval_seed)
            parts.append(f"## Retrieved repository context\n{chunks}")

        return "\n\n".join(parts)

    def _render_layer_7(self) -> str:
        """Active plan state, open-file set, unresolved diagnostics.

        Genuinely mutable, and that is the point — this is the state a long run carries
        across compaction boundaries. It sits at the *bottom* of the prefix so that a change
        here re-encodes only itself and the tail, leaving layers 1–6 cached.
        """
        anchored: list[str] = []
        if self._plan:
            anchored.append("### Plan\n" + "\n".join(f"{i}. {s}" for i, s in enumerate(self._plan, 1)))
        if self._open_files:
            anchored.append("### Open files\n" + "\n".join(f"- {p}" for p in self._open_files))
        if self._diagnostics:
            anchored.append(
                "### Unresolved diagnostics\n"
                + "\n".join(f"- {d.path}:{d.line} [{d.severity}] {d.message}" for d in self._diagnostics)
            )
        return "## Current state\n" + "\n\n".join(anchored) if anchored else ""

    def _schema_fingerprint(self) -> str:
        return "\x00".join(
            f"{s.name}:{s.description}:{sorted(s.parameters.items())!r}" for s in self._tool_schemas
        )

    @staticmethod
    def _digest(payload: str) -> str:
        return hashlib.sha256(payload.encode()).hexdigest()

    async def assemble(self, role: str = "execution") -> AssembledPrompt:
        """Render the current state into a `ModelRequest`, compacting first if needed.

        The compaction check runs **pre-assembly, once per step** — never mid-turn, and never
        on a per-turn schedule. Compaction resets the cache exactly once in exchange for
        reclaiming the window; done continuously it pays that cost every turn and saves
        nothing.
        """
        stable = self._render_layers_1_to_6()
        prefix = "\n\n".join(p for p in (stable, self._render_layer_7()) if p)
        prefix_tokens = estimate_tokens(prefix) + sum(
            estimate_tokens(f"{s.name}{s.description}{s.parameters}") for s in self._tool_schemas
        )

        compacted = False
        budget = max(0, self._config.max_context_tokens - prefix_tokens)
        threshold = int(budget * (1.0 - self._config.compact_at_headroom))
        if self.tail_tokens() > threshold:
            before = tuple(self._exchanges)
            after = await self._compactor.compact(
                before,
                keep_first=self._config.keep_first_exchanges,
                keep_last_tokens=self._config.keep_last_tokens,
            )
            if after != before:
                self._exchanges = list(after)
                compacted = True

        messages: list[Message] = [self._head]
        for ex in self._exchanges:
            messages.extend(ex.messages())

        schemas = self._schema_fingerprint()
        return AssembledPrompt(
            request=ModelRequest(
                system=prefix,
                messages=messages,
                tools=list(self._tool_schemas),
                role=role,
            ),
            prefix_digest=self._digest(prefix + "\x00" + schemas),
            stable_prefix_digest=self._digest(stable + "\x00" + schemas),
            tail_tokens=self.tail_tokens(),
            prefix_tokens=prefix_tokens,
            compacted=compacted,
        )
