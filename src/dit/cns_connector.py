"""Optional connector to CNS (``cns.gate``).

DIT is independent. It has no runtime dependency, imports nothing from CNS
when it loads, and its whole suite passes with CNS absent. This module is the
one place that knows CNS exists, and it asks for CNS only when one of its
functions is called. Without CNS installed those calls raise
:class:`CnsNotInstalled` with the install command; nothing else in DIT is
affected.

What connecting means
---------------------
DIT keeps its own :class:`~dit.results.GateResult` (``gate``, ``passed``,
``severity``, ``reason``). CNS's shared gate contract is
``cns.gate.GateResult`` (``gate``, ``position``, ``outcome``, ``reason``,
``subject``, ``subject_digest``). This module translates one into the other
without changing either, so a consumer that speaks CNS can use DIT's gates
and resolve them alongside gates from other repositories.

The mapping, and why
--------------------
=====================  ===========================================
DIT                    CNS
=====================  ===========================================
gate position          ``OMEGA``. DIT judges the payload *as
                       generated*: the result does not leave if a
                       gate fails. It has no precondition end, and
                       this connector does not invent one.
``passed``             ``PASS``
failed, RETRYABLE      ``RETRY``  (a re-render with a delta may fix it)
failed, TERMINAL       ``TERMINAL_BREACH``  (no delta repairs it)
``reason``             ``reason`` unchanged
judged text            ``subject`` (a label, default ``"payload"``)
                       and ``subject_digest``, which is
                       ``cns.gate.subject_digest({"text": text})``
=====================  ===========================================

Because DIT has only the outcome end, ``cns_chain(...).complete()`` is
``False`` by design. That is CNS's own finding about DIT ("a good outcome
stratum with no precondition") stated honestly, not a defect in the
connector. A consumer that wants a complete chain supplies the ``alpha`` end
from a repository that has one.

Install with the extra: ``pip install 'dit[cns]'``.
"""

from __future__ import annotations

import importlib
from dataclasses import replace
from types import ModuleType
from typing import Any, Mapping, Sequence

from .evaluate import run_stack
from .oscillation import state_digest
from .gates import GSA_V13_STACK, Gate, build_stack
from .results import GateResult, Severity, Status, TowerResult
from .tower import DeterministicIntegrityTower
from .rules import RuleSet, default_rules

__all__ = [
    "CnsGate",
    "CnsNotInstalled",
    "cns_available",
    "cns_chain",
    "evaluate_to_cns",
    "tower_result_to_cns",
    "payload_digest",
    "to_cns_result",
]

INSTALL_HINT = "pip install 'dit[cns]'"

#: What ``subject`` is set to when the caller does not name the judged content.
DEFAULT_SUBJECT = "payload"


class CnsNotInstalled(ImportError):
    """Raised by this module's functions when ``cns`` cannot be imported."""


def _cns_gate() -> ModuleType:
    """Import ``cns.gate`` on demand, or say exactly what is missing."""
    try:
        return importlib.import_module("cns.gate")
    except ImportError as exc:
        raise CnsNotInstalled(
            "dit.cns_connector needs the CNS package (cns.gate), which is not "
            f"installed. Install it with: {INSTALL_HINT}. DIT itself works "
            "without it."
        ) from exc


def cns_available() -> bool:
    """Whether the CNS gate contract can be imported in this environment."""
    try:
        _cns_gate()
    except CnsNotInstalled:
        return False
    return True


def payload_digest(text: str) -> str:
    """The digest a bound verdict on ``text`` carries.

    Pass it, with the subject label, to ``GateResult.binds`` to check that a
    verdict was issued against exactly this text.
    """
    return _cns_gate().subject_digest({"text": text})


def to_cns_result(
    result: GateResult, text: str, *, subject: str = DEFAULT_SUBJECT
) -> Any:
    """Translate one DIT verdict on ``text`` into a ``cns.gate.GateResult``."""
    gate = _cns_gate()
    if result.passed:
        outcome = gate.GateOutcome.PASS
    elif result.severity is Severity.TERMINAL:
        outcome = gate.GateOutcome.TERMINAL_BREACH
    else:
        outcome = gate.GateOutcome.RETRY
    return gate.GateResult(
        gate=result.gate,
        position=gate.GatePosition.OMEGA,
        outcome=outcome,
        reason=result.reason,
        subject=subject,
        subject_digest=gate.subject_digest({"text": text}),
    )


