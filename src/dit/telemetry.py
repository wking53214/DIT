"""Structured telemetry.

The audit's "Standardize Internal System Telemetry" item. Events are
emitted as structured records on the ``dit`` logger; nothing is printed.
A deployment attaches its own handler and gets machine-readable lines
without the package choosing a log format for it.
"""

from __future__ import annotations

import logging
from typing import Any

LOGGER = logging.getLogger("dit")


class Telemetry:
    """Emits one logger record per tower event, with a stable event name."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or LOGGER
        self.events: list[dict[str, Any]] = []

    def emit(self, event: str, **fields: Any) -> dict[str, Any]:
        record = {"event": event, **fields}
        self.events.append(record)
        self._logger.info(event, extra={"dit": record})
        return record
