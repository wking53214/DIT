import pytest

from dit import (
    CausalityGate,
    FULL_STACK,
    GSA_V13_STACK,
    HedgingGate,
    IdentityGate,
    SemanticContaminationGate,
    Severity,
    build_stack,
    default_rules,
)


@pytest.fixture
def rules():
    return default_rules()


@pytest.mark.parametrize(
    "text", ["I reviewed the data.", "We measured 4 nodes.", "Our latency fell."]
)
def test_identity_gate_rejects_first_person(rules, text):
    result = IdentityGate(rules).check(text)
    assert not result.passed
    assert result.severity is Severity.RETRYABLE
    assert "First-person" in result.reason


def test_identity_gate_passes_impersonal_text(rules):
    assert IdentityGate(rules).check("Latency fell 12% because of batching.").passed


def test_identity_gate_does_not_fire_inside_words(rules):
    """'mine' is a pronoun; 'mineral' is not. Word boundaries hold."""
    assert IdentityGate(rules).check("Mineral throughput rose 3%.").passed


@pytest.mark.parametrize("text", ["This may hold.", "Results seems fine.", "Perhaps."])
def test_hedging_gate_rejects_uncertainty(rules, text):
    assert not HedgingGate(rules).check(text).passed


def test_causality_gate_accepts_a_causal_connective(rules):
    assert CausalityGate(rules).check("Throughput rose because batching landed.").passed


def test_causality_gate_accepts_a_bare_metric(rules):
    assert CausalityGate(rules).check("Throughput rose 12%.").passed


def test_causality_gate_rejects_unanchored_assertion(rules):
    result = CausalityGate(rules).check("Throughput rose sharply.")
    assert not result.passed
    assert "causal" in result.reason


def test_semantic_contamination_is_terminal(rules):
    result = SemanticContaminationGate(rules).check("The team believes 4 nodes failed.")
    assert not result.passed
    assert result.severity is Severity.TERMINAL
    assert "TERMINAL_LOGIC_BREACH" in result.reason


def test_semantic_gate_ignores_near_misses(rules):
    """'fell' and 'believable' must not trip the affective vocabulary."""
    assert SemanticContaminationGate(rules).check("Depth fell 9%.").passed


def test_build_stack_instantiates_in_order(rules):
    stack = build_stack(rules, GSA_V13_STACK)
    assert [gate.name for gate in stack] == ["identity", "hedging", "causality"]


def test_full_stack_appends_the_epistemic_gate(rules):
    assert build_stack(rules, FULL_STACK)[-1].name == "semantic_contamination"


def test_gate_rejects_a_rule_set_missing_its_pattern():
    from dit import RuleSet

    with pytest.raises(KeyError):
        IdentityGate(RuleSet.from_mapping({"unrelated": "x"}, name="tiny"))
