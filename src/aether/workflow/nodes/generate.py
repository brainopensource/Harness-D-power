"""GenerateStep — turns retrieved context into a candidate edit.

Two Sprint 3.5 changes, both aimed at the same failure: locally, models were
producing confident output about files they had never been shown, in a format
nobody had told them to use.

* **A system layer.** One frozen `system` message states the role and the
  output contract. `ModelMessage` had supported `role="system"` since Sprint 1
  and nothing emitted one — the whole prompt was a single bare user turn. This
  is the seed of ADR-0010's L1, not a replacement for the five-layer assembler
  (TASK-031), and it is deliberately short: every token here is paid on every
  call of every task.
* **The edit format is injected**, not hard-coded. The output contract in the
  prompt and the parser that reads the reply come from the same `EditFormat`
  object, so they cannot disagree.

Tool use is off unless a node asks for it (`params.tools: true`): the built-in
registry still executes uncontained on the host, and a task that does not need
a shell should not be offered one.
"""

from __future__ import annotations

from datetime import UTC, datetime

from aether.domain.budget import BudgetDims
from aether.domain.effects import ShellArgs
from aether.domain.ids import Frozen, SpanId
from aether.domain.model_io import (
    ModelMessage,
    ModelRequest,
    StopReason,
    TextDelta,
    ToolCallDelta,
    ToolCallRef,
)
from aether.domain.taint import Provenance, TaintSpan
from aether.domain.task import Task
from aether.domain.tools import ToolCall, ToolSpec
from aether.domain.workspace import WorktreeRef
from aether.workflow.dispatch_facade import DispatchFacade
from aether.workflow.edit_format import DEFAULT_EDIT_FORMAT, get_edit_format
from aether.workflow.nodes.retrieve import RetrievedContext
from aether.workflow.step import StepContext, WorkflowStep

#: The L1 seed. Short on purpose — it is paid on every call.
SYSTEM_ROLE = (
    "You are a precise software engineer fixing a bug in an existing repository. "
    "You are shown the relevant files. Change as little as possible."
)


def build_system_text(edit_instructions: str) -> str:
    return f"{SYSTEM_ROLE}\n\n{edit_instructions}"


class GeneratedPatch(Frozen):
    task: Task
    worktree: WorktreeRef
    #: The model's reply, unparsed. Kept raw so the repair edge can show the
    #: model what it actually said, and so a parse failure is diagnosable.
    raw_output: str = ""
    edit_format: str = DEFAULT_EDIT_FORMAT
    iteration: int = 0  # 0 = first attempt; >0 = produced by the repair edge
    #: Why the completion ended. Carried because `provider_error` is *our*
    #: failure, not the task's: without it a 429, a socket reset or a read
    #: timeout arrives here as an empty `raw_output`, which `ApplyStep` reads as
    #: "the model produced no edit" and the gate then scores `FAILED` on an
    #: unmodified worktree. B4 was built for the evaluator and not for the
    #: provider, and the asymmetry was invisible because both paths end in a
    #: `GateReport`. Consumed by `ApplyStep` -> `EvaluateStep`.
    stop_reason: StopReason = "end"

    @property
    def patch_text(self) -> str:
        """Sprint 2's name for the model's output. Retained for callers and
        tests written against it."""
        return self.raw_output


