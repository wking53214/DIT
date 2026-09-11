"""The kinetic governor.

A mechanical rev-limiter: it paces emission against payload density so a
burst of cheap tokens cannot leave the tower at a rate its consumers were
not sized for. The 0.815 coefficient is the historical constant, carried
forward as configuration.

The audit's "Single-Threaded Blocking Lifecycle disguised as Concurrent
Architecture" finding applies to the tower, not to this component: the
pause is a real ``await`` and yields the event loop, so concurrent
transactions interleave through it rather than queue behind it.
"""

from __future__ import annotations

import asyncio

from .config import TowerConfig


class KineticGovernor:
    """Computes and applies the temporal budget for one emission."""

    name = "kinetic_governor"

    def __init__(self, config: TowerConfig) -> None:
        self._config = config

    def temporal_budget(self, payload: str) -> float:
        """Seconds to hold this payload before release.

        Density is word count. The floor is the configured target latency;
        the ceiling stops a very large payload from stalling the caller.
        """
        if not self._config.pacing_enabled:
            return 0.0
        density = len(payload.split())
        computed = (
            density
            * self._config.pacing_seconds_per_word
            * self._config.pacing_coefficient
        )
        floor = self._config.target_latency_ms / 1000.0
        return max(floor, min(computed, self._config.max_pause_seconds))

    async def pace(self, payload: str) -> float:
        """Apply the budget. Returns the seconds actually waited."""
        delay = self.temporal_budget(payload)
        if delay > 0:
            await asyncio.sleep(delay)
        return delay
