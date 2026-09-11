"""The hash-chain ledger.

Recovered from the later DIT-era Sentinel OS kernel
(``sentinel_os/ledger/audit_store.py``), where the genesis anchor is 64
zeroes and records are hashed over canonical JSON.

One correction to the recovered implementation: its ``verify`` compared
only each record's stored ``prev_hash`` against the previous record's
stored ``hash``, so editing a record's *content* and leaving the two hash
fields alone passed verification. :meth:`HashChainLedger.verify`
recomputes every digest from the record body.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Callable, Mapping, Sequence

from .results import LedgerTampered

#: The genesis anchor: 64 zeroes, as recovered.
GENESIS = "0" * 64

#: Fields the ledger writes itself. A caller's record may not set them.
_RESERVED = ("ts", "prev_hash", "hash")


def canonical_json(data: Any) -> str:
    """Stable serialization: sorted keys, no insignificant whitespace."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def _digest(record: Mapping[str, Any]) -> str:
    body = {key: value for key, value in record.items() if key != "hash"}
    return hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()


class HashChainLedger:
    """An append-only, tamper-evident record of tower transactions."""

    def __init__(self, *, clock: Callable[[], float] = time.time) -> None:
        self._log: list[dict[str, Any]] = []
        self._clock = clock

    def __len__(self) -> int:
        return len(self._log)

    @property
    def head(self) -> str:
        return self._log[-1]["hash"] if self._log else GENESIS

    def append(self, record: Mapping[str, Any]) -> str:
        """Seal one record onto the chain. Returns its hash."""
        collisions = [key for key in _RESERVED if key in record]
        if collisions:
            raise ValueError(
                f"record may not set ledger-owned fields: {collisions}"
            )
        entry: dict[str, Any] = dict(record)
        entry["ts"] = self._clock()
        entry["prev_hash"] = self.head
        entry["hash"] = _digest(entry)
        self._log.append(entry)
        return entry["hash"]

    def entries(self) -> Sequence[Mapping[str, Any]]:
        """A read-only snapshot. Mutating the copies cannot edit the chain."""
        return tuple(dict(entry) for entry in self._log)

    def verify(self) -> bool:
        """True when every link and every digest still holds."""
        previous = GENESIS
        for entry in self._log:
            if entry.get("prev_hash") != previous:
                return False
            if entry.get("hash") != _digest(entry):
                return False
            previous = entry["hash"]
        return True

    def require_intact(self) -> None:
        """Raise :class:`LedgerTampered` if verification fails."""
        if not self.verify():
            raise LedgerTampered(
                f"hash-chain verification failed over {len(self._log)} record(s)"
            )
