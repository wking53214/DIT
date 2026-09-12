"""Synchronous evaluation.

The tower is for callers who can re-ask a generator: it gates, and on
failure it re-renders with an instructional delta. Some callers cannot.
They already hold the text -- it came back from an API call that is over,
or it was read from a record -- and the only question is whether it passes.

:func:`evaluate` answers that question. No event loop, no generator, no
retry, no signing, no ledger. One gate stack, one payload, one verdict.

    >>> from dit import evaluate
    >>> evaluate("Throughput may have improved.").passed
    False

This is the same evaluation the tower performs;
:class:`~dit.tower.DeterministicIntegrityTower` calls straight into it, so
the two cannot drift.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from .gates import GSA_V13_STACK, Gate, build_stack
from .results import GateResult, Severity
from .rules import RuleSet, default_rules


@dataclass(frozen=True)
class Evaluation:
    """One gate stack's verdict on one payload."""

    passed: bool
    parity: float
    gate_results: tuple[GateResult, ...]
    failures: tuple[str, ...]
    terminal_gate: str | None = None

    @property
    def terminal(self) -> bool:
        """True when a gate failed in a way no re-render can repair."""
        return self.terminal_gate is not None

    def as_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "parity": self.parity,
            "failures": list(self.failures),
            "terminal": self.terminal,
            "terminal_gate": self.terminal_gate,
            "gates": [result.as_dict() for result in self.gate_results],
        }


def run_stack(text: str, gates: Sequence[Gate]) -> tuple[GateResult, ...]:
    """Run every gate over ``text``, short-circuiting on a terminal failure.

    A terminal failure ends the stack because nothing after it can change
    the outcome, and because evaluating further gates against a payload
    already outside the evidentiary frame produces findings about text
    that will not be released either way.
    """
    results: list[GateResult] = []
    for gate in gates:
        result = gate.check(text)
        results.append(result)
        if not result.passed and result.severity is Severity.TERMINAL:
            break
    return tuple(results)


def parity_of(results: Sequence[GateResult]) -> float:
    """The fraction of gates satisfied, rounded to the historical 4 places.

    An empty stack scores 1.0: nothing was asked, so nothing failed.
    """
    if not results:
        return 1.0
    passed = sum(1 for result in results if result.passed)
    return round(passed / len(results), 4)


def evaluate(
    text: str,
    gates: Sequence[Gate] | None = None,
    *,
    rules: RuleSet | None = None,
) -> Evaluation:
    """Judge ``text`` against a gate stack.

    Args:
        text: the payload to judge, as written. Nothing is normalized.
        gates: an explicit stack. Defaults to the three retryable GSA v13.0
            strata built over ``rules``.
        rules: the rule set used to build the default stack. Ignored when
            ``gates`` is given, since those gates carry their own.
    """
    stack = gates if gates is not None else build_stack(
        rules or default_rules(), GSA_V13_STACK
    )
    results = run_stack(text, stack)
    terminal = next(
        (
            result
            for result in results
            if not result.passed and result.severity is Severity.TERMINAL
        ),
        None,
    )
    failures = tuple(result.reason for result in results if not result.passed)
    return Evaluation(
        passed=not failures,
        parity=parity_of(results),
        gate_results=results,
        failures=failures,
        terminal_gate=terminal.gate if terminal is not None else None,
    )
