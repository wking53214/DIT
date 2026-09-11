import time

from conftest import run
from dit import FAST, HISTORICAL, KineticGovernor, TowerConfig


def test_budget_floors_at_the_target_latency():
    governor = KineticGovernor(HISTORICAL)
    assert governor.temporal_budget("one") == HISTORICAL.target_latency_ms / 1000.0


def test_budget_ceilings_at_the_maximum_pause():
    governor = KineticGovernor(HISTORICAL)
    assert governor.temporal_budget("word " * 10_000) == HISTORICAL.max_pause_seconds


def test_budget_scales_with_payload_density():
    governor = KineticGovernor(HISTORICAL)
    small = governor.temporal_budget("word " * 20)
    large = governor.temporal_budget("word " * 100)
    assert small < large


def test_the_0815_coefficient_is_applied():
    config = TowerConfig(target_latency_ms=0.0, max_pause_seconds=10.0)
    words = 100
    expected = words * config.pacing_seconds_per_word * config.pacing_coefficient
    assert KineticGovernor(config).temporal_budget("w " * words) == expected


def test_pacing_can_be_disabled():
    assert KineticGovernor(FAST).temporal_budget("word " * 100) == 0.0
    assert run(KineticGovernor(FAST).pace("word " * 100)) == 0.0


def test_pace_actually_waits():
    governor = KineticGovernor(TowerConfig(target_latency_ms=20.0))
    started = time.monotonic()
    waited = run(governor.pace("payload"))
    assert waited == 0.02
    assert time.monotonic() - started >= 0.015
