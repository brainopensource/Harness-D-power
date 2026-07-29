"""Toolchain payloads — see docs/03-contracts-and-models/domain-schemas.md#toolchain.

The port exists so gates never hardcode pytest and pyright. These are its payloads.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ToolchainInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    language: str
    test_runner: str
    type_checker: str | None = None
    linter: str | None = None
    package_manager: str | None = None


class TestReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: int
    failed: int
    skipped: int
    duration_s: float
    failures: tuple[str, ...] = ()  # node ids, not free text
    exit_code: int


class CoverageReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    line_rate: float  # 0-1
    branch_rate: float | None = None
    by_file: dict[str, float] = {}  # exempt: keyed by path, open-shaped
