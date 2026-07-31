"""SFT/DPO sample schemas — Spec §6's provider-neutral shape, validated on write.

The exporter defines these schemas; it reads no schema from the `TrajectoryStore`, which "defines
no schema of its own" (`trace-distillation.md`) — step and message shapes live in
`domain/trajectory.py` and `domain/content.py`.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class SFTSample(BaseModel):
    """One admitted, replay-verified, untainted, in-budget step: the assembled request context
    plus the model's own emitted message, and enough labels to reconstruct provenance."""

    model_config = ConfigDict(frozen=True)

    #: Provider-neutral turn list: `[{"role": ..., "content": [...]}]`, the exact reconstructed
    #: prefix up to and including the model's own turn.
    messages: list[dict[str, Any]]
    #: Canonical tool schemas at that step (sorted, matching what the model actually saw).
    tools: list[dict[str, Any]]
    labels: dict[str, Any]


class DPOSample(BaseModel):
    """A Best-of-N preference pair on identical prefixes: same task, same context up to the
    divergence point, one admitted candidate (`chosen`) and one gate-failed sibling (`rejected`).
    """

    model_config = ConfigDict(frozen=True)

    prompt: list[dict[str, Any]]
    chosen: dict[str, Any]
    rejected: dict[str, Any]
    labels: dict[str, Any]
