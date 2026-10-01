"""The connected half: what DIT's verdicts become when CNS is installed.

Skipped when CNS is absent. The independence half, which must hold in both
environments, is in ``test_cns_independence.py`` and never skips.
"""

from __future__ import annotations

import pytest

cns_gate = pytest.importorskip(
    "cns.gate", reason="cns not installed; run in an environment with dit[cns]"
)

from dit import (  # noqa: E402
    FULL_STACK,
    CausalityGate,
    HedgingGate,
    IdentityGate,
    SemanticContaminationGate,
    build_stack,
    default_rules,
    evaluate,
)
from dit.cns_connector import (  # noqa: E402
    CnsGate,
    cns_available,
    cns_chain,
    evaluate_to_cns,
    payload_digest,
    to_cns_result,
)

CLEAN = "Queue depth fell 22% because the batch window was widened."
HEDGED = "Throughput may have improved."
IDENTITY = "I widened the batch window, so depth fell 22%."
AFFECTIVE = "Queue depth fell 22% because the window widened, and we hope it holds."

SAMPLES = (CLEAN, HEDGED, IDENTITY, AFFECTIVE, "", "Nothing to report.")


def test_cns_is_seen_as_available():
    assert cns_available() is True


def test_a_passing_verdict_maps_to_pass_at_the_omega_end():
    (verdict,) = evaluate_to_cns(CLEAN, [HedgingGate(default_rules())])
    assert verdict.outcome is cns_gate.GateOutcome.PASS
    assert verdict.position is cns_gate.GatePosition.OMEGA
    assert verdict.gate == "hedging"
    assert not verdict.blocking()


def test_a_retryable_failure_maps_to_retry_and_keeps_its_reason():
    (verdict,) = evaluate_to_cns(HEDGED, [HedgingGate(default_rules())])
    assert verdict.outcome is cns_gate.GateOutcome.RETRY
    assert verdict.blocking()
    assert "hedging" in verdict.reason.lower()


def test_a_terminal_failure_maps_to_terminal_breach():
    stack = build_stack(default_rules(), FULL_STACK)
    results = evaluate_to_cns(AFFECTIVE, stack)
    assert results[-1].gate == "semantic_contamination"
    assert results[-1].outcome is cns_gate.GateOutcome.TERMINAL_BREACH
    assert cns_gate.resolve(results) is cns_gate.GateOutcome.TERMINAL_BREACH


def test_every_verdict_is_bound_to_the_text_it_judged():
    results = evaluate_to_cns(HEDGED, subject="reply-1")
    assert cns_gate.unbound(results) == ()
    digest = payload_digest(HEDGED)
    assert all(r.binds("reply-1", digest) for r in results)
    # A verdict transplanted onto different text does not bind.
    assert not any(r.binds("reply-1", payload_digest(CLEAN)) for r in results)
    # Nor onto a different subject label.
    assert not any(r.binds("reply-2", digest) for r in results)


def test_the_connector_agrees_with_dits_own_evaluation_on_every_sample():
    """The translation must not change what DIT decided."""
    for text in SAMPLES:
        native = evaluate(text)
        outcome = cns_gate.resolve(evaluate_to_cns(text))
        assert (outcome is cns_gate.GateOutcome.PASS) is native.passed, text
        assert (
            outcome is cns_gate.GateOutcome.TERMINAL_BREACH
        ) is native.terminal, text


def test_the_translation_keeps_dits_short_circuit_on_a_terminal_gate():
    stack = build_stack(default_rules(), (SemanticContaminationGate, IdentityGate))
    text = "We hope it works."
    assert len(evaluate_to_cns(text, stack)) == 1


def test_a_cns_gate_satisfies_the_cns_gate_protocol():
    gate = CnsGate(IdentityGate(default_rules()))
    assert isinstance(gate, cns_gate.Gate)
    assert gate.name == "identity"
    assert gate.position is cns_gate.GatePosition.OMEGA


def test_a_cns_gate_judges_the_same_way_as_the_gate_it_wraps():
    inner = IdentityGate(default_rules())
    gate = CnsGate(inner)
    for text in SAMPLES:
        assert gate.check(text) == to_cns_result(inner.check(text), text)


def test_a_cns_gate_refuses_a_non_text_candidate():
    with pytest.raises(TypeError):
        CnsGate(HedgingGate(default_rules())).check(b"bytes")


def test_the_chain_is_outcome_only_and_says_so():
    chain = cns_chain()
    assert chain.misplaced() == ()
    assert chain.alpha == ()
    assert len(chain.omega) == 3
    assert chain.complete() is False  # DIT has no precondition end


def test_the_chain_runs_through_cns_resolution():
    chain = cns_chain(build_stack(default_rules(), FULL_STACK))
    verdicts = [g.check(AFFECTIVE) for g in chain.omega]
    assert cns_gate.resolve(verdicts) is cns_gate.GateOutcome.TERMINAL_BREACH
    assert cns_gate.resolve([g.check(CLEAN) for g in chain.omega]) is (
        cns_gate.GateOutcome.PASS
    )


def test_the_causality_gate_maps_like_the_others():
    (verdict,) = evaluate_to_cns("Nothing to report.", [CausalityGate(default_rules())])
    assert verdict.outcome is cns_gate.GateOutcome.RETRY