class GenerateStep(WorkflowStep[RetrievedContext, GeneratedPatch]):
    node_kind = "generate"
    input_type = RetrievedContext
    output_type = GeneratedPatch

    MAX_ROUNDS = 4

    def __init__(
        self,
        dispatch: DispatchFacade,
        model_name: str,
        tool_catalog: tuple[ToolSpec, ...] = (),
        max_tokens: int = 4096,
        edit_format: str = DEFAULT_EDIT_FORMAT,
    ) -> None:
        self._dispatch = dispatch
        self._model_name = model_name
        self._tool_catalog = tool_catalog
        self._max_tokens = max_tokens
        self._edit_format = get_edit_format(edit_format)

    def _build_spans(self, payload: RetrievedContext, node_id: str) -> tuple[TaintSpan, ...]:
        spans = [
            TaintSpan(
                span_id=SpanId(f"{node_id}-instructions"),
                label=Provenance.OPERATOR,
                text=payload.instructions,
                source="task.instructions",
                created_at=datetime.now(UTC),
            )
        ]
        for index, file_slice in enumerate(payload.files):
            spans.append(
                TaintSpan(
                    span_id=SpanId(f"{node_id}-file-{index}"),
                    # Repository content is not operator-authored. Labelling it
                    # otherwise would launder its provenance (ADR-0015).
                    label=Provenance.AGENT,
                    text=f"=== {file_slice.repo_rel_path} ===\n{file_slice.text}",
                    source=f"file:{file_slice.repo_rel_path}",
                    created_at=datetime.now(UTC),
                )
            )
        return tuple(spans)

    def _system_message(self, node_id: str) -> ModelMessage:
        return ModelMessage(
            role="system",
            spans=(
                TaintSpan(
                    span_id=SpanId(f"{node_id}-system"),
                    label=Provenance.TRUSTED_SYSTEM,
                    text=build_system_text(self._edit_format.instructions()),
                    source="harness.system_layer",
                    created_at=datetime.now(UTC),
                ),
            ),
        )

    async def run(self, ctx: StepContext, payload: RetrievedContext) -> GeneratedPatch:
        spans = self._build_spans(payload, str(ctx.node_id))
        messages: list[ModelMessage] = [
            self._system_message(str(ctx.node_id)),
            ModelMessage(role="user", spans=spans),
        ]
        patch_text_parts: list[str] = []
        stop_reason: StopReason = "end"
        # What actually justifies the *next* request, which is not the same set
        # as what justified the first. Tool output is `UNTRUSTED_EXTERNAL` at
        # birth and is fed back to the model, so from round 2 on it can steer a
        # tool call. Passing only the round-0 spans meant `DefaultPolicyEngine`
        # evaluated `any(span.label in UNTRUSTED ...)` over a set that could not
        # contain an untrusted span by construction, which made I11's predicate
        # dead code on the one path it exists for (spec.md §5, ADR-0015).
        justifying: tuple[TaintSpan, ...] = spans

        for _round in range(self.MAX_ROUNDS):
            request = ModelRequest(
                model=self._model_name,
                messages=tuple(messages),
                tools=self._tool_catalog,
                max_tokens=self._max_tokens,
            )
            events = await self._dispatch.model(request, BudgetDims(prompt_tokens=self._max_tokens))

            tool_calls: dict[str, dict[str, str]] = {}
            for event in events:
                if isinstance(event, TextDelta):
                    patch_text_parts.append(event.text)
                elif isinstance(event, ToolCallDelta):
                    call = tool_calls.setdefault(event.call_id, {"name": "", "args": ""})
                    if event.name:
                        call["name"] = event.name
                    call["args"] += event.args_json_fragment
                elif event.kind == "stop":
                    stop_reason = event.reason

            if not tool_calls or stop_reason != "tool_use":
                break

            # The assistant's own tool_calls message comes first, then one
            # `tool` message per call naming the `tool_call_id` it answers.
            # Sprint 2 appended only the results, which every OpenAI-compatible
            # endpoint rejects — the path had only ever run against mocks that
            # returned no tool calls, so nothing caught it.
            messages.append(
                ModelMessage(
                    role="assistant",
                    spans=(),
                    tool_calls=tuple(
                        ToolCallRef(call_id=call_id, name=info["name"], args_json=info["args"] or "{}")
                        for call_id, info in tool_calls.items()
                    ),
                )
            )

            for call_id, info in tool_calls.items():
                tool_call = ToolCall(
                    call_id=call_id,
                    name=info["name"],
                    args_json=info["args"] or "{}",
                    justifying_spans=tuple(s.span_id for s in justifying),
                )
                result = await self._dispatch.shell(
                    ShellArgs(worktree=payload.worktree, call=tool_call),
                    BudgetDims(wall_clock_ms=30000),
                    justifying_spans=justifying,
                )
                messages.append(ModelMessage(role="tool", spans=result.spans, tool_call_id=call_id))
                # Now in the model's context, therefore justifying whatever it
                # asks for next. Monotone: a span never loses its label here.
                justifying = (*justifying, *result.spans)

        # Parsing belongs to the format, not to this node: the prompt that
        # asked for a shape and the parser that reads it are the same object.
        return GeneratedPatch(
            task=payload.task,
            worktree=payload.worktree,
            raw_output="".join(patch_text_parts),
            edit_format=self._edit_format.name,
            stop_reason=stop_reason,
        )
