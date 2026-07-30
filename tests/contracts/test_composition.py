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
    SandboxConfig,
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


def test_refuse_disabling_require_tests_unmodified() -> None:
    with pytest.raises(ValueError, match="gates.require_tests_unmodified=False is refused"):
        Config(
            gates=GatesConfig(require_tests_unmodified=False),
        )


def test_refuse_undefined_model_tier_in_roles() -> None:
    with pytest.raises(ValueError, match="references undefined tier"):
        Config(
            model=ModelConfig(
                roles={"planning": "non_existent_tier"},
            )
        )
