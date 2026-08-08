"""Prompt assembly: layering (ADR-0010) and its stability floor (I10).

`compactor.py` (L5-only compaction, `TASK-024`) lands at M2 and is not here
yet — `LayeredAssembler` exposes no API that could rewrite L1-L4, which is
the structural precondition that task depends on.
"""

from __future__ import annotations
