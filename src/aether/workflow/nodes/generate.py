"""GenerateStep — builds a `ModelRequest` from retrieved context +
`ToolRegistry.catalog()`, streams from `ModelProvider`; on a `ToolCallDelta`,
dispatches to `ToolRegistry.execute()` and feeds the `ToolResult` back as a
new message, bounded to a small fixed round-trip cap. Terminates on
`StopEvent`. Exercises `ToolRegistry` as one of the four M1a boundaries."""

from __future__ import annotations

from datetime import UTC, datetime

from aether.composition import ShellArgs
from aether.domain.budget import BudgetDims
from aether.domain.ids import Frozen, SpanId
from aether.domain.model_io import ModelMessage, ModelRequest, TextDelta, ToolCallDelta
from aether.domain.taint import Provenance, TaintSpan
from aether.domain.task import Task
from aether.domain.tools import ToolCall, ToolSpec
from aether.domain.workspace import WorktreeRef
from aether.workflow.dispatch_facade import DispatchFacade
from aether.workflow.nodes.retrieve import RetrievedContext
from aether.workflow.step import StepContext, WorkflowStep


class GeneratedPatch(Frozen):
    task: Task
    worktree: WorktreeRef
    patch_text: str
    iteration: int = 0  # 0 = first attempt; >0 = produced by the repair edge


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
    ) -> None:
        self._dispatch = dispatch
        self._model_name = model_name
        self._tool_catalog = tool_catalog
        self._max_tokens = max_tokens

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
        if payload.file_slice is not None:
            spans.append(
                TaintSpan(
                    span_id=SpanId(f"{node_id}-file"),
                    label=Provenance.AGENT,
                    text=payload.file_slice.text,
                    source=f"file:{payload.file_slice.repo_rel_path}",
                    created_at=datetime.now(UTC),
                )
            )
        return tuple(spans)

    async def run(self, ctx: StepContext, payload: RetrievedContext) -> GeneratedPatch:
        spans = self._build_spans(payload, str(ctx.node_id))
        messages: list[ModelMessage] = [ModelMessage(role="user", spans=spans)]
        patch_text_parts: list[str] = []

        for _round in range(self.MAX_ROUNDS):
            request = ModelRequest(
                model=self._model_name,
                messages=tuple(messages),
                tools=self._tool_catalog,
                max_tokens=self._max_tokens,
            )
            events = await self._dispatch.model(request, BudgetDims(prompt_tokens=self._max_tokens))

            tool_calls: dict[str, dict[str, str]] = {}
            stop_reason = "end"
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

            for call_id, info in tool_calls.items():
                tool_call = ToolCall(
                    call_id=call_id,
                    name=info["name"],
                    args_json=info["args"] or "{}",
                    justifying_spans=tuple(s.span_id for s in spans),
                )
                result = await self._dispatch.shell(
                    ShellArgs(worktree=payload.worktree, call=tool_call),
                    BudgetDims(wall_clock_ms=30000),
                    justifying_spans=spans,
                )
                messages.append(ModelMessage(role="tool", spans=result.spans))

        raw_patch = "".join(patch_text_parts)
        cleaned_lines: list[str] = []
        in_diff = False
        for line in raw_patch.splitlines():
            if line.startswith("```"):
                continue
            if line.startswith(("diff --git", "--- ", "+++ ", "@@ ")):
                in_diff = True
            if in_diff:
                cleaned_lines.append(line)

        final_patch = "\n".join(cleaned_lines) if cleaned_lines else raw_patch

        return GeneratedPatch(
            task=payload.task, worktree=payload.worktree, patch_text=final_patch
        )

