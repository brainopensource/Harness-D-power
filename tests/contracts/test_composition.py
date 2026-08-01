"""Tests for composition root and configuration validation.

See docs/05-tech-stack/composition-and-configuration.md.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sagiha import Config, Kernel, build_kernel
from sagiha.domain.config import (
    AutonomyConfig,
    GatesConfig,
    ModelConfig,
    ModelTierConfig,
    RetrievalConfig,
    SandboxConfig,
    SearchConfig,
    TelemetryConfig,
    WorkspaceConfig,
)


def test_build_kernel_default_config(tmp_path: Path) -> None:
    cassette = tmp_path / "c.json"
    cassette.write_text("[]", encoding="utf-8")
    config = Config(
        model=ModelConfig(mode="replay"),
        telemetry=TelemetryConfig(trajectory_db=str(tmp_path / "t.db")),
        workspace=WorkspaceConfig(root=str(tmp_path)),
        sandbox=SandboxConfig(runtime="subprocess"),
    )
    kernel = build_kernel(config, cassette_path=str(cassette))
    assert isinstance(kernel, Kernel)
    assert kernel.config == config


def test_refuse_subprocess_in_autonomous_mode() -> None:
    with pytest.raises(ValueError, match="sandbox.runtime='subprocess' is refused"):
        Config(
            sandbox=SandboxConfig(runtime="subprocess"),
            autonomy=AutonomyConfig(level="autonomous"),
        )


def test_refuse_host_network_without_allow_unsafe() -> None:
    with pytest.raises(ValueError, match="sandbox.network='host' is refused"):
        Config(
            sandbox=SandboxConfig(network="host", allow_unsafe=False),
        )


def test_refuse_host_network_outside_interactive() -> None:
    with pytest.raises(ValueError, match="autonomy.level='interactive'"):
        Config(
            sandbox=SandboxConfig(network="host", allow_unsafe=True),
            autonomy=AutonomyConfig(level="autonomous"),
        )


def test_autonomous_requires_container_runtime() -> None:
    # Default runtime is container — autonomous is legal.
    cfg = Config(autonomy=AutonomyConfig(level="autonomous"))
    assert cfg.sandbox.runtime == "container"
    assert cfg.autonomy.level == "autonomous"


def test_refuse_disabling_require_tests_unmodified() -> None:
    with pytest.raises(ValueError, match="gates.require_tests_unmodified=False is refused"):
        Config(
            gates=GatesConfig(require_tests_unmodified=False),
            sandbox=SandboxConfig(runtime="subprocess"),
        )


def test_refuse_undefined_model_tier_in_roles() -> None:
    with pytest.raises(ValueError, match="references undefined tier"):
        Config(
            model=ModelConfig(
                roles={"planning": "non_existent_tier"},
            ),
            sandbox=SandboxConfig(runtime="subprocess"),
        )


def test_refuse_search_enabled_when_judge_and_execution_share_a_model() -> None:
    with pytest.raises(ValueError, match="judge-separation|search.enabled=True is refused"):
        Config(
            model=ModelConfig(
                tiers={"same": ModelTierConfig(provider="anthropic", model="shared-model")},
                roles={"judge": "same", "execution": "same"},
            ),
            search=SearchConfig(enabled=True),
            sandbox=SandboxConfig(runtime="subprocess"),
        )


def test_search_enabled_allowed_when_judge_and_execution_differ() -> None:
    config = Config(
        model=ModelConfig(
            tiers={
                "judge_tier": ModelTierConfig(provider="anthropic", model="judge-model"),
                "exec_tier": ModelTierConfig(provider="anthropic", model="exec-model"),
            },
            roles={"judge": "judge_tier", "execution": "exec_tier"},
        ),
        search=SearchConfig(enabled=True),
        sandbox=SandboxConfig(runtime="subprocess"),
    )
    assert config.search.enabled


def test_build_kernel_retrieval_disabled_keeps_six_tools(tmp_path: Path) -> None:
    cassette = tmp_path / "c.json"
    cassette.write_text("[]", encoding="utf-8")
    config = Config(
        model=ModelConfig(mode="replay"),
        telemetry=TelemetryConfig(trajectory_db=str(tmp_path / "t.db")),
        workspace=WorkspaceConfig(root=str(tmp_path)),
        sandbox=SandboxConfig(runtime="subprocess"),
        retrieval=RetrievalConfig(enabled=False),
    )
    kernel = build_kernel(config, cassette_path=str(cassette))
    assert kernel.indexer is None
    assert kernel.code_graph is None
    assert len(kernel.tool_schemas) == 6
    assert "find_symbols" not in {s.name for s in kernel.tool_schemas}


def test_build_kernel_retrieval_enabled_wires_indexer_and_tools(tmp_path: Path) -> None:
    cassette = tmp_path / "c.json"
    cassette.write_text("[]", encoding="utf-8")
    (tmp_path / "demo.py").write_text("def hello():\n    pass\n", encoding="utf-8")
    config = Config(
        model=ModelConfig(mode="replay"),
        telemetry=TelemetryConfig(trajectory_db=str(tmp_path / "t.db")),
        workspace=WorkspaceConfig(root=str(tmp_path)),
        sandbox=SandboxConfig(runtime="subprocess"),
        retrieval=RetrievalConfig(enabled=True),
    )
    kernel = build_kernel(config, cassette_path=str(cassette))
    assert kernel.indexer is not None
    assert kernel.code_graph is not None
    names = {s.name for s in kernel.tool_schemas}
    assert "find_symbols" in names
    assert "get_skeleton" in names
    assert "impacted_by" in names
    assert len(kernel.tool_schemas) == 9


@pytest.mark.asyncio
async def test_build_kernel_retrieval_enabled_find_symbols_trusted(tmp_path: Path) -> None:
    cassette = tmp_path / "c.json"
    cassette.write_text("[]", encoding="utf-8")
    (tmp_path / "demo.py").write_text("def hello():\n    pass\n", encoding="utf-8")
    config = Config(
        model=ModelConfig(mode="replay"),
        telemetry=TelemetryConfig(trajectory_db=str(tmp_path / "t.db")),
        workspace=WorkspaceConfig(root=str(tmp_path)),
        sandbox=SandboxConfig(runtime="subprocess"),
        retrieval=RetrievalConfig(enabled=True),
    )
    kernel = build_kernel(config, cassette_path=str(cassette))
    registry = kernel.tool_registry
    assert await registry.trusted_output("find_symbols") is True


def test_agency_never_constructs_a_tcb_evaluator() -> None:
    """RC-8: `agency` must not build its own `GateEvaluator`.

    `RunLoop.evaluator` used to default to `evaluator or GateEvaluator(...)`, which meant the
    layer being judged constructed its own judge — a TCB object built outside the composition
    root, where `tcb-isolation` cannot see it. Two things must hold and stay holding: the
    parameter is required, and `agency.run_loop` does not import from the evaluator package
    at all (an unused import is one careless edit away from becoming a used one).
    """
    import inspect

    from sagiha.agency import run_loop as run_loop_module
    from sagiha.agency.run_loop import RunLoop

    param = inspect.signature(RunLoop.__init__).parameters["evaluator"]
    assert param.default is inspect.Parameter.empty, (
        "RunLoop.evaluator must be required — a default means agency can construct a TCB object"
    )

    source = inspect.getsource(run_loop_module)
    assert "from sagiha.outer_loop" not in source, (
        "agency/run_loop.py must not import from outer_loop (the TCB) at all"
    )
