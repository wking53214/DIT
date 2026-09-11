import pytest

from dit import StructureNormalizer, default_rules


@pytest.fixture
def normalizer():
    return StructureNormalizer(default_rules())


@pytest.mark.parametrize(
    "verb", ["improve", "optimize", "enhance", "enable", "support", "leverage"]
)
def test_every_abstract_verb_collapses_to_the_primitive(normalizer, verb):
    assert normalizer.normalize(f"The team will {verb} the pipeline.") == (
        "The team will use the pipeline."
    )


def test_normalization_is_idempotent(normalizer):
    once = normalizer.normalize("Optimize and leverage the queue.")
    assert normalizer.normalize(once) == once


def test_would_change_predicts_a_rewrite(normalizer):
    assert normalizer.would_change("optimize this")
    assert not normalizer.would_change("measure this")


def test_normalizer_leaves_gate_vocabulary_untouched(normalizer):
    """The ordering invariant, stated as a property.

    Normalization runs after the gates. That is only safe because it
    rewrites the abstract-verb vocabulary and nothing else: it can neither
    introduce a pronoun or a hedge, nor remove a causal connective or a
    metric. If this ever fails, the post-pass ordering in dit.tower is no
    longer sound.
    """
    rules = default_rules()
    text = "Teams optimize throughput because latency rose 12%."
    normalized = normalizer.normalize(text)
    for rule in ("pronominal_purge", "syntactic_breach", "causal_link"):
        assert bool(rules[rule].search(text)) == bool(rules[rule].search(normalized))
    assert bool(rules["metric_verification"].search(normalized))
