"""Advisory (AOI) port — a single calibrated predictor dispatching on `PredictionKind`.

See docs/03-contracts-and-models/hexagonal-ports.md#advisory-aoi and
docs/05-tech-stack/aoi-coprocessors.md. Returns a calibrated `Prediction`; ships in shadow mode.
Advisory only — ranks and filters but never admits or rejects. Deferred past v0.1 per the
2026-07-28 architecture review: this Protocol exists so the port surface is complete, but ships
with no adapter in v0.1; only the event-logging substrate that will train it is built.

Reward, failure, and cost-performance predictions differ only in which scalar they predict — a
taxonomy, not three contracts (ADR-0019). If `PredictionKind` ever accumulates variants whose
payloads diverge structurally, split the Protocol again along that seam.
"""

from __future__ import annotations

from typing import Final, Protocol

from sagiha.domain.work import Prediction, PredictionKind, TaskSpec

PORT_VERSION: Final = 2
STABILITY: Final = "experimental"


class Advisory(Protocol):
    async def predict(self, kind: PredictionKind, task: TaskSpec, branch_id: str) -> Prediction: ...
