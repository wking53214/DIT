import pytest

from dit import FAST, HISTORICAL, LoopScope, TowerConfig


def test_historical_profile_carries_the_0815_constant():
    assert HISTORICAL.pacing_coefficient == 0.815
    assert HISTORICAL.max_attempts == 5
    assert HISTORICAL.target_latency_ms == 15.0


def test_default_loop_scope_is_per_run():
    """The audit's 'State Leakage across Transactions' is closed by
    default, not by configuration."""
    assert HISTORICAL.loop_scope is LoopScope.RUN


def test_fast_profile_disables_pacing_only():
    assert not FAST.pacing_enabled
    assert FAST.pacing_coefficient == HISTORICAL.pacing_coefficient


def test_config_is_frozen():
    with pytest.raises(Exception):
        HISTORICAL.max_attempts = 99  # type: ignore[misc]


def test_with_returns_a_validated_copy():
    assert HISTORICAL.with_(max_attempts=2).max_attempts == 2
    with pytest.raises(ValueError):
        HISTORICAL.with_(max_attempts=0)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_attempts": 0},
        {"target_latency_ms": -1},
        {"pacing_coefficient": 0},
        {"loop_cache_entries": 0},
        {"loop_cache_ttl_seconds": 0},
        {"max_delta_chars": 8},
        {"max_delta_chars": 1000, "max_prompt_chars": 100},
    ],
)
def test_invalid_envelopes_are_rejected(kwargs):
    with pytest.raises(ValueError):
        TowerConfig(**kwargs)
