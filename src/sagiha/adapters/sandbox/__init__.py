"""Sandbox adapters — Container / Podman rootless isolation."""

from sagiha.adapters.sandbox.container import ContainerSandbox, secret_materialize_paths
from sagiha.adapters.sandbox.egress import EgressProxy

__all__ = ["ContainerSandbox", "EgressProxy", "secret_materialize_paths"]
