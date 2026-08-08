"""ModelNode — unified step execution for LLM-driven nodes (T5, `TASK-057`).

Replaces architect, generate, repair, and reflector steps with a single node
class configured by a `RoleSpec` and capability instances bound at composition.

No subclasses. `node_kind`, `input_type`, and `output_type` are instance
attributes on `ModelNode` to satisfy `NODE_SOCKETS` validation without class
duplication.
"""

from __future__ import annotations

from typing import Any

from aether.agency.capabilities.inference import get_inference
from aether.agency.capabilities.parsers import get_parser
from aether.agency.capabilities.sources import get_source
from aether.agency.context.assembler import LayeredAssembler
from aether.agency.dispatch import EffectDispatch
from aether.agency.roles import RoleSpec
from aether.domain.ids import Frozen
from aether.domain.tools import ToolSpec
from aether.workflow.step import StepContext, WorkflowStep


class ModelNode(WorkflowStep[Any, Any]):
    """Any node whose work is: gather context, assemble prompt, call model,
    parse reply. Architect, generate, repair and reflector are all this node
    with different capabilities bound at composition.

    No subclasses, ever.
    """

    def __init__(
        self,
        dispatch: EffectDispatch,
        *,
        node_kind: str,
        input_type: type[Frozen],
        output_type: type[Frozen],
        spec: RoleSpec,
        model_name: str,
        max_tokens: int,
        tool_catalog: tuple[ToolSpec, ...] = (),
    ) -> None:
        self.node_kind = node_kind
        self.input_type = input_type
        self.output_type = output_type
        self._dispatch = dispatch
        self._spec = spec
        self._model_name = model_name
        self._max_tokens = max_tokens
        self._tool_catalog = tool_catalog
        self._assembler = LayeredAssembler()

    async def run(self, ctx: StepContext, payload: Any) -> Any:
        req = self._spec.request_from(payload)

        # 1. Gather blocks from capabilities
        blocks_list = []
        for src_name in self._spec.sources:
            src = get_source(src_name)
            gathered = await src.gather(self._dispatch, req)
            blocks_list.extend(gathered)
        blocks = tuple(blocks_list)

        # 2. Get parser & inference
        parser = get_parser(self._spec.parser)
        inference = get_inference(self._spec.inference)

        # 3. Assemble prompt request
        request = self._assembler.assemble(
            role=self._spec.role_text,
            blocks=blocks,
            contract=parser.instructions(),
            model=self._model_name,
            max_tokens=self._max_tokens,
            tools=self._tool_catalog if self._spec.wants_tools else (),
            node_id=str(ctx.node_id),
        )

        # 4. Invoke inference
        spans = tuple(span for msg in request.messages for span in msg.spans)
        result = await inference.invoke(
            self._dispatch,
            request,
            worktree=req.worktree,
            justifying=spans,
        )

        # 5. Parse output and fold into payload
        known_files = (
            tuple(f.repo_rel_path for f in payload.files)
            if hasattr(payload, "files")
            else getattr(payload, "retrieved_files", ())
        )
        test_paths = getattr(payload.task, "test_paths", ()) if hasattr(payload, "task") else ()
        parsed = parser.parse(result.text, known_files=known_files, test_paths=test_paths)
        return parsed.into(payload, result, output_type=self.output_type)


__all__ = ["ModelNode"]
