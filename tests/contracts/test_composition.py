"""Tests for composition root and configuration validation.

See docs/05-tech-stack/composition-and-configuration.md.
"""

from __future__ import annotations

import pytest

from sagiha import Config, Kernel, build_kernel
from sagiha.domain.config import (
    AutonomyConfig,
    GatesConfig,
    ModelConfig,
    SandboxConfig,
)


def test_build_kernel_default_config() -> None:
    config = Config()
    kernel = build_kernel(config)
    assert isinstance(kernel, Kernel)
    assert kernel.config == config


def test_refuse_subprocess_in_autonomous_mode() -> None:
    with pytest.raises(
        ValueError, match="sandbox.runtime='subprocess' is refused"
    ):
        Config(
            sandbox=SandboxConfig(runtime="subprocess"),
            autonomy=AutonomyConfig(level="autonomous"),
        )


def test_refuse_host_network_without_allow_unsafe() -> None:
    with pytest.raises(
        ValueError, match="sandbox.network='host' is refused"
    ):
        Config(
            sandbox=SandboxConfig(network="host", allow_unsafe=False),
        )


def test_refuse_disabling_require_tests_unmodified() -> None:
    with pytest.raises(
        ValueError, match="gates.require_tests_unmodified=False is refused"
    ):
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
