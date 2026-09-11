"""Result and failure types.

The 2026-07-07 audit recorded "Brittle Exception-Driven Flow Control":
the recovered engine signalled an exhausted retry budget by raising
``SystemError``, forcing integration layers to catch a core exception for
an ordinary operational outcome. Exhaustion is a value here. The historical
raising behaviour stays available through
:meth:`dit.tower.DeterministicIntegrityTower.run_strict`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class Status(str, Enum):
    PASS = "PASS"
    #: Retry budget spent without a compliant render.
    EXHAUSTED = "EXHAUSTED"
    #: An epistemic breach: not retryable, the tower refuses the payload.
    TERMINAL_BREACH = "TERMINAL_BREACH"


class Severity(str, Enum):
    #: The attempt is rejected; the tower re-renders with an instructional delta.
    RETRYABLE = "retryable"
    #: The transaction is over. No delta can repair it.
    TERMINAL = "terminal"


@dataclass(frozen=True)
class GateResult:
    """One gate's verdict on one candidate payload."""

    gate: str
    passed: bool
    severity: Severity = Severity.RETRYABLE
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "gate": self.gate,
            "passed": self.passed,
            "severity": self.severity.value,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class AttemptRecord:
    """What happened on one pass through the tower."""

    attempt: int
    digest: str
    looped: bool
    gate_results: tuple[GateResult, ...]
    failures: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.failures and not self.looped

    def as_dict(self) -> dict[str, Any]:
        return {
            "attempt": self.attempt,
            "digest": self.digest,
            "looped": self.looped,
            "passed": self.passed,
            "gates": [result.as_dict() for result in self.gate_results],
            "failures": list(self.failures),
        }


@dataclass(frozen=True)
class TowerResult:
    """The outcome of one :meth:`run`.

    ``parity`` is the historical scalar: 1.0000 on a clean render, and the
    fraction of gates satisfied on the final attempt otherwise. It is
    reported rather than asserted, so a caller can see how close a refused
    transaction came.
    """

    status: Status
    parity: float
    attempts: int
    latency_ms: float
    payload: str | None
    checksum: str | None = None
    failures: tuple[str, ...] = ()
    history: tuple[AttemptRecord, ...] = ()
    ledger_hash: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status is Status.PASS

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "parity": self.parity,
            "attempts": self.attempts,
            "latency_ms": self.latency_ms,
            "checksum": self.checksum,
            "payload": self.payload,
            "failures": list(self.failures),
            "history": [record.as_dict() for record in self.history],
            "ledger_hash": self.ledger_hash,
            "metadata": dict(self.metadata),
        }


class DITError(Exception):
    """Base class for every error this package raises."""


class TowerCollapse(DITError):
    """Raised by ``run_strict`` when parity 1.0000 is unachievable.

    Carries the full :class:`TowerResult` so a caller that does want the
    exception still gets the evidence, which the historical ``SystemError``
    did not provide.
    """

    def __init__(self, result: TowerResult) -> None:
        self.result = result
        super().__init__(
            "GSA_CRITICAL_ERROR: Deterministic Integrity Tower collapsed. "
            f"1.0000 Parity unachievable after {result.attempts} attempt(s): "
            f"{'; '.join(result.failures) or 'no gate detail recorded'}"
        )


class MissingSigningKey(DITError):
    """Raised when a stasis signature is requested with no key configured."""


class LedgerTampered(DITError):
    """Raised when a hash-chain verification finds a broken or edited link."""
