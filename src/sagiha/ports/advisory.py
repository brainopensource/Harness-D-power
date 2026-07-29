"""Advisory (AOI) ports — RewardPredictor, FailurePredictor, CostPerformanceEstimator.

See docs/03-contracts-and-models/hexagonal-ports.md#advisory-aoi and
docs/05-tech-stack/aoi-coprocessors.md. All return a calibrated `Prediction`; all ship in shadow
mode. Advisory only — they rank and filter but never admit or reject. Deferred past v0.1 per the
2026-07-28 architecture review: these Protocols exist so the port surface is complete, but ship
with no adapter in v0.1; only the event-logging substrate that will train them is built.
"""

from __future__ import annotations

from typing import Final, Protocol

from sagiha.domain.work import Prediction, TaskSpec

PORT_VERSION: Final = 1
STABILITY: Final = "experimental"


class RewardPredictor(Protocol):
    async def predict(self, task: TaskSpec, branch_id: str) -> Prediction: ...


class FailurePredictor(Protocol):
    async def predict(self, task: TaskSpec, branch_id: str) -> Prediction: ...


class CostPerformanceEstimator(Protocol):
    async def predict(self, task: TaskSpec) -> Prediction: ...
