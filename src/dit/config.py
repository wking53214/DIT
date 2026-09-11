"""Tower configuration.

Every operating constant of the Deterministic Integrity Tower lives here
rather than inside the components, so a deployment can be reasoned about
from one frozen object instead of by reading five constructors.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum


class LoopScope(str, Enum):
    """Lifetime of the oscillation guard's memory.

    RUN       one transaction. Two callers cannot collide. This is the
              default and the remediation for the 2026-07-07 audit finding
              "State Leakage across Transactions".
    INSTANCE  shared across every run on one tower. Historical behaviour.
              Available deliberately, bounded by size and TTL.
    """

    RUN = "run"
    INSTANCE = "instance"


@dataclass(frozen=True)
class TowerConfig:
    """Immutable operating envelope for one tower."""

    # Retry envelope.
    max_attempts: int = 5

    # Kinetic governor. The 0.815 coefficient is the historical constant;
    # it is configuration here, not a literal buried in the governor.
    pacing_enabled: bool = True
    target_latency_ms: float = 15.0
    pacing_coefficient: float = 0.815
    pacing_seconds_per_word: float = 0.002
    max_pause_seconds: float = 0.200

    # Oscillation guard.
    loop_scope: LoopScope = LoopScope.RUN
    loop_cache_entries: int = 4096
    loop_cache_ttl_seconds: float = 300.0

    # Instructional-delta injection defence.
    max_delta_chars: int = 2000
    max_prompt_chars: int = 32_000

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.target_latency_ms < 0:
            raise ValueError("target_latency_ms must be >= 0")
        if self.max_pause_seconds < 0:
            raise ValueError("max_pause_seconds must be >= 0")
        if self.pacing_coefficient <= 0:
            raise ValueError("pacing_coefficient must be > 0")
        if self.loop_cache_entries < 1:
            raise ValueError("loop_cache_entries must be >= 1")
        if self.loop_cache_ttl_seconds <= 0:
            raise ValueError("loop_cache_ttl_seconds must be > 0")
        if self.max_delta_chars < 64:
            raise ValueError("max_delta_chars must be >= 64")
        if self.max_prompt_chars < self.max_delta_chars:
            raise ValueError("max_prompt_chars must be >= max_delta_chars")

    def with_(self, **changes: object) -> "TowerConfig":
        """Return a copy with fields replaced, re-validated."""
        return replace(self, **changes)


#: The configuration the GSA v13.0 engine ran with, minus its defects.
HISTORICAL = TowerConfig()

#: Pacing disabled and loop memory per-run: the profile for test suites and
#: for callers who already rate-limit upstream.
FAST = TowerConfig(pacing_enabled=False)
