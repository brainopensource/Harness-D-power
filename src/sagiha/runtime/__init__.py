"""Sandboxed execution — the Runtime layer of CAR (docs/02-architecture/car-model.md).

v2-S5 landed the rootless Podman perimeter in `sagiha.adapters.sandbox`. This package
remains the CAR Runtime layer home for future in-process runtime helpers; the Workspace
adapter (`ContainerSandbox`) is the security boundary agents execute inside.
"""
