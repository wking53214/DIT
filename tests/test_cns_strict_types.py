"""F08: the CNS connector reads DIT verdicts with strict types.

``severity="terminal"`` as a plain string used to become RETRY (a downgrade)
and ``passed="no"`` used to become PASS (truthiness). Anything the connector
does not recognise as DIT's own verdict is a TERMINAL_BREACH, never a pass or
a downgrade.
"""

from __future__ import annotations

import os

import pytest

if os.environ.get("DIT_REQUIRE_CNS") == "1":  # CI: a missing cns is a failure, not a skip
    import cns.gate as cns_gate
else:
    cns_gate = pytest.importorskip(
        "cns.gate", reason="cns not installed; run in an environment with dit[cns]"
    )

from dit.cns_connector import CnsGate, payload_digest, to_cns_result  # noqa: E402
from dit.results import GateResult, Severity  # noqa: E402

PASS = cns_gate.GateOutcome.PASS
RETRY = cns_gate.GateOutcome.RETRY
BREACH = cns_gate.GateOutcome.TERMINAL_BREACH
TEXT = "I feel great"


@pytest.mark.parametrize("severity", ["terminal", "TERMINAL", "retryable", None, 1, "fatal"])
def test_a_severity_that_is_not_a_severity_member_is_a_terminal_breach(severity):
    result = GateResult(gate="semantic_contamination", passed=False, severity=severity, reason="EMOTIONAL_LEAK")
    assert to_cns_result(result, TEXT).outcome is BREACH


@pytest.mark.parametrize("passed", ["no", "yes", "", 1, 0, None, "False"])
def test_a_passed_that_is_not_a_bool_is_a_terminal_breach(passed):
    result = GateResult(gate="hedging", passed=passed, severity=Severity.RETRYABLE, reason="r")
    assert to_cns_result(result, TEXT).outcome is BREACH


def test_a_pass_with_an_unrecognised_severity_is_not_a_pass():
    result = GateResult(gate="hedging", passed=True, severity="retryable", reason="")
    assert to_cns_result(result, TEXT).outcome is BREACH


@pytest.mark.parametrize("bad", [
    {"gate": "hedging", "passed": True, "severity": "retryable", "reason": ""},
    None,
    True,
    "PASS",
])
def test_something_that_is_not_a_dit_verdict_is_a_terminal_breach(bad):
    verdict = to_cns_result(bad, TEXT)  # type: ignore[arg-type]
    assert verdict.outcome is BREACH


def test_a_wrapped_gate_returning_a_non_verdict_is_a_terminal_breach():
    class Liar:
        name = "liar"

        def check(self, text):
            return {"passed": True}

    verdict = CnsGate(Liar()).check(TEXT)
    assert verdict.outcome is BREACH and verdict.gate == "liar"


def test_well_typed_verdicts_map_as_before_and_stay_bound():
    cases = [
        (GateResult("g", True, Severity.RETRYABLE, ""), PASS),
        (GateResult("g", False, Severity.RETRYABLE, "r"), RETRY),
        (GateResult("g", False, Severity.TERMINAL, "t"), BREACH),
    ]
    for native, outcome in cases:
        verdict = to_cns_result(native, TEXT, subject="s")
        assert verdict.outcome is outcome and verdict.binds("s", payload_digest(TEXT))
