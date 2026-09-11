"""Oscillation protection.

Detects a generator that has begun to repeat itself. The recovered engine
kept every digest it had ever seen in an instance-level ``set``, which the
2026-07-07 audit flagged twice:

    State Leakage across Transactions
        a digest from an earlier, unrelated transaction classified a fresh
        payload as a loop.
    Unbounded Memory Growth
        no eviction policy, so a long-lived tower leaked until the host
        died.

The guard here is bounded by entry count and by age, and its default scope
is one transaction, so neither failure is reachable. ``LoopScope.INSTANCE``
restores cross-transaction memory for callers who want it, still bounded.
"""

from __future__ import annotations

import hashlib
import time
from collections import OrderedDict
from typing import Callable

from .config import TowerConfig


def state_digest(text: str) -> str:
    """SHA-256 of a payload.

    The recovered engine used MD5, which the audit flagged as a collision
    vector letting a crafted payload masquerade as a prior one and force a
    false loop classification. SHA-256 closes that.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class OscillationGuard:
    """A bounded, expiring set of payload digests."""

    def __init__(
        self,
        config: TowerConfig,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._max_entries = config.loop_cache_entries
        self._ttl = config.loop_cache_ttl_seconds
        self._clock = clock
        self._seen: OrderedDict[str, float] = OrderedDict()

    def __len__(self) -> int:
        self._evict()
        return len(self._seen)

    def _evict(self) -> None:
        now = self._clock()
        # Expire by age. Insertion order is age order, so stop at the first
        # live entry rather than walking the whole cache.
        while self._seen:
            oldest_key = next(iter(self._seen))
            if now - self._seen[oldest_key] < self._ttl:
                break
            self._seen.popitem(last=False)
        # Then trim by size.
        while len(self._seen) > self._max_entries:
            self._seen.popitem(last=False)

    def seen(self, digest: str) -> bool:
        """Has this digest been recorded and not yet expired?"""
        self._evict()
        return digest in self._seen

    def remember(self, digest: str) -> None:
        self._seen[digest] = self._clock()
        self._seen.move_to_end(digest)
        self._evict()

    def clear(self) -> None:
        self._seen.clear()
