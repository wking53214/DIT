import pytest

from conftest import COMPLIANT, constant, run
from dit import (
    FAST,
    FULL_STACK,
    DeterministicIntegrityTower,
    Evaluation,
    RuleSet,
    build_stack,
    default_rules,
    evaluate,
    parity_of,
    run_stack,
)
from dit.results import GateResult, Severity


def test_compliant_text_passes():
    result = evaluate(COMPLIANT)
    assert isinstance(result, Evaluation)
    assert result.passed
    assert result.parity == 1.0
    assert result.failures == ()
    assert not result.terminal


def test_failing_text_names_every_gate():
    result = evaluate("I think this may work.")
    assert not result.passed
    # All three strata fail: first person, a hedge, and no metric or cause.
    assert len(result.failures) == 3
    assert result.parity == 0.0


def test_evaluation_needs_no_event_loop():
    """The whole point: a caller holding finished text has no generator to
    await, and should not have to start a loop to ask one question."""
    import asyncio

    with pytest.raises(RuntimeError):
        asyncio.get_running_loop()
    assert evaluate(COMPLIANT).passed


def test_terminal_gate_is_reported_and_short_circuits():
    stack = build_stack(default_rules(), FULL_STACK)
    result = evaluate("The team believes this is fine.", stack)
    assert result.terminal
    assert result.terminal_gate == "semantic_contamination"


def test_terminal_short_circuit_stops_the_stack():
    class _Tripwire:
        name = "tripwire"
        ran = False

        def check(self, text):
            type(self).ran = True
            return GateResult(self.name, True)

    terminal = build_stack(default_rules(), FULL_STACK)[-1]
    evaluate("The team believes this is fine.", [terminal, _Tripwire()])
    assert not _Tripwire.ran


def test_custom_stack_is_honoured():
    stack = build_stack(default_rules(), FULL_STACK)[1:2]  # hedging only
    assert [gate.name for gate in stack] == ["hedging"]
    assert evaluate("I measured nothing at all.", stack).passed


def test_custom_rules_are_honoured():
    from dit import GSA_V13_PATTERNS

    relaxed = RuleSet.from_mapping(
        {**GSA_V13_PATTERNS, "syntactic_breach": r"\b(zzz)\b"}, name="relaxed"
    )
    assert not evaluate("Throughput may hold because load fell 2%.").passed
    assert evaluate("Throughput may hold because load fell 2%.", rules=relaxed).passed


def test_empty_stack_scores_one():
    result = evaluate("anything at all", [])
    assert result.passed
    assert result.parity == 1.0


def test_parity_of_counts_satisfied_gates():
    results = (
        GateResult("a", True),
        GateResult("b", False, Severity.RETRYABLE, "no"),
        GateResult("c", True),
        GateResult("d", True),
    )
    assert parity_of(results) == 0.75
    assert parity_of(()) == 1.0


def test_run_stack_returns_one_result_per_gate():
    stack = build_stack(default_rules())
    assert len(run_stack(COMPLIANT, stack)) == len(stack)


def test_as_dict_is_serializable():
    import json

    payload = json.dumps(evaluate("I think this may work.").as_dict())
    assert "hedging" in payload


def test_evaluate_does_not_normalize():
    """evaluate judges text as written and returns no payload. Rewriting is
    the tower's release-time job, not evaluation's."""
    result = evaluate("Teams optimize throughput because load rose 12%.")
    assert result.passed
    assert not hasattr(result, "payload")


def test_tower_and_evaluate_agree():
    """The anti-drift property: the tower gates through the same code.

    If these ever disagree, a caller auditing text with evaluate() would
    reach a different verdict than the tower that released it.
    """
    for text in (
        COMPLIANT,
        "I think this may work.",
        "Throughput rose sharply.",
        "We measured 4 nodes.",
    ):
        standalone = evaluate(text)
        tower = DeterministicIntegrityTower(constant(text), config=FAST)
        result = run(tower.run(text if standalone.passed else "prompt"))
        first_attempt = result.history[0]
        assert first_attempt.gate_results == standalone.gate_results