class CnsGate:
    """A DIT gate that satisfies ``cns.gate.Gate``.

    Wraps any object with DIT's ``name`` and ``check(text)``. ``check`` runs
    the wrapped gate unchanged and returns its verdict as a bound
    ``cns.gate.GateResult`` at the OMEGA end.
    """

    def __init__(self, inner: Gate, *, subject: str = DEFAULT_SUBJECT) -> None:
        _cns_gate()  # fail here, at construction, not on first use
        self._inner = inner
        self._subject = subject

    @property
    def name(self) -> str:
        return self._inner.name

    @property
    def position(self) -> Any:
        return _cns_gate().GatePosition.OMEGA

    def check(self, candidate: object) -> Any:
        if not isinstance(candidate, str):
            raise TypeError(
                f"DIT gates judge text; got {type(candidate).__name__}"
            )
        return to_cns_result(
            self._inner.check(candidate), candidate, subject=self._subject
        )


def _default_stack(rules: RuleSet | None) -> tuple[Gate, ...]:
    return build_stack(rules or default_rules(), GSA_V13_STACK)


def tower_result_to_cns(
    tower: DeterministicIntegrityTower,
    result: TowerResult,
    *,
    subject: str,
) -> tuple[Any, ...]:
    """Bind CNS verdicts to the exact payload and release evidence in a TowerResult.

    This only accepts a successful native release whose signature verifies
    under this tower's signer and whose attached ledger (if any) verifies at
    the result's head. It re-runs the tower's own gates against the released
    payload, then binds each CNS verdict to the final payload, DIT payload
    digest, signature block, checksum and optional ledger hash. The CNS digest
    does not replace either native evidence item or establish signer identity.
    """
    if not isinstance(tower, DeterministicIntegrityTower):
        raise TypeError("tower must be a DeterministicIntegrityTower")
    if not isinstance(result, TowerResult):
        raise TypeError("result must be a TowerResult")
    if result.status is not Status.PASS or not isinstance(result.payload, str):
        raise ValueError("only a PASS TowerResult with a released payload can be bound")
    signature = result.metadata.get("signature")
    if (
        not isinstance(result.checksum, str)
        or not result.checksum
        or not isinstance(signature, Mapping)
        or signature.get("value") != result.checksum
        or signature.get("algorithm") != tower.signer.algorithm
        or signature.get("key_id") != tower.signer.key_id
        or not tower.signer.verify(result.payload, result.checksum)
    ):
        raise ValueError("TowerResult lacks a valid signature from this tower")
    if tower.ledger is None:
        if result.ledger_hash is not None:
            raise ValueError("TowerResult ledger hash cannot be verified by this tower")
    elif (
        result.ledger_hash != tower.ledger.head
        or not tower.ledger.verify(expected_head=result.ledger_hash)
    ):
        raise ValueError("TowerResult ledger does not verify at its recorded head")
    if not tower.gates:
        raise ValueError("a release cannot be bound without DIT gate results")

    native_results = run_stack(result.payload, tower.gates)
    if not native_results:
        raise ValueError("a release cannot be bound without DIT gate results")
    cns = _cns_gate()
    release_content = {
        "status": result.status.value,
        "payload": result.payload,
        "native_payload_digest": state_digest(result.payload),
        "checksum": result.checksum,
        "signature": dict(signature),
        "ledger_hash": result.ledger_hash,
    }
    digest = cns.subject_digest(release_content)
    return tuple(
        replace(
            to_cns_result(native, result.payload, subject=subject),
            subject_digest=digest,
        )
        for native in native_results
    )


def cns_chain(
    gates: Sequence[Gate] | None = None,
    *,
    rules: RuleSet | None = None,
    subject: str = DEFAULT_SUBJECT,
) -> Any:
    """A ``cns.gate.GateChain`` holding DIT's gates in the ``omega`` slot.

    ``alpha`` stays empty: DIT has no precondition end. The default stack is
    the same one :func:`dit.evaluate` uses.
    """
    gate = _cns_gate()
    stack = gates if gates is not None else _default_stack(rules)
    return gate.GateChain(omega=tuple(CnsGate(g, subject=subject) for g in stack))


def evaluate_to_cns(
    text: str,
    gates: Sequence[Gate] | None = None,
    *,
    rules: RuleSet | None = None,
    subject: str = DEFAULT_SUBJECT,
) -> tuple[Any, ...]:
    """Run DIT's stack over ``text`` and return CNS verdicts.

    Same stack, same short-circuit on a terminal failure, same verdicts as
    :func:`dit.evaluate`; only the representation differs. Combine the
    result with ``cns.gate.resolve``.
    """
    _cns_gate()
    stack = gates if gates is not None else _default_stack(rules)
    return tuple(
        to_cns_result(r, text, subject=subject) for r in run_stack(text, stack)
    )
