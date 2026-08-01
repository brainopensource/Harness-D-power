"""Trace → dataset exporter — Tier B of the RHI outer loop (v2-S4 Epic S4.4).

See `docs/04-workflows-and-loops/trace-distillation.md` for the eligibility spec this package
implements. Not TCB: `tcb-isolation` names `sagiha.outer_loop.evaluator` specifically, not
`sagiha.outer_loop`, so this package may import adapters and agency-layer reconstruction
machinery (`ContextAssembler.from_trajectory`) freely.
"""

from sagiha.outer_loop.export.eligibility import RunEligibility, assess
from sagiha.outer_loop.export.schema import DPOSample, SFTSample

__all__ = ["DPOSample", "RunEligibility", "SFTSample", "assess"]
