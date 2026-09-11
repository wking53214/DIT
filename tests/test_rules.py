import pytest

from dit import GSA_V13_PATTERNS, RuleSet, default_rules


def test_default_rule_set_carries_every_recovered_pattern():
    rules = default_rules()
    assert set(rules.names()) == set(GSA_V13_PATTERNS)


def test_rules_are_case_insensitive_like_the_recovered_engine():
    rules = default_rules()
    assert rules["pronominal_purge"].search("I am here")
    assert rules["pronominal_purge"].search("WE are here")


def test_unknown_rule_names_the_defined_set():
    rules = default_rules()
    with pytest.raises(KeyError) as excinfo:
        rules["not_a_rule"]
    assert "pronominal_purge" in str(excinfo.value)


def test_requires_reports_every_missing_rule():
    rules = RuleSet.from_mapping({"a": "x"}, name="tiny")
    with pytest.raises(KeyError) as excinfo:
        rules.requires("a", "b", "c")
    assert "'b'" in str(excinfo.value) and "'c'" in str(excinfo.value)


def test_invalid_pattern_is_rejected_at_build_time():
    with pytest.raises(ValueError):
        RuleSet.from_mapping({"broken": "("}, name="broken")


def test_rules_are_data_not_code():
    """The audit's 'Tight Coupling of Validation Mechanics'.

    A deployment swaps the vocabulary without touching the engine.
    """
    relaxed = RuleSet.from_mapping(
        {**GSA_V13_PATTERNS, "syntactic_breach": r"\b(definitely_not_a_word)\b"},
        name="relaxed",
    )
    assert not relaxed["syntactic_breach"].search("this might be true")
