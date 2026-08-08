"""`EffectDispatch` structural protocol tests (T5, `TASK-057`).

Verifies that `DispatchFacade` satisfies `EffectDispatch` at runtime without
`agency/` or `workflow/` importing each other.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from aether.agency.dispatch import EffectDispatch
from aether.workflow.dispatch_facade import DispatchFacade


def test_the_real_facade_satisfies_the_structural_protocol() -> None:
    """Structural typing is checked by nobody unless something checks it. A
    facade method signature drifting away from this Protocol would surface as
    an AttributeError mid-run, which is the failure mode F6 documents.
    """
    mock_dispatcher = MagicMock()
    facade = DispatchFacade(mock_dispatcher, "run-test")
    assert isinstance(facade, EffectDispatch)
