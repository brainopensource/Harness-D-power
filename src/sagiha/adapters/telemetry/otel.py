"""OpenTelemetry EventBus subscriber adapter for Block 5.

See docs/05-tech-stack/telemetry-and-observability.md.

SENIOR TODO: OTLP gRPC/HTTP exporter, trace context propagation across events,
             token usage metrics counter, span attributes redaction.
"""

from __future__ import annotations

import logging

from sagiha.domain.events import Event

logger = logging.getLogger(__name__)


class OTelEventObserver:
    """EventBus subscriber exporting events as OpenTelemetry spans and metrics."""

    def __init__(self, otlp_endpoint: str = "http://localhost:4317") -> None:
        self._endpoint = otlp_endpoint

    async def on_event(self, event: Event) -> None:
        """Handle incoming EventBus event and export to OTel collector."""
        raise NotImplementedError("v2-S7 — see docs/STATUS.md")
