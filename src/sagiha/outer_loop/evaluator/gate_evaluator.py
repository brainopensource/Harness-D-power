"""GateEvaluator — the Evaluator port's only implementation (R4).

Moved out of `agency/run_loop.py`, which is not TCB-guarded, into this package, which
`tcb-isolation` in `.importlinter` protects: an agent editing its own grader would have to land
that change somewhere `agency` and `adapters` cannot be imported from.
"""

from __future__ import annotations

import json
import re
import uuid

from sagiha.domain.content import TextBlock, ToolCall
from sagiha.domain.control import RunContext
from sagiha.domain.work import CriterionResult, GateReport, TaskSpec
from sagiha.kernel.bus import EventBus
from sagiha.kernel.dispatch import dispatch
from sagiha.kernel.policy.effects import classify_command
from sagiha.ports.governor import ResourceGovernor
from sagiha.ports.policy import PolicyEngine
from sagiha.ports.tool_registry import ToolRegistry

#: Markers that silence a checker rather than satisfy it. Adding one is how a diff
#: passes a gate without doing the work, so a run that introduces one does not admit.
_SUPPRESSION = re.compile(r"#\s*type:\s*ignore|#\s*noqa|#\s*pragma:\s*no cover|pytest\.mark\.skip")


class GateEvaluator:
    """Runs each `AcceptanceCriterion.check` through `run_command` and grades the coding profile.

    Every gate is one of three things, and never anything else:

    * `True`  — the check ran and passed.
    * `False` — the check ran and failed.
    * `None`  — the check **could not be run** (no base ref, git unavailable, or no
      adapter exists yet). `None` is never a pass; `GateReport.admitted` requires an
      explicit `True` for every gate in `required_gates`, so an unevaluable required
      gate fails closed (D20).

    Before PR-1a, `tests_unmodified`, `no_new_suppressions`, `coverage_not_decreased`,
    and `diff_within_bounds` were hardcoded `True` (H1). Three are now real `git diff`
    checks; `coverage_not_decreased` reports an honest `None` until a `Toolchain`
    adapter and a baseline exist.
    """

    def __init__(
        self,
        policy_engine: PolicyEngine,
        resource_governor: ResourceGovernor,
        tool_registry: ToolRegistry,
        bus: EventBus,
        *,
        test_paths: tuple[str, ...] = ("tests/",),
        max_diff_lines: int = 1000,
        require_coverage_not_decreased: bool = False,
    ) -> None:
        self._policy = policy_engine
        self._governor = resource_governor
        self._registry = tool_registry
        self._bus = bus
        self._test_paths = test_paths
        self._max_diff_lines = max_diff_lines
        self._require_coverage = require_coverage_not_decreased

    async def _run(self, argv: list[str], ctx: RunContext) -> tuple[bool, str]:
        """Run a command through the same dispatch choke point the criteria use.

        Deliberately not `subprocess` directly: routing through `dispatch` means the
        gates create no new authority path — they are authorized, audited, and recorded
        exactly like any other effect.
        """
        call = ToolCall(
            call_id=str(uuid.uuid4()),
            tool_name="run_command",
            arguments={"command": argv},
            effect=classify_command(argv, await self._registry.get_effect_class("run_command")),
        )
        result = await dispatch(
            call=call,
            ctx=ctx,
            policy=self._policy,
            governor=self._governor,
            registry=self._registry,
            bus=self._bus,
        )
        # `run_command` returns a CommandResult serialized as JSON, not raw stdout —
        # the gates need the stdout field, not the envelope.
        if not result.content or not isinstance(result.content[0], TextBlock):
            return False, ""
        try:
            payload = json.loads(result.content[0].text)
        except json.JSONDecodeError:
            return False, ""
        return payload.get("exit_code") == 0, str(payload.get("stdout", ""))

    async def _stage_intent_to_add(self, ctx: RunContext) -> bool:
        """Make untracked files visible to `git diff` before any gate reads it.

        Without this, `git diff <base>` reports only tracked changes — so an agent that
        *creates* `tests/test_fake.py`, or writes 5,000 new lines across new files,
        passes `tests_unmodified` and `diff_within_bounds` untouched. `--intent-to-add`
        records the paths in the index without staging content, which is the standard
        idiom for exactly this and is what makes all three gates see created files.
        """
        ok, _ = await self._run(["git", "add", "--intent-to-add", "-A"], ctx)
        return ok

    async def _tests_unmodified(self, base: str, ctx: RunContext) -> bool | None:
        """Passes iff no file under a test path differs from the base ref.

        This is the gate the T3 evaluation-capture threat model rests on, and the one
        `Config` refuses to let you disable. It was a literal `True` until PR-1a (H1).
        """
        ok, out = await self._run(["git", "diff", "--name-only", base, "--", *self._test_paths], ctx)
        if not ok:
            return None  # cannot evaluate — never report a pass
        return out.strip() == ""

    async def _diff_within_bounds(self, base: str, ctx: RunContext) -> bool | None:
        ok, out = await self._run(["git", "diff", "--numstat", base], ctx)
        if not ok:
            return None
        total = 0
        for line in out.splitlines():
            fields = line.split("\t")
            if len(fields) < 2:
                continue
            for count in fields[:2]:
                # "-" marks a binary file: no line counts to add.
                if count.isdigit():
                    total += int(count)
        return total <= self._max_diff_lines

    async def _no_new_suppressions(self, base: str, ctx: RunContext) -> bool | None:
        """Scans ADDED lines only — a suppression already in the base is not this run's."""
        ok, out = await self._run(["git", "diff", base, "-U0"], ctx)
        if not ok:
            return None
        for line in out.splitlines():
            # `+++ b/path` is a file header, not content.
            if not line.startswith("+") or line.startswith("+++"):
                continue
            if _SUPPRESSION.search(line):
                return False
        return True

    async def evaluate(self, task: TaskSpec, ctx: RunContext) -> GateReport:
        criteria: list[CriterionResult] = []
        for criterion in task.acceptance:
            call = ToolCall(
                call_id=str(uuid.uuid4()),
                tool_name="run_command",
                arguments={"command": ["bash", "-lc", criterion.check]},
                effect=await self._registry.get_effect_class("run_command"),
            )
            result = await dispatch(
                call=call,
                ctx=ctx,
                policy=self._policy,
                governor=self._governor,
                registry=self._registry,
                bus=self._bus,
            )
            passed = not result.is_error
            output = ""
            if result.content and isinstance(result.content[0], TextBlock):
                output = result.content[0].text
            criteria.append(
                CriterionResult(
                    description=criterion.description,
                    check=criterion.check,
                    passed=passed,
                    required=criterion.required,
                    output=output,
                )
            )

        # Coding profile gates, evaluated against the run's base commit.
        #
        # `base_commit` absent means the gates cannot be computed at all. They report
        # None, and because None is never a pass, the run fails closed — which is the
        # only safe reading of "I could not check".
        base = ctx.base_commit
        if base is None or not await self._stage_intent_to_add(ctx):
            tests_unmodified = diff_within_bounds = no_new_suppressions = None
        else:
            tests_unmodified = await self._tests_unmodified(base, ctx)
            diff_within_bounds = await self._diff_within_bounds(base, ctx)
            no_new_suppressions = await self._no_new_suppressions(base, ctx)

        required = {"no_new_suppressions", "tests_unmodified", "diff_within_bounds"}
        if self._require_coverage:
            required.add("coverage_not_decreased")

        return GateReport(
            criteria=tuple(criteria),
            no_new_suppressions=no_new_suppressions,
            tests_unmodified=tests_unmodified,
            # The one gate that legitimately cannot be honest yet: no Toolchain adapter,
            # no baseline to compare against. `None` is the true answer; fabricating
            # `True` here is precisely the H1 defect this PR removes.
            coverage_not_decreased=None,
            diff_within_bounds=diff_within_bounds,
            required_gates=frozenset(required),
        )
