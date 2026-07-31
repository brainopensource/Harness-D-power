"""Shared test fixtures and helpers.

`build_test_evaluator` exists because of RC-8: `RunLoop.evaluator` is a **required**
argument. `agency` used to default-construct a `GateEvaluator` when none was passed, which
meant the layer under judgement also chose its own judge, and a TCB object got built outside
the composition root where the `tcb-isolation` contract cannot see it. Tests that build a
`RunLoop` by hand (rather than from `build_kernel`) now pass an evaluator explicitly, exactly
as the composition root does — this helper is the one place that assembly lives, so it does
not get copy-pasted into a dozen test modules.

`config_for_test` defaults `sandbox.runtime='subprocess'` so the unit suite stays
Podman-free. Production schema default remains `container` (ADR-0016).
"""

from __future__ import annotations

from typing import Any

from sagiha.domain.config import Config, SandboxConfig
from sagiha.kernel.bus import EventBus
from sagiha.outer_loop.evaluator import GateEvaluator
from sagiha.ports.governor import ResourceGovernor
from sagiha.ports.policy import PolicyEngine
from sagiha.ports.tool_registry import ToolRegistry


def build_test_evaluator(
    policy_engine: PolicyEngine,
    resource_governor: ResourceGovernor,
    tool_registry: ToolRegistry,
    bus: EventBus | None = None,
) -> GateEvaluator:
    """The same `GateEvaluator` wiring `composition.build_kernel` performs, for hand-built loops."""
    return GateEvaluator(policy_engine, resource_governor, tool_registry, bus or EventBus())


def config_for_test(**kwargs: Any) -> Config:
    """Build a `Config` for tests, defaulting to subprocess sandbox (no Podman required)."""
    if "sandbox" not in kwargs:
        kwargs["sandbox"] = SandboxConfig(runtime="subprocess")
    return Config(**kwargs)
