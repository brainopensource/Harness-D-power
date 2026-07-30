"""Evaluator — trusted computing base.

See docs/08-decisions/0007-trusted-computing-base.md. `GateEvaluator` is the sole
implementation of `sagiha.ports.evaluator.Evaluator`, moved here from `agency/run_loop.py`
(R4) so the grader sits behind the `tcb-isolation` `import-linter` guard.
"""

from __future__ import annotations

from sagiha.outer_loop.evaluator.gate_evaluator import GateEvaluator

__all__ = ["GateEvaluator"]
