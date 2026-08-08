"""AblationFlags (TASK-049b): the baseline default and its hash discipline."""

from __future__ import annotations

from aether.domain.config import AblationFlags, config_hash


def test_baseline_default_is_no_injection() -> None:
    assert AblationFlags().inject_test_source is False


def test_a_deviating_flag_changes_the_config_hash() -> None:
    """A run using the ablation says so in its own instrument tuple — two
    configs that differ must hash differently, or the deviation is invisible."""
    baseline = config_hash(AblationFlags())
    deviating = config_hash(AblationFlags(inject_test_source=True))
    assert baseline != deviating
